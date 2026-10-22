"""Endpoints privados de lojas e links."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_business_access, get_current_user, require_admin, verify_csrf_origin
from app.core.database import get_db
from app.models.business import Business
from app.models.review_link import ReviewLink
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessResponse, BusinessUpdate, LinkCreate, LinkResponse, LinkUpdate
from app.services.business_service import create_business, create_link, public_link_payload, update_business, update_link

router = APIRouter(prefix="/api", tags=["businesses"])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/businesses", response_model=list[BusinessResponse])
def list_businesses(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), is_active: bool | None = None):
    _no_store(response)
    query = select(Business)
    if not current_user.is_admin:
        query = query.join(Business.memberships).where(Business.memberships.any(user_id=current_user.id))
    if is_active is not None:
        query = query.where(Business.is_active == is_active)
    return db.scalars(query.order_by(Business.id).offset(offset).limit(limit)).all()


@router.post("/businesses", response_model=BusinessResponse, status_code=201, dependencies=[Depends(verify_csrf_origin)])
def create_business_endpoint(data: BusinessCreate, response: Response, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    _no_store(response)
    try:
        return create_business(db, data)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Slug já cadastrado.", headers={"Cache-Control": "no-store"})


@router.get("/businesses/{business_id}", response_model=BusinessResponse)
def get_business(response: Response, business: tuple = Depends(get_business_access())):
    _no_store(response)
    return business[0]


@router.patch("/businesses/{business_id}", response_model=BusinessResponse, dependencies=[Depends(verify_csrf_origin)])
def patch_business(data: BusinessUpdate, response: Response, business: tuple = Depends(get_business_access("owner")), db: Session = Depends(get_db)):
    _no_store(response)
    return update_business(db, business[0], data)


@router.get("/businesses/{business_id}/links", response_model=list[LinkResponse])
def list_links(response: Response, business: tuple = Depends(get_business_access()), db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), source: str | None = None, is_active: bool | None = None):
    _no_store(response)
    query = select(ReviewLink).where(ReviewLink.business_id == business[0].id)
    if source is not None:
        query = query.where(ReviewLink.source == source)
    if is_active is not None:
        query = query.where(ReviewLink.is_active == is_active)
    links = db.scalars(query.order_by(ReviewLink.id).offset(offset).limit(limit)).all()
    return [public_link_payload(link) for link in links]


@router.post("/businesses/{business_id}/links", response_model=LinkResponse, status_code=201, dependencies=[Depends(verify_csrf_origin)])
def post_link(data: LinkCreate, response: Response, business: tuple = Depends(get_business_access()), db: Session = Depends(get_db)):
    _no_store(response)
    if not business[0].is_active:
        raise HTTPException(status_code=409, detail="Loja inativa.", headers={"Cache-Control": "no-store"})
    try:
        return public_link_payload(create_link(db, business[0], data))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc), headers={"Cache-Control": "no-store"})


@router.patch("/links/{link_id}", response_model=LinkResponse, dependencies=[Depends(verify_csrf_origin)])
def patch_link(link_id: int, data: LinkUpdate, response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _no_store(response)
    link = db.get(ReviewLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado.", headers={"Cache-Control": "no-store"})
    business = db.get(Business, link.business_id)
    if current_user.is_admin:
        role = "admin"
    else:
        membership = next((m for m in business.memberships if m.user_id == current_user.id), None)
        if not membership:
            raise HTTPException(status_code=404, detail="Link não encontrado.", headers={"Cache-Control": "no-store"})
        role = membership.role
    if role not in {"manager", "owner", "admin"}:
        raise HTTPException(status_code=403, detail="Permissão insuficiente.", headers={"Cache-Control": "no-store"})
    return public_link_payload(update_link(db, link, data))
