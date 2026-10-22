"""Testes de integridade do modelo de dados contra PostgreSQL real."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.tokens import generate_link_code
from app.models.access_event import AccessEvent
from app.models.business import Business
from app.models.business_membership import BusinessMembership
from app.models.review_link import ReviewLink
from app.models.review_snapshot import ReviewSnapshot
from app.models.user import User


def test_entities_creation_and_relationships(db_session):
    """Valida a criação e navegação dos relacionamentos de todas as entidades."""
    user = User(
        email="proprietario@loja.com",
        password_hash="fake_hash_para_teste",
    )
    db_session.add(user)
    db_session.commit()

    business = Business(
        name="Café Central",
        slug="cafe-central",
        google_review_url="https://g.page/r/cafe-central/review",
    )
    db_session.add(business)
    db_session.commit()

    membership = BusinessMembership(
        user_id=user.id,
        business_id=business.id,
        role="owner",
    )
    db_session.add(membership)

    link = ReviewLink(
        business_id=business.id,
        source="nfc",
        label="Balcão Principal",
        destination_url="https://g.page/r/cafe-central/review",
    )
    db_session.add(link)

    snapshot = ReviewSnapshot(
        business_id=business.id,
        total_reviews=42,
        average_rating=Decimal("4.85"),
        source="manual",
    )
    db_session.add(snapshot)
    db_session.commit()

    event = AccessEvent(
        review_link_id=link.id,
        result="redirected",
        is_probable_bot=False,
    )
    db_session.add(event)
    db_session.commit()

    # Validação de IDs e timestamps
    assert user.id > 0
    assert business.id > 0
    assert link.id > 0
    assert link.code is not None and len(link.code) >= 6
    assert event.id > 0
    assert snapshot.id > 0

    # Navegação reversa e direta
    db_session.refresh(business)
    assert len(business.memberships) == 1
    assert business.memberships[0].user.email == "proprietario@loja.com"
    assert len(business.review_links) == 1
    assert business.review_links[0].label == "Balcão Principal"
    assert len(business.review_snapshots) == 1
    assert business.review_snapshots[0].total_reviews == 42

    db_session.refresh(link)
    assert len(link.access_events) == 1
    assert link.access_events[0].result == "redirected"


def test_user_email_uniqueness(db_session):
    """Verifica que o email de usuário deve ser estritamente único."""
    u1 = User(email="duplicado@loja.com", password_hash="h1")
    u2 = User(email="duplicado@loja.com", password_hash="h2")
    db_session.add(u1)
    db_session.commit()

    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_business_slug_uniqueness(db_session):
    """Verifica que o slug de estabelecimentos é único."""
    b1 = Business(
        name="Loja A",
        slug="mesmo-slug",
        google_review_url="https://g.page/r/1",
    )
    b2 = Business(
        name="Loja B",
        slug="mesmo-slug",
        google_review_url="https://g.page/r/2",
    )
    db_session.add(b1)
    db_session.commit()

    db_session.add(b2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_review_link_code_uniqueness(db_session):
    """Verifica a unicidade estrita do código público do link."""
    b = Business(name="L", slug="l-code", google_review_url="https://g.page/r/1")
    db_session.add(b)
    db_session.commit()

    l1 = ReviewLink(
        business_id=b.id,
        code="codigo_repetido",
        source="qr",
        destination_url="https://g.page/r/1",
    )
    l2 = ReviewLink(
        business_id=b.id,
        code="codigo_repetido",
        source="nfc",
        destination_url="https://g.page/r/1",
    )
    db_session.add(l1)
    db_session.commit()

    db_session.add(l2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_business_membership_uniqueness(db_session):
    """Verifica que não pode haver duplicata de (user_id, business_id)."""
    user = User(email="gerente@loja.com", password_hash="hash")
    business = Business(name="Padaria", slug="padaria", google_review_url="https://g.page/r/padaria")
    db_session.add_all([user, business])
    db_session.commit()

    m1 = BusinessMembership(user_id=user.id, business_id=business.id, role="owner")
    m2 = BusinessMembership(user_id=user.id, business_id=business.id, role="manager")
    db_session.add(m1)
    db_session.commit()

    db_session.add(m2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_email_lowercase_check_constraint(db_session):
    """Verifica que a CheckConstraint barra emails com maiúsculas."""
    user = User(email="EmailComMaiusculas@Loja.com", password_hash="hash")
    db_session.add(user)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_business_membership_role_check_constraint(db_session):
    """Verifica que role fora de ('owner', 'manager') é rejeitada."""
    user = User(email="func@loja.com", password_hash="h")
    business = Business(name="B", slug="b-role", google_review_url="https://g.page/r/1")
    db_session.add_all([user, business])
    db_session.commit()

    membership = BusinessMembership(user_id=user.id, business_id=business.id, role="admin_invalido")
    db_session.add(membership)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_review_link_source_check_constraint(db_session):
    """Verifica que source de review_links deve ser 'nfc', 'qr' ou 'other'."""
    business = Business(name="B", slug="b-source", google_review_url="https://g.page/r/1")
    db_session.add(business)
    db_session.commit()

    link = ReviewLink(
        business_id=business.id,
        source="bluetooth_invalido",
        destination_url="https://g.page/r/1",
    )
    db_session.add(link)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_review_link_destination_url_https_check_constraint(db_session):
    """Verifica que destination_url deve começar com https://."""
    business = Business(name="B", slug="b-https", google_review_url="https://g.page/r/1")
    db_session.add(business)
    db_session.commit()

    link = ReviewLink(
        business_id=business.id,
        source="qr",
        destination_url="http://inseguro.com/avaliacao",
    )
    db_session.add(link)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_access_event_result_check_constraint(db_session):
    """Verifica que result deve ser 'redirected' ou 'blocked_inactive'."""
    business = Business(name="B", slug="b-event", google_review_url="https://g.page/r/1")
    db_session.add(business)
    db_session.commit()
    link = ReviewLink(business_id=business.id, source="qr", destination_url="https://g.page/r/1")
    db_session.add(link)
    db_session.commit()

    event = AccessEvent(
        review_link_id=link.id,
        result="resultado_invalido",
    )
    db_session.add(event)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_review_snapshot_check_constraints(db_session):
    """Verifica as CheckConstraints de review_snapshots (source, total >= 0, rating 0 a 5)."""
    business = Business(name="B", slug="b-snap", google_review_url="https://g.page/r/1")
    db_session.add(business)
    db_session.commit()

    # Total de avaliações negativo
    snap_neg = ReviewSnapshot(
        business_id=business.id,
        total_reviews=-5,
        source="manual",
    )
    db_session.add(snap_neg)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Rating maior que 5.0
    snap_rating_high = ReviewSnapshot(
        business_id=business.id,
        total_reviews=10,
        average_rating=Decimal("5.50"),
        source="manual",
    )
    db_session.add(snap_rating_high)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Source inválida
    snap_invalid_source = ReviewSnapshot(
        business_id=business.id,
        total_reviews=10,
        source="scraped_invalido",
    )
    db_session.add(snap_invalid_source)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_ondelete_restrict_for_business_and_links(db_session):
    """Verifica que RESTRICT impede a exclusão acidental de estabelecimentos e links com histórico."""
    business = Business(name="B", slug="b-restrict", google_review_url="https://g.page/r/1")
    db_session.add(business)
    db_session.commit()

    link = ReviewLink(business_id=business.id, source="qr", destination_url="https://g.page/r/1")
    db_session.add(link)
    db_session.commit()

    event = AccessEvent(review_link_id=link.id, result="redirected")
    db_session.add(event)
    db_session.commit()

    # 1. Tentar deletar link que possui access_events -> RESTRICT bloqueia
    db_session.delete(link)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 2. Tentar deletar business que possui review_links -> RESTRICT bloqueia
    db_session.delete(business)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_ondelete_cascade_for_memberships(db_session):
    """Verifica que a exclusão de user ou business remove memberships em cascata."""
    user = User(email="cascade@loja.com", password_hash="h")
    business = Business(name="B Cascade", slug="b-cascade", google_review_url="https://g.page/r/1")
    db_session.add_all([user, business])
    db_session.commit()

    membership = BusinessMembership(user_id=user.id, business_id=business.id, role="owner")
    db_session.add(membership)
    db_session.commit()

    # Deletar usuário deve remover a membership automaticamente via CASCADE
    db_session.delete(user)
    db_session.commit()

    remaining_memberships = db_session.query(BusinessMembership).filter_by(business_id=business.id).all()
    assert len(remaining_memberships) == 0


def test_generate_link_code_uniqueness_and_format():
    """Valida a geração em lote de códigos aleatórios seguros."""
    codes = {generate_link_code(nbytes=6) for _ in range(1000)}
    assert len(codes) == 1000, "Todos os 1000 códigos gerados devem ser únicos"
    for code in codes:
        assert len(code) >= 6
        assert "/" not in code and "?" not in code and "#" not in code