"""Modelo de Evento de Acesso (AccessEvent).

Privacidade por design: não armazena IP (nem hasheado), user-agent bruto, fingerprint ou geolocalização.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.review_link import ReviewLink


class AccessEvent(Base):
    __tablename__ = "access_events"
    __table_args__ = (
        CheckConstraint(
            "result IN ('redirected', 'blocked_inactive')",
            name="result_valid",
        ),
        Index("ix_access_events_link_occurred", "review_link_id", "occurred_at"),
        Index("ix_access_events_occurred_at", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    review_link_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("review_links.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    is_probable_bot: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    review_link: Mapped["ReviewLink"] = relationship(
        "ReviewLink", back_populates="access_events"
    )