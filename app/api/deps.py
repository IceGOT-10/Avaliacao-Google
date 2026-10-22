"""Dependências FastAPI para injeção de sessão e autenticação de usuários."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import resolve_session_user


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
