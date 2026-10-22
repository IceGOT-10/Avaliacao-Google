"""Serviço de autenticação e gerenciamento de sessões server-side."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    generate_session_token,
    hash_session_token,
    verify_password,
)
from app.models.user import User
from app.models.user_session import UserSession

logger = logging.getLogger(__name__)


def authenticate_user(
    db: Session,
    email: str | None,
    password: str | None,
) -> User | None:
    """Autentica o usuário com mitigação de timing attack e resposta uniforme.

    Regras:
    - Normaliza o email (strip + lower).
    - Usuário inexistente, inativo ou senha errada produzem exatamente a mesma resposta (None).
    - Para usuário inexistente, executa verificação contra hash fictício para equalizar o tempo.
    """
    if not email or not password:
        if password:
            verify_password(DUMMY_PASSWORD_HASH, password)
        return None

    normalized_email = email.strip().lower()

    stmt = select(User).where(User.email == normalized_email)
    user = db.scalars(stmt).first()

    if user is None:
        verify_password(DUMMY_PASSWORD_HASH, password)
        return None

    is_valid = verify_password(user.password_hash, password)

    if not is_valid:
        return None

    if not user.is_active:
        return None

    return user


def create_user_session(
    db: Session,
    user: User,
    session_ttl_hours: int | None = None,
) -> str:
    """Cria uma nova sessão server-side persistindo apenas o hash SHA-256 do token.

    Retorna o token aleatório em texto claro estritamente para ser enviado no cookie.
    """
    settings = get_settings()
    ttl_hours = session_ttl_hours if session_ttl_hours is not None else settings.session_ttl_hours

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)

    user_session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(user_session)
    db.commit()

    return raw_token


def resolve_session_user(
    db: Session,
    token: str | None,
) -> User | None:
    """Valida o token da sessão e retorna o usuário associado, se ativo e sessão válida.

    Regras:
    - Token ausente ou vazio: retorna None.
    - Sessão expirada ou com revoked_at preenchido: retorna None.
    - Usuário inativo: retorna None.
    """
    if not token or not isinstance(token, str):
        return None

    token_hash = hash_session_token(token)
    now = datetime.now(timezone.utc)

    stmt = (
        select(UserSession)
        .where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    user_session = db.scalars(stmt).first()
    if not user_session:
        return None

    user = user_session.user
    if not user or not user.is_active:
        return None

    return user


def revoke_user_session(
    db: Session,
    token: str | None,
) -> None:
    """Revoga a sessão identificada pelo token (operação idempotente)."""
    if not token or not isinstance(token, str):
        return

    token_hash = hash_session_token(token)
    now = datetime.now(timezone.utc)

    stmt = select(UserSession).where(
        UserSession.token_hash == token_hash,
        UserSession.revoked_at.is_(None),
    )
    user_session = db.scalars(stmt).first()
    if user_session:
        user_session.revoked_at = now
        db.commit()
