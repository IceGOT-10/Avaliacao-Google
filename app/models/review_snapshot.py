"""Modelo de Snapshot de Avaliações (ReviewSnapshot)."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.business import Business


class ReviewSnapshot(Base):
    __tablename__ = "review_snapshots"
    __table_args__ = (
        CheckConstraint("total_reviews >= 0", name="total_reviews_non_negative"),
        CheckConstraint(
            "average_rating IS NULL OR (average_rating >= 0 AND average_rating <= 5)",
            name="average_rating_range",
        ),
        CheckConstraint("source IN ('manual', 'google_api')", name="source_valid"),
        Index("ix_review_snapshots_business_captured", "business_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total_reviews: Mapped[int] = mapped_column(nullable=False)
    average_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ok", nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    business: Mapped["Business"] = relationship(
        "Business", back_populates="review_snapshots"
    )