"""Configurações globais e fixtures do Pytest."""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Cliente HTTP de teste para rotas FastAPI (não depende de banco)."""
    return TestClient(app)


def get_verified_test_db_url() -> str:
    """Obtém e valida estritamente a URL do banco de teste."""
    settings = get_settings()
    test_url = os.environ.get("TEST_DATABASE_URL") or settings.test_database_url

    if not test_url:
        current_url = make_url(settings.database_url)
        if current_url.database and current_url.database.endswith("_test"):
            test_url = settings.database_url
        else:
            raise RuntimeError(
                "TEST_DATABASE_URL não configurada. Defina a variável de ambiente TEST_DATABASE_URL "
                "apontando para uma base de testes dedicada (ex.: review_redirect_test)."
            )

    parsed = make_url(test_url)
    if not parsed.database or not parsed.database.endswith("_test"):
        raise RuntimeError(
            f"Violação de segurança: o banco de testes deve terminar obrigatoriamente com '_test'. "
            f"Nome recebido: '{parsed.database}'."
        )

    return test_url


@pytest.fixture(scope="session")
def test_engine():
    """Engine conectado ao banco de teste e com migrações Alembic aplicadas."""
    test_url = get_verified_test_db_url()

    # Aplica migrações Alembic no banco de teste
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_url.replace("%", "%%"))
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(test_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Iterator[Session]:
    """Sessão de banco isolada para testes, com limpeza ao final."""
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Limpeza reversa de tabelas para garantir isolamento entre testes
        with test_engine.begin() as conn:
            conn.execute(
                text(
                    "TRUNCATE TABLE user_sessions, access_events, review_snapshots, review_links, "
                    "business_memberships, businesses, users RESTART IDENTITY CASCADE;"
                )
            )
        session.close()


@pytest.fixture
def db_client(db_session: Session) -> Iterator[TestClient]:
    """TestClient configurado com override de get_db apontando para a db_session do banco _test."""
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app, base_url="https://testserver", follow_redirects=False) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
