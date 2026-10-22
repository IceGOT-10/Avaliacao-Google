"""Modelo de Link de Avaliação (ReviewLink)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tokens import generate_link_code

if TYPE_CHECKING:
    from app.models.access_event import AccessEvent
    from app.models.business import Business


class ReviewLink(Base):
    __tablename__ = "review_links"
    __table_args__ = (
        CheckConstraint("source IN ('nfc', 'qr', 'other')", name="source_valid"),
        CheckConstraint("destination_url LIKE 'https://%'", name="destination_url_https"),
        Index("ix_review_links_business_id", "business_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=generate_link_code, nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    business: Mapped["Business"] = relationship("Business", back_populates="review_links")
    access_events: Mapped[list["AccessEvent"]] = relationship(
        "AccessEvent", back_populates="review_link", passive_deletes="all"
    )