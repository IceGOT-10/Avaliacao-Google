"""Endpoints de autenticação de lojistas e administradores: /auth/*."""

import logging
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    create_user_session,
    revoke_user_session,
)
from app.services.login_rate_limiter import global_login_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool


def _verify_csrf_origin(request: Request) -> None:
    """Verifica a origem de requisições de alteração de estado (CSRF protection adicional).

    Se os cabeçalhos Origin ou Referer estiverem presentes, valida contra ALLOWED_ORIGINS.
    Limitação conhecida: se ambos estiverem ausentes (ex.: ferramentas de API ou requisições
    sem cabeçalho de origem), a defesa primária se apoia na política SameSite=Lax do cookie.
    """
    settings = get_settings()
    allowed = set(settings.allowed_origins)

    origin = request.headers.get("origin")
    if origin:
        if origin not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origem de requisição não permitida.",
                headers={"Cache-Control": "no-store"},
            )
        return

    referer = request.headers.get("referer")
    if referer:
        try:
            parsed = urlsplit(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
            if referer_origin not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Origem de requisição não permitida.",
                    headers={"Cache-Control": "no-store"},
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origem de requisição inválida.",
                headers={"Cache-Control": "no-store"},
            )


@router.post("/login", response_model=UserResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Autentica o usuário, emite cookie HttpOnly de sessão e zera contadores de tentativa."""
    _verify_csrf_origin(request)
    settings = get_settings()

    # 1. Verificação do limitador de taxa de login
    is_blocked, remaining = global_login_rate_limiter.is_blocked(body.email)
    if is_blocked:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Muitas tentativas de login. Tente novamente mais tarde."},
            headers={"Cache-Control": "no-store", "Retry-After": str(remaining)},
        )

    # 2. Autenticação com proteção contra timing attack
    user = authenticate_user(db=db, email=body.email, password=body.password)
    if not user:
        global_login_rate_limiter.record_failure(body.email)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Credenciais inválidas."},
            headers={"Cache-Control": "no-store"},
        )

    # 3. Sucesso: zera falhas e cria sessão
    global_login_rate_limiter.record_success(body.email)
    raw_token = create_user_session(db=db, user=user)

    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        is_admin=user.is_admin,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Revoga a sessão atual no banco e invalida o cookie HttpOnly (idempotente)."""
    _verify_csrf_origin(request)
    settings = get_settings()

    token = request.cookies.get(settings.session_cookie_name)
    if token:
        revoke_user_session(db=db, token=token)

    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"})


@router.get("/me", response_model=UserResponse)
def get_me(
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """Retorna os dados do usuário autenticado a partir do cookie de sessão."""
    response.headers["Cache-Control"] = "no-store"
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_admin=current_user.is_admin,
    )
