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

    # --- WhatsApp via AiSensy (BSP on top of Meta Cloud API) ---
    # AiSensy Campaign API base. Sends go to {base}/campaign/t1/api/v2.
    aisensy_api_base: str = "https://backend.aisensy.com"
    # Global API key fallback. A workspace may override with its own key
    # (workspaces.aisensy_api_key) so each client's AiSensy project stays
    # isolated — the per-workspace key always wins over this env default.
    aisensy_api_key: str | None = None
    # "source" tag attached to every send (shows up on the AiSensy contact).
    aisensy_source: str = "rebooking-tool"
    # Shared secret required on the inbound webhook (/webhooks/aisensy?token=).
    # AiSensy does not sign callbacks the way Meta does, so we gate on this.
    aisensy_webhook_token: str | None = None

    # --- CORS ---
    cors_origins: str = "*"  # comma-separated list, or * for all


@lru_cache
def get_settings() -> Settings:
    return Settings()
