"""Schemas públicos de lojas e links."""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.url_validator import validate_destination_url


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=64)
    google_review_url: str = Field(max_length=2048)
    timezone: str = "America/Sao_Paulo"

    @field_validator("google_review_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        if not validate_destination_url(value):
            raise ValueError("URL de avaliação inválida ou não autorizada.")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Fuso horário inválido.")
        return value


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    google_review_url: str | None = Field(default=None, max_length=2048)
    timezone: str | None = None
    is_active: bool | None = None

    @field_validator("google_review_url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        if value is not None and not validate_destination_url(value):
            raise ValueError("URL de avaliação inválida ou não autorizada.")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Fuso horário inválido.")
        return value


class BusinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    google_review_url: str
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LinkCreate(BaseModel):
    source: Literal["nfc", "qr", "other"]
    label: str | None = Field(default=None, max_length=100)
    destination_url: str | None = Field(default=None, max_length=2048)

    @field_validator("destination_url")
    @classmethod
    def valid_url(cls, value: str | None) -> str | None:
        if value is not None and not validate_destination_url(value):
            raise ValueError("URL de destino inválida ou não autorizada.")
        return value


class LinkUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    code: str | None = None
    source: str | None = None
    destination_url: str | None = None

    @model_validator(mode="after")
    def immutable_fields(self):
        if any(getattr(self, field) is not None for field in ("code", "source", "destination_url")):
            raise ValueError("code, source e destination_url são imutáveis.")
        return self


class LinkResponse(BaseModel):
    id: int
    code: str
    source: str
    label: str | None
    destination_url: str
    is_active: bool
    created_at: datetime
    public_path: str
    public_url: str | None = None

