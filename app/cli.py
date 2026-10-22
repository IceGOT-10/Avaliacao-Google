"""Interface de Linha de Comando (CLI) administrativa da aplicação."""

import argparse
import getpass
import sys
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password, validate_password_policy
from app.models.user import User
from app.models.business import Business
from app.models.business_membership import BusinessMembership


def _normalize_email(email: str) -> str | None:
    value = email.strip().lower() if isinstance(email, str) else ""
    return value if value and "@" in value and len(value) <= 254 else None


def _prompt_password(kind: str, password_prompt: Callable[[], tuple[str, str]] | None) -> tuple[str, str]:
    if password_prompt is not None:
        return password_prompt()
    return getpass.getpass(f"Senha do {kind}: "), getpass.getpass("Confirme a senha: ")


def run_create_admin(
    email: str,
    db: Session | None = None,
    password_prompt: Callable[[], tuple[str, str]] | None = None,
) -> int:
    """Cria um usuário administrador com senha segura fornecida interativamente."""
    normalized_email = _normalize_email(email)
    if not normalized_email:
        sys.stderr.write("Erro: informe um endereço de email válido.\n")
        return 1

    pwd1, pwd2 = _prompt_password("administrador", password_prompt)

    if pwd1 != pwd2:
        sys.stderr.write("Erro: as senhas digitadas não coincidem.\n")
        return 1

    valid, err_msg = validate_password_policy(pwd1)
    if not valid:
        sys.stderr.write(f"Erro na política de senha: {err_msg}\n")
        return 1

    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        existing = db.scalars(select(User).where(User.email == normalized_email)).first()
        if existing:
            sys.stderr.write(f"Erro: já existe um usuário cadastrado com o email '{normalized_email}'.\n")
            return 1

        admin_user = User(
            email=normalized_email,
            password_hash=hash_password(pwd1),
            is_active=True,
            is_admin=True,
        )
        db.add(admin_user)
        db.commit()
        sys.stdout.write(f"Administrador criado com sucesso: {normalized_email}\n")
        return 0
    except Exception as exc:
        db.rollback()
        sys.stderr.write(f"Erro ao salvar administrador no banco de dados: {exc}\n")
        return 1
    finally:
        if owns_session:
            db.close()


def run_create_user(email: str, db: Session | None = None, password_prompt: Callable[[], tuple[str, str]] | None = None) -> int:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return 1
    pwd1, pwd2 = _prompt_password("usuário", password_prompt)
    if pwd1 != pwd2:
        return 1
    valid, _ = validate_password_policy(pwd1)
    if not valid:
        return 1
    owns_session = db is None
    db = db or SessionLocal()
    try:
        if db.scalars(select(User).where(User.email == normalized_email)).first():
            return 1
        db.add(User(email=normalized_email, password_hash=hash_password(pwd1), is_active=True, is_admin=False))
        db.commit()
        return 0
    except Exception:
        db.rollback()
        return 1
    finally:
        if owns_session:
            db.close()


def run_grant_access(email: str, business_slug: str, role: str, db: Session | None = None) -> int:
    normalized_email = _normalize_email(email)
    if not normalized_email or role not in {"owner", "manager"}:
        return 1
    owns_session = db is None
    db = db or SessionLocal()
    try:
        user = db.scalars(select(User).where(User.email == normalized_email)).first()
        business = db.scalars(select(Business).where(Business.slug == business_slug)).first()
        if not user or not business:
            return 1
        membership = db.scalars(select(BusinessMembership).where(
            BusinessMembership.user_id == user.id, BusinessMembership.business_id == business.id,
        )).first()
        if membership:
            membership.role = role
        else:
            db.add(BusinessMembership(user_id=user.id, business_id=business.id, role=role))
        db.commit()
        return 0
    except Exception:
        db.rollback()
        return 1
    finally:
        if owns_session:
            db.close()


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Utilitários administrativos para o review-redirect.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    create_admin_parser = subparsers.add_parser(
        "create-admin",
        help="Cria um novo usuário com privilégios de administrador.",
    )
    create_admin_parser.add_argument(
        "--email",
        required=True,
        help="Email do administrador (será convertido para minúsculas).",
    )

    create_user_parser = subparsers.add_parser("create-user")
    create_user_parser.add_argument("--email", required=True)
    grant_parser = subparsers.add_parser("grant-access")
    grant_parser.add_argument("--email", required=True)
    grant_parser.add_argument("--business-slug", required=True)
    grant_parser.add_argument("--role", required=True, choices=["owner", "manager"])

    parsed = parser.parse_args(args)

    if parsed.subcommand == "create-admin":
        return run_create_admin(email=parsed.email)
    if parsed.subcommand == "create-user":
        return run_create_user(email=parsed.email)
    if parsed.subcommand == "grant-access":
        return run_grant_access(email=parsed.email, business_slug=parsed.business_slug, role=parsed.role)

    return 0


if __name__ == "__main__":
    sys.exit(main())
