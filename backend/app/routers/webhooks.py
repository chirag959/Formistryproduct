"""AiSensy webhook: inbound replies + delivery/read/failed status updates.

POST /webhooks/aisensy?token=<secret>

AiSensy (unlike Meta direct) does not sign callbacks or run a GET verify
handshake, and its Campaign API does not return a WhatsApp message id — so:
  * the endpoint is gated on a shared secret token (query or header), and
  * events are matched to a contact by PHONE within the workspace, then applied
    to that contact's most recent outbound message.

AiSensy's exact payload is behind a login-gated doc, so the parser below reads
the phone / status / text defensively across the field names AiSensy is known
to use, and also accepts a raw Meta-style `entry[]` envelope if the project is
configured to forward it. Once you share a real sample payload this can be
tightened. Set AISENSY_WEBHOOK_TOKEN and point AiSensy at
  https://<host>/webhooks/aisensy?token=<AISENSY_WEBHOOK_TOKEN>
"""
import logging

from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Contact, Message, MessageStatus, Reply
from app.services.aisensy import webhook_token_ok

logger = logging.getLogger("webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_STATUS_MAP = {
    "sent": MessageStatus.sent,
    "delivered": MessageStatus.delivered,
    "read": MessageStatus.read,
    "failed": MessageStatus.failed,
    "undelivered": MessageStatus.failed,
}
# Never downgrade: a later 'delivered' must not overwrite 'read'/'replied'.
_STATUS_RANK = {
    MessageStatus.sent: 0,
    MessageStatus.delivered: 1,
    MessageStatus.read: 2,
    MessageStatus.replied: 3,
    MessageStatus.failed: 3,
}

# Candidate keys AiSensy may use for the customer's phone, status, and text.
_PHONE_KEYS = ("waId", "whatsappNumber", "mobile", "phone", "from", "destination", "number")
_STATUS_KEYS = ("status", "messageStatus", "deliveryStatus", "event")
_TEXT_KEYS = ("text", "message", "body", "messageText", "content")


@router.get("/aisensy")
def aisensy_health():
    """Simple reachability check (AiSensy has no verify handshake)."""
    return {"status": "ok"}


@router.post("/aisensy")
async def aisensy_receive(request: Request):
    token = request.query_params.get("token") or request.headers.get("X-Webhook-Token")
    if not webhook_token_ok(token):
        logger.warning("Rejected AiSensy webhook with bad/missing token")
        return Response(status_code=403, content="invalid token")
    if not request.query_params.get("token") and not request.headers.get("X-Webhook-Token"):
        logger.warning("AiSensy webhook accepted with no token (AISENSY_WEBHOOK_TOKEN unset)")

    try:
        payload = await request.json()
    except Exception:
        logger.warning("AiSensy webhook: non-JSON body")
        return {"status": "ignored"}

    db = SessionLocal()
    try:
        for event in _iter_events(payload):
            _handle_event(db, event)
        db.commit()
    except Exception:  # never 500 back to AiSensy — log and ack
        logger.exception("Error processing AiSensy webhook")
        db.rollback()
    finally:
        db.close()
    return {"status": "ok"}


def _iter_events(payload) -> list[dict]:
    """Flatten the various shapes AiSensy might POST into a list of dicts.

    Handles: a bare event object, a list of events, {"data": [...]}, and a
    raw Meta-style {"entry":[{"changes":[{"value":{...}}]}]} envelope.
    """
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    if not isinstance(payload, dict):
        return []

    # Meta-style envelope (some AiSensy projects forward it verbatim).
    if "entry" in payload:
        out: list[dict] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for st in value.get("statuses", []):
                    phone = st.get("recipient_id")
                    out.append({"_phone": phone, "_status": st.get("status"),
                                "_errors": st.get("errors")})
                for m in value.get("messages", []):
                    out.append({"_phone": m.get("from"), "_text": _meta_text(m)})
        return out

    if isinstance(payload.get("data"), list):
        return [e for e in payload["data"] if isinstance(e, dict)]
    return [payload]


def _handle_event(db: Session, event: dict) -> None:
    phone = _first(event, _PHONE_KEYS) or event.get("_phone")
    contact = _match_contact(db, phone)
    if not contact:
        logger.info("AiSensy event for unknown number %s", phone)
        return

    status_raw = (event.get("_status") or _first(event, _STATUS_KEYS) or "").lower()
    text = event.get("_text") or _first(event, _TEXT_KEYS)
    new_status = _STATUS_MAP.get(status_raw)

    latest = (
        db.query(Message)
        .filter(Message.contact_id == contact.id)
        .order_by(Message.sent_at.desc())
        .first()
    )

    if new_status:  # delivery/read/failed status update
        if latest and _STATUS_RANK[new_status] >= _STATUS_RANK[latest.status]:
            latest.status = new_status
            if new_status == MessageStatus.failed:
                latest.error_detail = str(event.get("_errors") or text or "failed")
        return

    # Otherwise treat it as an inbound reply.
    db.add(
        Reply(
            message_id=latest.id if latest else None,
            contact_id=contact.id,
            workspace_id=contact.workspace_id,
            body=text if isinstance(text, str) else None,
        )
    )
    if latest:
        latest.status = MessageStatus.replied  # highest rank — always wins


def _match_contact(db: Session, phone: str | None) -> Contact | None:
    if not phone:
        return None
    phone = str(phone)
    candidate = phone if phone.startswith("+") else "+" + phone.lstrip("+")
    contact = db.query(Contact).filter(Contact.phone == candidate).first()
    if contact:
        return contact
    digits = "".join(ch for ch in phone if ch.isdigit())[-10:]
    if len(digits) == 10:
        return db.query(Contact).filter(Contact.phone.like(f"%{digits}")).first()
    return None


def _first(event: dict, keys) -> str | None:
    for k in keys:
        v = event.get(k)
        if v not in (None, ""):
            return v if isinstance(v, str) else str(v)
    return None


def _meta_text(m: dict) -> str | None:
    if m.get("type") == "text":
        return m.get("text", {}).get("body")
    if m.get("type") == "button":
        return m.get("button", {}).get("text")
    return m.get("type")
