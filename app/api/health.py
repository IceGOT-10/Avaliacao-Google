from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check: não consulta o banco nem expõe configuração."""
    return {"status": "ok"}
