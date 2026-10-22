"""Dependências FastAPI para injeção de sessão e autenticação de usuários."""

from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.models.business import Business
from app.models.business_membership import BusinessMembership
from app.services.auth_service import resolve_session_user


def verify_csrf_origin(request: Request) -> None:
    settings = get_settings()
    allowed = set(settings.allowed_origins)
    origin = request.headers.get("origin")
    if origin:
        if origin not in allowed:
            raise HTTPException(status_code=403, detail="Origem de requisição não permitida.", headers={"Cache-Control": "no-store"})
        return
    referer = request.headers.get("referer")
    if referer:
        try:
            parsed = urlsplit(referer)
            if f"{parsed.scheme}://{parsed.netloc}" not in allowed:
                raise ValueError
        except Exception:
            raise HTTPException(status_code=403, detail="Origem de requisição inválida.", headers={"Cache-Control": "no-store"})


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Extrai o token da sessão a partir do cookie HttpOnly e resolve o usuário ativo."""
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado.",
            headers={"Cache-Control": "no-store"},
        )

    user = resolve_session_user(db=db, token=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão inválida ou expirada.",
            headers={"Cache-Control": "no-store"},
        )

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Exige que o usuário autenticado possua privilégios de administrador."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
            headers={"Cache-Control": "no-store"},
        )
    return current_user


def get_business_access(min_role: str = "manager"):
    def dependency(
        business_id: int = Path(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> tuple[Business, str]:
        business = db.get(Business, business_id)
        if not business:
            raise HTTPException(status_code=404, detail="Loja não encontrada.", headers={"Cache-Control": "no-store"})
        if current_user.is_admin:
            return business, "admin"
        membership = db.scalars(select(BusinessMembership).where(
            BusinessMembership.business_id == business_id,
            BusinessMembership.user_id == current_user.id,
        )).first()
        if not membership:
            raise HTTPException(status_code=404, detail="Loja não encontrada.", headers={"Cache-Control": "no-store"})
        ranks = {"manager": 1, "owner": 2, "admin": 3}
        if ranks.get(membership.role, 0) < ranks.get(min_role, 1):
            raise HTTPException(status_code=403, detail="Permissão insuficiente.", headers={"Cache-Control": "no-store"})
        return business, membership.role
    return dependency
