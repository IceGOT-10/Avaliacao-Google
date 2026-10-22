"""Operações de lojas e links."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.tokens import generate_link_code
from app.models.business import Business
from app.models.review_link import ReviewLink
from app.schemas.business import BusinessCreate, BusinessUpdate, LinkCreate, LinkUpdate


def create_business(db: Session, data: BusinessCreate) -> Business:
    business = Business(**data.model_dump())
    db.add(business)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(business)
    return business


def update_business(db: Session, business: Business, data: BusinessUpdate) -> Business:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(business, key, value)
    db.commit()
    db.refresh(business)
    return business


def create_link(db: Session, business: Business, data: LinkCreate) -> ReviewLink:
    destination = data.destination_url or business.google_review_url
    payload = data.model_dump(exclude={"destination_url"})
    for _ in range(5):
        link = ReviewLink(business_id=business.id, destination_url=destination, **payload)
        db.add(link)
        try:
            db.commit()
            db.refresh(link)
            return link
        except IntegrityError:
            db.rollback()
    raise RuntimeError("Não foi possível gerar um código único para o link.")


def update_link(db: Session, link: ReviewLink, data: LinkUpdate) -> ReviewLink:
    values = data.model_dump(exclude_unset=True, exclude={"code", "source", "destination_url"})
    if "is_active" in values:
        from datetime import datetime, timezone
        link.is_active = values.pop("is_active")
        link.deactivated_at = None if link.is_active else datetime.now(timezone.utc)
    for key, value in values.items():
        setattr(link, key, value)
    db.commit()
    db.refresh(link)
    return link


def public_link_payload(link: ReviewLink) -> dict:
    base = get_settings().public_base_url
    return {
        "id": link.id, "code": link.code, "source": link.source, "label": link.label,
        "destination_url": link.destination_url, "is_active": link.is_active,
        "created_at": link.created_at, "public_path": f"/r/{link.code}",
        "public_url": f"{base.rstrip('/')}/r/{link.code}" if base else None,
    }
