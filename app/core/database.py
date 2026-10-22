"""Engine e sessão SQLAlchemy 2.x com convenção de nomenclatura de constraints."""

from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

POSTGRES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa com convenção de nomenclatura para o schema."""

    metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)


# create_engine é preguiçoso: não abre conexão até o primeiro uso.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependência FastAPI que fornece uma sessão por requisição."""
    with SessionLocal() as session:
        yield session