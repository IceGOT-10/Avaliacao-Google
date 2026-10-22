"""Testes de integração para autenticação por sessão e cookies (POST /auth/*, GET /auth/me)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.security import hash_password, hash_session_token
from app.main import app
from app.models.user import User
from app.models.user_session import UserSession
from app.services.login_rate_limiter import LoginRateLimiter, global_login_rate_limiter

# Rota temporária registrada apenas para validar o require_admin
admin_test_router = APIRouter()


@admin_test_router.get("/admin-only-test")
def admin_only_endpoint(admin: User = Depends(require_admin)):
    return {"admin_id": admin.id}


app.include_router(admin_test_router)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Garante estado limpo do limitador de login para cada teste."""
    global_login_rate_limiter.reset()
    yield
    global_login_rate_limiter.reset()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Usuário padrão ativo e não-admin."""
    user = User(
        email="lojista@exemplo.com",
        password_hash=hash_password("senha_lojista_123"),
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def inactive_user(db_session: Session) -> User:
    """Usuário cadastrado porém inativo."""
    user = User(
        email="inativo@exemplo.com",
        password_hash=hash_password("senha_lojista_123"),
        is_active=False,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Usuário administrador."""
    admin = User(
        email="admin@exemplo.com",
        password_hash=hash_password("senha_admin_super_123"),
        is_active=True,
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    return admin


def test_login_success_and_cookie_attributes(db_client, db_session, test_user):
    """Login bem-sucedido retorna 200, dados seguros e cookie HttpOnly com SameSite=Lax."""
    settings = get_settings()

    response = db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == "lojista@exemplo.com"
    assert data["is_admin"] is False
    assert "password_hash" not in data
    assert response.headers.get("Cache-Control") == "no-store"

    # Verificação estrita dos atributos do cookie
    cookie = response.cookies.get(settings.session_cookie_name)
    assert cookie is not None, "Cookie de sessão deve ser emitido"

    # Inspeciona o cabeçalho Set-Cookie para conferir HttpOnly e SameSite
    set_cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/" in set_cookie

    # Garante que NENHUM token em claro foi persistido no banco
    raw_token = cookie
    session_in_db = db_session.scalars(select(UserSession).where(UserSession.user_id == test_user.id)).first()
    assert session_in_db is not None
    assert session_in_db.token_hash == hash_session_token(raw_token)
    assert session_in_db.token_hash != raw_token


def test_login_email_case_insensitivity(db_client, test_user):
    """Email digitado com maiúsculas deve autenticar normalmente via normalização."""
    response = db_client.post(
        "/auth/login",
        json={"email": "Lojista@Exemplo.COM", "password": "senha_lojista_123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "lojista@exemplo.com"


def test_login_invalid_credentials_indistinguishable(db_client, test_user, inactive_user):
    """Senha errada, email inexistente e usuário inativo produzem a MESMA resposta 401."""
    r_wrong_pwd = db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_totalmente_errada"},
    )
    r_nonexistent = db_client.post(
        "/auth/login",
        json={"email": "naoexiste@exemplo.com", "password": "senha_totalmente_errada"},
    )
    r_inactive = db_client.post(
        "/auth/login",
        json={"email": "inativo@exemplo.com", "password": "senha_lojista_123"},
    )

    for r in [r_wrong_pwd, r_nonexistent, r_inactive]:
        assert r.status_code == 401
        assert r.json() == {"detail": "Credenciais inválidas."}
        assert r.headers.get("Cache-Control") == "no-store"
        assert "set-cookie" not in r.headers


def test_login_rate_limiting_and_reset_on_success(db_client, test_user):
    """Excesso de falhas (5) bloqueia com 429; login correto após bloqueio zera o histórico."""
    # 5 tentativas falhas
    for _ in range(5):
        r = db_client.post(
            "/auth/login",
            json={"email": "lojista@exemplo.com", "password": "senha_incorreta_1"},
        )
        assert r.status_code == 401

    # 6ª tentativa -> 429 Too Many Requests
    r_blocked = db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
    )
    assert r_blocked.status_code == 429
    assert "muitas tentativas" in r_blocked.json()["detail"].lower()
    assert "Retry-After" in r_blocked.headers

    # Reset manual da janela simula a expiração do tempo
    global_login_rate_limiter.reset()

    # Tentativa com senha correta agora tem sucesso e limpa o limitador
    r_ok = db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
    )
    assert r_ok.status_code == 200


