"""Testes essenciais de isolamento multi-loja e CRUD de links."""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.business import Business
from app.models.business_membership import BusinessMembership
from app.models.user import User


def _user(db: Session, email: str, admin: bool = False) -> User:
    value = User(email=email, password_hash=hash_password("senha_teste_12345"), is_admin=admin)
    db.add(value)
    db.commit()
    return value


def _business(db: Session, slug: str) -> Business:
    value = Business(name=slug.title(), slug=slug, google_review_url="https://g.page/r/test")
    db.add(value)
    db.commit()
    return value


def _login(client, email: str):
    response = client.post("/auth/login", json={"email": email, "password": "senha_teste_12345"})
    assert response.status_code == 200


def test_business_access_isolated_and_manager_cannot_edit(db_client, db_session):
    owner = _user(db_session, "owner@example.com")
    b1 = _business(db_session, "loja-um")
    b2 = _business(db_session, "loja-dois")
    db_session.add(BusinessMembership(user_id=owner.id, business_id=b1.id, role="manager"))
    db_session.commit()
    _login(db_client, owner.email)

    assert db_client.get(f"/api/businesses/{b1.id}").status_code == 200
    assert db_client.get(f"/api/businesses/{b2.id}").status_code == 404
    assert db_client.patch(f"/api/businesses/{b1.id}", json={"name": "Novo"}).status_code == 403
    created = db_client.post(f"/api/businesses/{b1.id}/links", json={"source": "qr"})
    assert created.status_code == 201
    link_id = created.json()["id"]
    assert db_client.patch(f"/api/links/{link_id}", json={"is_active": False}).status_code == 200


def test_admin_can_create_business_and_anonymous_api_is_401(db_client, db_session):
    assert db_client.get("/api/businesses").status_code == 401
    admin = _user(db_session, "admin@example.com", admin=True)
    _login(db_client, admin.email)
    response = db_client.post("/api/businesses", json={
        "name": "Nova Loja", "slug": "nova-loja",
        "google_review_url": "https://g.page/r/test",
    })
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"


def test_link_immutability_and_inactive_business(db_client, db_session):
    owner = _user(db_session, "owner2@example.com")
    business = _business(db_session, "loja-inativa")
    db_session.add(BusinessMembership(user_id=owner.id, business_id=business.id, role="owner"))
    db_session.commit()
    _login(db_client, owner.email)
    created = db_client.post(f"/api/businesses/{business.id}/links", json={"source": "nfc"})
    assert created.status_code == 201
    assert db_client.patch(f"/api/links/{created.json()['id']}", json={"code": "outro"}).status_code == 422
    business.is_active = False
    db_session.commit()
    assert db_client.post(f"/api/businesses/{business.id}/links", json={"source": "other"}).status_code == 409
