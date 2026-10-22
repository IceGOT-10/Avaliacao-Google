from fastapi import FastAPI

from app.api import auth, businesses, health, redirect
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.middleware("http")
async def private_api_no_store(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(health.router)
app.include_router(redirect.router)
app.include_router(auth.router)
app.include_router(businesses.router)