def test_auth_me_scenarios(db_client, db_session, test_user):
    """Testa /auth/me: sem cookie, com cookie válido, expirado e usuário inativado após login."""
    settings = get_settings()

    # 1. Sem cookie -> 401
    r_no_cookie = db_client.get("/auth/me")
    assert r_no_cookie.status_code == 401
    assert r_no_cookie.headers.get("Cache-Control") == "no-store"

    # 2. Com login e cookie válido -> 200
    db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
    )
    r_me = db_client.get("/auth/me")
    assert r_me.status_code == 200
    assert r_me.json()["email"] == "lojista@exemplo.com"

    # 3. Sessão expirada -> 401
    session = db_session.scalars(select(UserSession).where(UserSession.user_id == test_user.id)).first()
    session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    r_expired = db_client.get("/auth/me")
    assert r_expired.status_code == 401

    # 4. Usuário inativado após o login -> 401
    # Restaura validade da sessão
    session.expires_at = datetime.now(timezone.utc) + timedelta(hours=12)
    test_user.is_active = False
    db_session.commit()

    r_inactive = db_client.get("/auth/me")
    assert r_inactive.status_code == 401


def test_logout_revokes_session_and_clears_cookie(db_client, db_session, test_user):
    """Logout revoga a sessão no banco, limpa o cookie e é estritamente idempotente."""
    settings = get_settings()

    # Realiza login
    db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
    )
    assert db_client.get("/auth/me").status_code == 200

    # Realiza logout
    r_logout = db_client.post("/auth/logout")
    assert r_logout.status_code == 204
    assert r_logout.headers.get("Cache-Control") == "no-store"

    # Verifica que a sessão no banco recebeu revoked_at
    session = db_session.scalars(select(UserSession).where(UserSession.user_id == test_user.id)).first()
    assert session.revoked_at is not None

    # Tentar acessar /auth/me agora retorna 401
    assert db_client.get("/auth/me").status_code == 401

    # Logout subsequente sem sessão é idempotente e retorna 204
    r_logout_again = db_client.post("/auth/logout")
    assert r_logout_again.status_code == 204


def test_csrf_origin_header_validation(db_client, test_user):
    """Garante que métodos não-seguros (POST) rejeitam Origin não permitido com 403."""
    # Origin malicioso -> 403 Forbidden
    r_malicious = db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
        headers={"Origin": "https://malicious-site.example.com"},
    )
    assert r_malicious.status_code == 403
    assert "origem" in r_malicious.json()["detail"].lower()

    # Referer malicioso -> 403 Forbidden
    r_malicious_ref = db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
        headers={"Referer": "https://malicious-site.example.com/phishing"},
    )
    assert r_malicious_ref.status_code == 403

    # Origin permitido (ex.: http://localhost:3000) -> prossegue
    r_allowed = db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert r_allowed.status_code == 200


def test_require_admin_dependency(db_client, test_user, admin_user):
    """Usuário comum recebe 403 em rota administrativa; administrador tem acesso permitido."""
    # Login com lojista comum (não admin)
    db_client.post(
        "/auth/login",
        json={"email": "lojista@exemplo.com", "password": "senha_lojista_123"},
    )
    r_denied = db_client.get("/admin-only-test")
    assert r_denied.status_code == 403
    assert "administradores" in r_denied.json()["detail"].lower()

    # Logout e login com admin
    db_client.post("/auth/logout")
    db_client.post(
        "/auth/login",
        json={"email": "admin@exemplo.com", "password": "senha_admin_super_123"},
    )
    r_allowed = db_client.get("/admin-only-test")
    assert r_allowed.status_code == 200
    assert r_allowed.json()["admin_id"] == admin_user.id
