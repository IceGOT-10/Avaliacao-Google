"""Engine e sessão SQLAlchemy 2.x. Nenhum modelo definido nesta etapa."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base declarativa para os modelos futuros."""


# create_engine é preguiçoso: não abre conexão até o primeiro uso.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependência FastAPI que fornece uma sessão por requisição."""
    with SessionLocal() as session:
        yield session
