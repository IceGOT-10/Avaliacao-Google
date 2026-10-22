"""Testes de integra??o para o fluxo p?blico GET /r/{code} contra PostgreSQL real."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent
from app.models.business import Business
from app.models.review_link import ReviewLink
from app.services.redirect_service import detect_probable_bot


@pytest.fixture
def test_business(db_session: Session) -> Business:
    """Fixture de estabelecimento para associar aos review_links."""
    b = Business(
        name="Caf? Central",
        slug="cafe-central",
        google_review_url="https://g.page/r/cafe-central",
    )
    db_session.add(b)
    db_session.commit()
    return b


def test_redirect_active_link_success(db_client, db_session, test_business):
    """Link ativo redireciona (307) para a destination_url, com Cache-Control e 1 access_event."""
    destination = "https://g.page/r/Cb_8Kxyz123"
    link = ReviewLink(
        business_id=test_business.id,
        code="link_valido_01",
        source="qr",
        destination_url=destination,
        is_active=True,
    )
    db_session.add(link)
    db_session.commit()

    response = db_client.get("/r/link_valido_01", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers.get("Location") == destination
    assert response.headers.get("Cache-Control") == "no-store"

    # Verifica persist?ncia do access_event
    events = db_session.scalars(
        select(AccessEvent).where(AccessEvent.review_link_id == link.id)
    ).all()
    assert len(events) == 1
    assert events[0].result == "redirected"


def test_redirect_inactive_link_returns_410(db_client, db_session, test_business):
    """Link desativado retorna 410 Gone, sem Location, com Cache-Control e evento blocked_inactive."""
    link = ReviewLink(
        business_id=test_business.id,
        code="link_inativo_02",
        source="nfc",
        destination_url="https://g.page/r/inativo",
        is_active=False,
        deactivated_at=datetime.now(timezone.utc),
    )
    db_session.add(link)
    db_session.commit()

    response = db_client.get("/r/link_inativo_02", follow_redirects=False)

    assert response.status_code == 410
    assert "Location" not in response.headers
    assert response.headers.get("Cache-Control") == "no-store"
    assert "desativado" in response.json().get("detail", "").lower()

    events = db_session.scalars(
        select(AccessEvent).where(AccessEvent.review_link_id == link.id)
    ).all()
    assert len(events) == 1
    assert events[0].result == "blocked_inactive"


def test_redirect_nonexistent_code_returns_404(db_client, db_session):
    """C?digo inexistente com formato v?lido retorna 404 e N?O grava nenhum evento."""
    response = db_client.get("/r/codigo_inexistente_999", follow_redirects=False)

    assert response.status_code == 404
    assert response.headers.get("Cache-Control") == "no-store"

    events = db_session.scalars(select(AccessEvent)).all()
    assert len(events) == 0


@pytest.mark.parametrize(
    "malformed_code",
    [
        "a",  # Curto demais (< 3)
        "ab",
        "codigo!invalido@",
        "codigo com espaco",
        "codigo/com/barra",
        "a" * 65,  # Longo demais (> 64)
    ],
)
def test_redirect_malformed_code_returns_404_without_query(db_client, db_session, malformed_code):
    """C?digo fora da especifica??o ? rejeitado com 404 imediatamente sem registrar evento."""
    response = db_client.get(f"/r/{malformed_code}", follow_redirects=False)

    assert response.status_code == 404
    events = db_session.scalars(select(AccessEvent)).all()
    assert len(events) == 0


def test_redirect_destination_outside_allowlist_returns_502(db_client, db_session, test_business):
    """Destino fora da allowlist retorna 502, sem Location, sem evento e sem vazar URL nos dados."""
    evil_url = "https://evil.example/phishing"
    link = ReviewLink(
        business_id=test_business.id,
        code="link_com_evil_url",
        source="qr",
        destination_url=evil_url,
        is_active=True,
    )
    db_session.add(link)
    db_session.commit()

    response = db_client.get("/r/link_com_evil_url", follow_redirects=False)

    assert response.status_code == 502
    assert "Location" not in response.headers
    assert response.headers.get("Cache-Control") == "no-store"
    # N?o vaza a URL de destino nem IDs internos no corpo de erro
    assert evil_url not in response.text
    assert str(link.id) not in response.text

    # CHECK constraint n?o aceitaria outro result; garante que NENHUM evento foi criado
    events = db_session.scalars(select(AccessEvent)).all()
    assert len(events) == 0


def test_bot_detection_heuristics(db_client, db_session, test_business):
    """Valida a detec??o heur?stica de bots pelo cabe?alho User-Agent sem armazen?-lo."""
    destination = "https://g.page/r/test-bot"
    link = ReviewLink(
        business_id=test_business.id,
        code="link_bot_test",
        source="qr",
        destination_url=destination,
        is_active=True,
    )
    db_session.add(link)
    db_session.commit()

    # 1. User-Agent de bot conhecido -> is_probable_bot = True
    db_client.get(
        "/r/link_bot_test",
        headers={"User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)"},
        follow_redirects=False,
    )
    # 2. User-Agent comum de navegador -> is_probable_bot = False
    db_client.get(
        "/r/link_bot_test",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"},
        follow_redirects=False,
    )
    # 3. Requisi??o sem cabe?alho User-Agent -> is_probable_bot = None
    # Removemos o User-Agent default do TestClient para simular cliente HTTP sem UA
    original_ua = db_client.headers.pop("user-agent", None)
    try:
        db_client.get("/r/link_bot_test", follow_redirects=False)
    finally:
        if original_ua is not None:
            db_client.headers["user-agent"] = original_ua

    events = db_session.scalars(
        select(AccessEvent).where(AccessEvent.review_link_id == link.id).order_by(AccessEvent.id)
    ).all()

    assert len(events) == 3
    assert events[0].is_probable_bot is True
    assert events[1].is_probable_bot is False
    assert events[2].is_probable_bot is None


def test_detect_probable_bot_unit():
    """Testes unit?rios isolados da fun??o pura detect_probable_bot."""
    assert detect_probable_bot(None) is None
    assert detect_probable_bot("") is None
    assert detect_probable_bot("   ") is None
    assert detect_probable_bot("Googlebot/2.1") is True
    assert detect_probable_bot("curl/8.4.0") is True
    assert detect_probable_bot("Wget/1.21") is True
    assert detect_probable_bot("python-requests/2.31.0") is True
    assert detect_probable_bot("facebookexternalhit/1.1") is True
    assert detect_probable_bot("Slackbot-LinkExpanding 1.0") is True
    assert detect_probable_bot("WhatsApp/2.23") is True
    assert detect_probable_bot("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is False


def test_privacy_no_ip_or_user_agent_columns_in_access_events():
    """Inspeciona o modelo e a tabela access_events para garantir privacidade estrita por design."""
    mapper = inspect(AccessEvent)
    column_names = {col.key for col in mapper.columns}

    expected_columns = {"id", "review_link_id", "occurred_at", "result", "is_probable_bot"}
    assert column_names == expected_columns, f"Colunas encontradas: {column_names}"

    # Garante aus?ncia total de colunas de IP, UA, fingerprint, geolocaliza??o
    prohibited_fields = {
        "ip",
        "ip_address",
        "client_ip",
        "user_agent",
        "ua",
        "raw_ua",
        "fingerprint",
        "geolocation",
        "country",
        "city",
    }
    assert column_names.isdisjoint(prohibited_fields)


def test_consecutive_accesses_generate_multiple_events(db_client, db_session, test_business):
    """Dois acessos consecutivos ao mesmo link ativo geram exatamente 2 eventos independentes."""
    link = ReviewLink(
        business_id=test_business.id,
        code="link_duplo_acesso",
        source="nfc",
        destination_url="https://maps.app.goo.gl/3wJxyzABC123",
        is_active=True,
    )
    db_session.add(link)
    db_session.commit()

    r1 = db_client.get("/r/link_duplo_acesso", follow_redirects=False)
    r2 = db_client.get("/r/link_duplo_acesso", follow_redirects=False)

    assert r1.status_code == 307
    assert r2.status_code == 307

    events = db_session.scalars(
        select(AccessEvent).where(AccessEvent.review_link_id == link.id)
    ).all()
    assert len(events) == 2
    assert all(e.result == "redirected" for e in events)


def test_health_check_remains_functional_without_database(client):
    """Garante que /health continua respondendo 200 OK sem depender da conex?o de banco."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
