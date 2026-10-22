"""Endpoint p?blico de redirecionamento de avalia??o Google: GET /r/{code}."""

from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.redirect_service import (
    RedirectDecision,
    RedirectStatus,
    resolve_and_record_redirect,
)

router = APIRouter(tags=["redirect"])


@router.get("/r/{code}")
def redirect_to_review(
    code: str,
    user_agent: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Response:
    '''Resolve o review_link ativo, registra o access_event e redireciona (307).'''
    decision: RedirectDecision = resolve_and_record_redirect(
        db=db,
        code=code,
        user_agent=user_agent,
    )

    headers = {"Cache-Control": "no-store"}

    if decision.status == RedirectStatus.REDIRECT:
        return RedirectResponse(
            url=decision.destination_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers=headers,
        )

    if decision.status == RedirectStatus.INACTIVE:
        return JSONResponse(
            status_code=status.HTTP_410_GONE,
            content={"detail": decision.detail or "Link desativado."},
            headers=headers,
        )

    if decision.status == RedirectStatus.NOT_FOUND:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": decision.detail or "Link n?o encontrado."},
            headers=headers,
        )

    if decision.status == RedirectStatus.INVALID_DESTINATION:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": decision.detail or "Destino do link inv?lido ou n?o autorizado."},
            headers=headers,
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno de redirecionamento."},
        headers=headers,
    )
