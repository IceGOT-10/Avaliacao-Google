"""Modelo de Estabelecimento (Business)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.business_membership import BusinessMembership
    from app.models.review_link import ReviewLink
    from app.models.review_snapshot import ReviewSnapshot


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    google_review_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="America/Sao_Paulo", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    memberships: Mapped[list["BusinessMembership"]] = relationship(
        "BusinessMembership", back_populates="business", cascade="all, delete-orphan"
    )
    review_links: Mapped[list["ReviewLink"]] = relationship(
        "ReviewLink", back_populates="business", passive_deletes="all"
    )
    review_snapshots: Mapped[list["ReviewSnapshot"]] = relationship(
        "ReviewSnapshot", back_populates="business", passive_deletes="all"
    )