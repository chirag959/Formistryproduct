"""AiSensy WhatsApp client + webhook helpers.

AiSensy is a BSP layered on Meta's WhatsApp Cloud API. Sends go through its
Campaign API, which references a pre-created "Live" API campaign (bound to an
approved template) by name and fills the template's variables via
templateParams. Credentials come from env or the per-workspace key (PRD §10);
every call logs success/failure so failed sends are visible, not silent.

Docs (Cloudflare-gated): https://wiki.aisensy.com/en/articles/11501889-api-reference-docs
"""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.models import Workspace

logger = logging.getLogger("aisensy")
settings = get_settings()


class AiSensyError(Exception):
    """Raised when a send fails; carries a human-readable detail for logging."""


def resolve_api_key(workspace: Workspace) -> str | None:
    """Per-workspace key wins over the global env fallback."""
    return workspace.aisensy_api_key or settings.aisensy_api_key


def is_configured(workspace: Workspace) -> bool:
    return bool(resolve_api_key(workspace))


def send_campaign_message(
    *,
    api_key: str,
    campaign_name: str,
    destination: str,
    user_name: str | None = None,
    template_params: list[str] | None = None,
) -> str | None:
    """Send one templated message via the AiSensy Campaign API.

    Returns AiSensy's message/submission id if the response carries one, else
    None (the v2 campaign API does not always echo a WhatsApp message id — we
    fall back to phone-based matching in the webhook). Raises AiSensyError on
    any failure.
    """
    if not api_key:
        raise AiSensyError("no AiSensy API key configured for this workspace")
    if not campaign_name:
        raise AiSensyError("campaign has no AiSensy campaign name")

    url = f"{settings.aisensy_api_base}/campaign/t1/api/v2"
    payload = {
        "apiKey": api_key,
        "campaignName": campaign_name,
        "destination": destination.lstrip("+"),
        "userName": user_name or "",
        "source": settings.aisensy_source,
        "templateParams": template_params or [],
    }

    try:
        resp = httpx.post(url, json=payload, timeout=30.0)
    except httpx.HTTPError as exc:
        logger.error("AiSensy send network error to %s: %s", destination, exc)
        raise AiSensyError(f"network error: {exc}") from exc

    if resp.status_code >= 400:
        logger.error("AiSensy send failed to %s [%s]: %s", destination, resp.status_code, resp.text)
        raise AiSensyError(f"HTTP {resp.status_code}: {resp.text}")

    # AiSensy replies with e.g. {"success": true, ...}. Treat an explicit
    # success:false as a failure even on a 200.
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if data.get("success") is False:
        detail = data.get("message") or resp.text
        logger.error("AiSensy send rejected for %s: %s", destination, detail)
        raise AiSensyError(str(detail))

    msg_id = data.get("messageId") or data.get("id")
    logger.info("AiSensy sent to %s id=%s", destination, msg_id)
    return msg_id


def webhook_token_ok(provided: str | None) -> bool:
    """Gate the inbound webhook on a shared secret.

    If AISENSY_WEBHOOK_TOKEN is configured we require an exact match. If it is
    not set (dev), we accept but the caller logs a warning.
    """
    if not settings.aisensy_webhook_token:
        return True
    return provided == settings.aisensy_webhook_token
