"""Módulo de segurança, hashing de senhas e geração de tokens de sessão."""

import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Instância padrão do PasswordHasher (utiliza parâmetros recomendados de Argon2id)
_hasher = PasswordHasher()

# Hash fictício pré-computado para mitigação de timing attacks em tentativas de login inexistentes
DUMMY_PASSWORD_HASH: str = _hasher.hash("dummy-security-hash-for-timing-mitigation")

# Limites da política de senhas (sem imposição de composição de caracteres)
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


def validate_password_policy(password: str) -> tuple[bool, str | None]:
    """Valida se a senha atende à política mínima de 12 e máxima de 128 caracteres."""
    if not isinstance(password, str):
        return False, "A senha deve ser uma string válida."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"A senha deve conter no mínimo {MIN_PASSWORD_LENGTH} caracteres."
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"A senha deve conter no máximo {MAX_PASSWORD_LENGTH} caracteres."
    return True, None


def hash_password(password: str) -> str:
    """Gera o hash Argon2id da senha fornecida."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verifica se a senha em texto plano confere com o hash Argon2.

    Retorna estritamente bool (True se coincidir, False caso contrário).
    Nunca levanta exceção para senha errada, formato inválido ou corrupção.
    """
    if not password_hash or not password:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception:
        return False


def needs_rehash(password_hash: str) -> bool:
    """Verifica se os parâmetros do hash estão desatualizados e requerem re-hash."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:
        return True


def generate_session_token() -> str:
    """Gera um token aleatório criptograficamente seguro de 32 bytes (URL-safe)."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Gera o hash SHA-256 (64 caracteres hex) do token de sessão para persistência."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
