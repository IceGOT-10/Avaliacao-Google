from fastapi import FastAPI

from app.api import health, redirect
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.include_router(health.router)
app.include_router(redirect.router)
