"""Meta WhatsApp Cloud API client + webhook signature verification.

Credentials come from env only (PRD §10). Every call logs success/failure so
failed sends are visible, not silent (PRD §10).
"""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("whatsapp")
settings = get_settings()


class WhatsAppError(Exception):
    """Raised when a send fails; carries a human-readable detail for logging."""


def is_configured() -> bool:
    return bool(settings.whatsapp_access_token)


def send_template(
    *,
    phone_number_id: str,
    to_phone: str,
    template_name: str,
    language_code: str = "en",
    body_params: list[str] | None = None,
) -> str:
    """Send an approved template message. Returns the WhatsApp message id.

    Raises WhatsAppError on any failure (network, HTTP error, unexpected shape).
    """
    if not is_configured():
        raise WhatsAppError("WHATSAPP_ACCESS_TOKEN not configured")
    if not phone_number_id:
        raise WhatsAppError("workspace has no whatsapp_phone_number_id")

    url = f"{settings.whatsapp_api_base}/{phone_number_id}/messages"
    components = []
    if body_params:
        components.append(
            {
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in body_params],
            }
        )
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone.lstrip("+"),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            **({"components": components} if components else {}),
        },
    }
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    except httpx.HTTPError as exc:
        logger.error("WhatsApp send network error to %s: %s", to_phone, exc)
        raise WhatsAppError(f"network error: {exc}") from exc

    if resp.status_code >= 400:
        detail = resp.text
        logger.error("WhatsApp send failed to %s [%s]: %s", to_phone, resp.status_code, detail)
        raise WhatsAppError(f"HTTP {resp.status_code}: {detail}")

    try:
        wamid = resp.json()["messages"][0]["id"]
    except (KeyError, IndexError, ValueError) as exc:
        logger.error("WhatsApp send unexpected response to %s: %s", to_phone, resp.text)
        raise WhatsAppError(f"unexpected response: {resp.text}") from exc

    logger.info("WhatsApp sent to %s wamid=%s", to_phone, wamid)
    return wamid


def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """Validate Meta's X-Hub-Signature-256 header against the app secret.

    If no app secret is configured we fail closed (return False) rather than
    silently trusting unsigned callbacks.
    """
    if not settings.whatsapp_app_secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.whatsapp_app_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)
