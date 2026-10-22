"""Configuração da aplicação via variáveis de ambiente (pydantic-settings)."""

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "review-redirect"
    environment: str = "development"
    database_url: str  # obrigatória; sem valor padrão para evitar credenciais embutidas
    test_database_url: str | None = None

    # Configurações de autenticação e sessão por cookie
    session_cookie_name: str = "session_id"
    session_ttl_hours: int = 12
    cookie_secure: bool = True
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Limitação de tentativas de login em memória
    login_rate_limit_max_attempts: int = 5
    login_rate_limit_window_seconds: int = 900  # 15 minutos

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    return json.loads(v_str)
                except Exception:
                    pass
            return [origin.strip() for origin in v_str.split(",") if origin.strip()]
        if isinstance(v, (list, tuple)):
            return [str(item).strip() for item in v if str(item).strip()]
        return ["http://localhost:3000", "http://localhost:8000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
