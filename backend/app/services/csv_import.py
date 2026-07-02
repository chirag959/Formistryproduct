"""CSV contact import. Idempotent on (workspace_id, phone) — PRD §10."""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import Contact
from app.schemas import UploadSummary

# Accept common header spellings so agencies don't have to reformat their export.
_NAME_KEYS = {"name", "contact", "customer", "full name"}
_PHONE_KEYS = {"phone", "mobile", "number", "phone number", "whatsapp"}
_DATE_KEYS = {"last_visit_date", "last visit", "last_visit", "lastvisit", "last visit date"}

_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d")


def _pick(row: dict[str, str], keys: set[str]) -> str | None:
    for k, v in row.items():
        if k and k.strip().lower() in keys:
            return (v or "").strip()
    return None


def normalize_phone(raw: str) -> str | None:
    """Best-effort E.164 normalization. Returns None if not salvageable.

    Indian defaults are applied for bare 10-digit numbers since the first
    client is a Mumbai salon, but any number already carrying a country code
    (leading +) is respected as-is.
    """
    if not raw:
        return None
    raw = raw.strip()
    has_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if has_plus:
        return "+" + digits
    if len(digits) == 10:  # bare local number → assume India (+91)
        return "+91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    if len(digits) == 11 and digits.startswith("0"):
        return "+91" + digits[1:]
    return "+" + digits


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def import_contacts(db: Session, workspace_id: int, content: bytes) -> UploadSummary:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    created = updated = skipped = 0
    errors: list[str] = []

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        phone_raw = _pick(row, _PHONE_KEYS)
        phone = normalize_phone(phone_raw or "")
        if not phone:
            skipped += 1
            errors.append(f"Row {i}: missing/invalid phone ({phone_raw!r})")
            continue
        name = _pick(row, _NAME_KEYS)
        last_visit = parse_date(_pick(row, _DATE_KEYS))

        existing = (
            db.query(Contact)
            .filter(Contact.workspace_id == workspace_id, Contact.phone == phone)
            .one_or_none()
        )
        if existing:  # update, never duplicate
            if name:
                existing.name = name
            if last_visit:
                existing.last_visit_date = last_visit
            updated += 1
        else:
            db.add(
                Contact(
                    workspace_id=workspace_id,
                    name=name,
                    phone=phone,
                    last_visit_date=last_visit,
                )
            )
            created += 1

    db.commit()
    return UploadSummary(created=created, updated=updated, skipped=skipped, errors=errors[:50])
