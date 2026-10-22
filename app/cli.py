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


def run_create_admin(
    email: str,
    db: Session | None = None,
    password_prompt: Callable[[], tuple[str, str]] | None = None,
) -> int:
    """Cria um usuário administrador com senha segura fornecida interativamente."""
    if not email or "@" not in email:
        sys.stderr.write("Erro: informe um endereço de email válido.\n")
        return 1

    normalized_email = email.strip().lower()

    if password_prompt is not None:
        pwd1, pwd2 = password_prompt()
    else:
        pwd1 = getpass.getpass("Senha do administrador: ")
        pwd2 = getpass.getpass("Confirme a senha: ")

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

    parsed = parser.parse_args(args)

    if parsed.subcommand == "create-admin":
        return run_create_admin(email=parsed.email)

    return 0


if __name__ == "__main__":
    sys.exit(main())
