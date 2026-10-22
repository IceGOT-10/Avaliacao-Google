"""Servi?o de resolu??o e registro de redirecionamento para review_links."""

import logging
import re
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.access_event import AccessEvent
from app.models.review_link import ReviewLink
from app.services.url_validator import validate_destination_url

logger = logging.getLogger(__name__)

# Express?o regular para valida??o do c?digo p?blico gerado via secrets.token_urlsafe
CODE_REGEX = re.compile(r"^[A-Za-z0-9_-]{3,64}$")

# Lista fixa de substrings comuns de User-Agents de bots e crawlers conhecidos
BOT_USER_AGENT_SUBSTRINGS: tuple[str, ...] = (
    "bot",
    "crawler",
    "spider",
    "curl",
    "wget",
    "python-requests",
    "headlesschrome",
    "googlebot",
    "facebookexternalhit",
    "slackbot",
    "whatsapp",
)


class RedirectStatus(str, Enum):
    REDIRECT = "redirect"
    INACTIVE = "inactive"
    NOT_FOUND = "not_found"
    INVALID_DESTINATION = "invalid_destination"


@dataclass(frozen=True)
class RedirectDecision:
    status: RedirectStatus
    destination_url: str | None = None
    detail: str | None = None


def is_valid_code_format(code: str | None) -> bool:
    '''Verifica se o formato e tamanho do c?digo s?o v?lidos antes de consultar o banco.'''
    if not code or not isinstance(code, str):
        return False
    return bool(CODE_REGEX.match(code))


def detect_probable_bot(user_agent: str | None) -> bool | None:
    '''Detecta heuristicamente se o User-Agent ? de um bot/crawler.

    Regras:
    - Se o cabe?alho estiver ausente ou for vazio, retorna None.
    - Se contiver substring de bot/crawler conhecido, retorna True.
    - Caso contr?rio, retorna False.
    - O User-Agent bruto nunca ? persistido nem logado.
    '''
    if user_agent is None:
        return None
    ua_clean = user_agent.strip().lower()
    if not ua_clean:
        return None
    return any(bot_token in ua_clean for bot_token in BOT_USER_AGENT_SUBSTRINGS)


def _record_access_event(
    db: Session,
    review_link_id: int,
    result: str,
    user_agent: str | None,
) -> None:
    '''Persiste um evento de acesso na mesma sess?o de forma resiliente.'''
    try:
        is_bot = detect_probable_bot(user_agent)
        event = AccessEvent(
            review_link_id=review_link_id,
            result=result,
            is_probable_bot=is_bot,
        )
        db.add(event)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(
            "Falha ao persistir access_event para review_link_id=%s: %s",
            review_link_id,
            type(exc).__name__,
        )


def resolve_and_record_redirect(
    db: Session,
    code: str,
    user_agent: str | None = None,
) -> RedirectDecision:
    '''Resolve o review_link pelo c?digo, registra o evento de acesso e decide a a??o.

    Regras de neg?cio:
    - C?digo fora do formato permitido: retorna NOT_FOUND (404) sem consultar o banco.
    - C?digo inexistente no banco: retorna NOT_FOUND (404), sem gravar evento.
    - Link inativo (is_active=False ou deactivated_at n?o nulo): grava evento 'blocked_inactive'
      e retorna INACTIVE (410).
    - Link ativo com destination_url inv?lida no validador anti-open-redirect:
      N?O redireciona, N?O grava evento (evita viola??o da check constraint),
      loga apenas link id e motivo, e retorna INVALID_DESTINATION (502).
    - Link ativo com destination_url v?lida: grava evento 'redirected'
      e retorna REDIRECT (307 com destination_url).
    '''
    # 1. Valida??o do formato do c?digo antes da consulta ao banco
    if not is_valid_code_format(code):
        return RedirectDecision(
            status=RedirectStatus.NOT_FOUND,
            detail="Link de avalia??o n?o encontrado.",
        )

    # 2. Consulta do link no banco
    stmt = select(ReviewLink).where(ReviewLink.code == code)
    link = db.scalars(stmt).first()
    if not link:
        return RedirectDecision(
            status=RedirectStatus.NOT_FOUND,
            detail="Link de avalia??o n?o encontrado.",
        )

    # 3. Verifica??o de status ativo / desativado
    if not link.is_active or link.deactivated_at is not None:
        _record_access_event(
            db=db,
            review_link_id=link.id,
            result="blocked_inactive",
            user_agent=user_agent,
        )
        return RedirectDecision(
            status=RedirectStatus.INACTIVE,
            detail="Este link de avalia??o foi desativado.",
        )

    # 4. Valida??o anti-open-redirect do destino
    if not validate_destination_url(link.destination_url):
        logger.warning(
            "Link review_link_id=%s rejeitado: destination_url fora da allowlist autorizada.",
            link.id,
        )
        return RedirectDecision(
            status=RedirectStatus.INVALID_DESTINATION,
            detail="Destino do link inv?lido ou n?o autorizado.",
        )

    # 5. Link ativo e destino v?lido
    _record_access_event(
        db=db,
        review_link_id=link.id,
        result="redirected",
        user_agent=user_agent,
    )
    return RedirectDecision(
        status=RedirectStatus.REDIRECT,
        destination_url=link.destination_url,
    )
