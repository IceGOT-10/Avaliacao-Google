"""Modelo de Usuário (User)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.business_membership import BusinessMembership


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lower"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    memberships: Mapped[list["BusinessMembership"]] = relationship(
        "BusinessMembership", back_populates="user", cascade="all, delete-orphan"
    )