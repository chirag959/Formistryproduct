"""Meta WhatsApp webhook: verify handshake, status updates, inbound replies.

GET  /webhooks/whatsapp  → Meta verification handshake (echo hub.challenge).
POST /webhooks/whatsapp  → delivery/read/failed status + inbound messages.

The POST body is signature-verified against the app secret (PRD §6).
"""
import logging

from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Contact, Message, MessageStatus, Reply
from app.services.whatsapp import verify_signature

logger = logging.getLogger("webhooks")
settings = get_settings()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Map Meta status strings to our enum. 'sent' stays sent; we never downgrade.
_STATUS_MAP = {
    "delivered": MessageStatus.delivered,
    "read": MessageStatus.read,
    "failed": MessageStatus.failed,
    "sent": MessageStatus.sent,
}
# Ordering so a later 'read' isn't overwritten by a stray earlier 'delivered'.
_STATUS_RANK = {
    MessageStatus.sent: 0,
    MessageStatus.delivered: 1,
    MessageStatus.read: 2,
    MessageStatus.replied: 3,
    MessageStatus.failed: 3,
}


@router.get("/whatsapp")
def verify(request: Request):
    """Meta calls this with hub.mode/verify_token/challenge to confirm the URL."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge", "")
    if mode == "subscribe" and settings.whatsapp_verify_token and token == settings.whatsapp_verify_token:
        return Response(content=challenge, media_type="text/plain")
    logger.warning("Webhook verify failed (mode=%s)", mode)
    return Response(status_code=403, content="verification failed")


@router.post("/whatsapp")
async def receive(request: Request):
    raw = await request.body()
    if not verify_signature(raw, request.headers.get("X-Hub-Signature-256")):
        logger.warning("Rejected webhook with invalid/missing signature")
        return Response(status_code=403, content="invalid signature")

    payload = await request.json()
    db = SessionLocal()
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                _handle_statuses(db, value.get("statuses", []))
                _handle_messages(db, value.get("messages", []), value.get("contacts", []))
        db.commit()
    except Exception:  # never 500 back to Meta — log and ack
        logger.exception("Error processing webhook payload")
        db.rollback()
    finally:
        db.close()
    # Always 200 so Meta doesn't retry-storm a payload we've already logged.
    return {"status": "ok"}


def _handle_statuses(db: Session, statuses: list[dict]) -> None:
    for st in statuses:
        wamid = st.get("id")
        new_status = _STATUS_MAP.get(st.get("status", ""))
        if not wamid or not new_status:
            continue
        msg = db.query(Message).filter(Message.whatsapp_message_id == wamid).one_or_none()
        if not msg:
            logger.info("Status for unknown wamid=%s (status=%s)", wamid, st.get("status"))
            continue
        if _STATUS_RANK[new_status] >= _STATUS_RANK[msg.status]:
            msg.status = new_status
            if new_status == MessageStatus.failed:
                errs = st.get("errors") or []
                msg.error_detail = str(errs[0]) if errs else "failed (see Meta)"


def _handle_messages(db: Session, messages: list[dict], contacts_meta: list[dict]) -> None:
    """An inbound message = a reply. Match to contact by phone, mark replied."""
    for m in messages:
        from_phone = m.get("from")
        body = _extract_text(m)
        contact = _match_contact(db, from_phone)
        if not contact:
            logger.info("Reply from unknown number %s", from_phone)
            continue

        # Attach to that contact's most recent outbound message, if any.
        msg = (
            db.query(Message)
            .filter(Message.contact_id == contact.id)
            .order_by(Message.sent_at.desc())
            .first()
        )
        db.add(
            Reply(
                message_id=msg.id if msg else None,
                contact_id=contact.id,
                workspace_id=contact.workspace_id,
                body=body,
            )
        )
        if msg:
            msg.status = MessageStatus.replied  # highest rank — always wins


def _match_contact(db: Session, from_phone: str | None) -> Contact | None:
    if not from_phone:
        return None
    candidate = from_phone if from_phone.startswith("+") else "+" + from_phone
    contact = db.query(Contact).filter(Contact.phone == candidate).first()
    if contact:
        return contact
    # Fall back to a suffix match (last 10 digits) for formatting drift.
    digits = "".join(ch for ch in from_phone if ch.isdigit())[-10:]
    if len(digits) == 10:
        return db.query(Contact).filter(Contact.phone.like(f"%{digits}")).first()
    return None


def _extract_text(m: dict) -> str | None:
    if m.get("type") == "text":
        return m.get("text", {}).get("body")
    if m.get("type") == "button":
        return m.get("button", {}).get("text")
    return m.get("type")  # e.g. 'image', 'audio' — record the kind at least
