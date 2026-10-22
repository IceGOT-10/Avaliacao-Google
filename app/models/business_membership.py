"""Modelo de Associação Loja-Usuário (BusinessMembership)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.user import User


class BusinessMembership(Base):
    __tablename__ = "business_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "business_id", name="uq_business_memberships_user_business"),
        CheckConstraint("role IN ('owner', 'manager')", name="role_valid"),
        Index("ix_business_memberships_business_id", "business_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    business: Mapped["Business"] = relationship("Business", back_populates="memberships")