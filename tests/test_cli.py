"""Testes para a CLI administrativa de criação de admin (app/cli.py)."""

import pytest
from sqlalchemy import select

from app.cli import main, run_create_admin
from app.core.security import verify_password
from app.models.user import User


def test_cli_create_admin_success(db_session, monkeypatch):
    """CLI cria usuário admin com email normalizado e senha com hash seguro."""
    password = "senha_admin_forte_123"

    # Simula entrada interativa do getpass
    monkeypatch.setattr("getpass.getpass", lambda prompt="": password)

    result = run_create_admin(
        email="NovoAdmin@Empresa.COM",
        db=db_session,
    )
    assert result == 0

    user = db_session.scalars(select(User).where(User.email == "novoadmin@empresa.com")).first()
    assert user is not None
    assert user.is_admin is True
    assert user.is_active is True
    assert verify_password(user.password_hash, password) is True


def test_cli_create_admin_mismatched_passwords(db_session):
    """CLI rejeita senhas que não coincidem."""
    result = run_create_admin(
        email="admin2@empresa.com",
        db=db_session,
        password_prompt=lambda: ("senha_um_123456", "senha_dois_123456"),
    )
    assert result == 1
    user = db_session.scalars(select(User).where(User.email == "admin2@empresa.com")).first()
    assert user is None


def test_cli_create_admin_violates_password_policy(db_session):
    """CLI rejeita senhas curtas (menor que 12 caracteres)."""
    result = run_create_admin(
        email="admin3@empresa.com",
        db=db_session,
        password_prompt=lambda: ("curta123", "curta123"),
    )
    assert result == 1
    user = db_session.scalars(select(User).where(User.email == "admin3@empresa.com")).first()
    assert user is None


def test_cli_create_admin_duplicate_email(db_session):
    """CLI não permite criar dois administradores com o mesmo email."""
    # Cria o primeiro
    res1 = run_create_admin(
        email="duplicado@empresa.com",
        db=db_session,
        password_prompt=lambda: ("senha_valida_1234", "senha_valida_1234"),
    )
    assert res1 == 0

    # Tenta criar com o mesmo email (maiúsculo)
    res2 = run_create_admin(
        email="DUPLICADO@empresa.com",
        db=db_session,
        password_prompt=lambda: ("senha_valida_1234", "senha_valida_1234"),
    )
    assert res2 == 1


def test_cli_main_entrypoint(db_session, monkeypatch):
    """Valida a execução de main(['create-admin', '--email', ...])."""
    password = "senha_via_main_1234"
    monkeypatch.setattr("getpass.getpass", lambda prompt="": password)
    monkeypatch.setattr("app.cli.SessionLocal", lambda: db_session)

    exit_code = main(["create-admin", "--email", "cli_main@empresa.com"])
    assert exit_code == 0

    user = db_session.scalars(select(User).where(User.email == "cli_main@empresa.com")).first()
    assert user is not None
    assert user.is_admin is True
