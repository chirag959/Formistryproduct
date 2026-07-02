"""Application settings, sourced entirely from environment variables.

Nothing here may carry a real secret default — see PRD §10. The only defaults
allowed are non-sensitive local-dev conveniences (host, port, algorithm).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    database_url: str = "postgresql+psycopg2://formistry:formistry@localhost:5432/formistry"

    # --- Auth ---
    jwt_secret: str = "change-me-in-env"  # MUST be overridden via env in prod
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 1 day

    # Bootstrap agency admin created on first startup if no users exist.
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None

    # --- WhatsApp Cloud API (Meta) ---
    # Graph API version + token. Per-workspace phone_number_id lives in the DB.
    whatsapp_api_base: str = "https://graph.facebook.com/v21.0"
    whatsapp_access_token: str | None = None
    # Token echoed back to Meta during the GET verify handshake.
    whatsapp_verify_token: str | None = None
    # App secret used to validate the X-Hub-Signature-256 header on callbacks.
    whatsapp_app_secret: str | None = None

    # --- CORS ---
    cors_origins: str = "*"  # comma-separated list, or * for all


@lru_cache
def get_settings() -> Settings:
    return Settings()
