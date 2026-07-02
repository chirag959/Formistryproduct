"""Lapsed-contact detection. Threshold is per-workspace (PRD §4)."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Contact, Workspace


def lapsed_cutoff(workspace: Workspace, today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=workspace.lapsed_threshold_days)


def get_lapsed_contacts(db: Session, workspace: Workspace, today: date | None = None) -> list[Contact]:
    """Contacts whose last visit is older than the workspace threshold.

    A contact with no recorded last_visit_date counts as lapsed — we have never
    seen them return, which is exactly who this tool exists to re-engage.
    """
    cutoff = lapsed_cutoff(workspace, today)
    return (
        db.query(Contact)
        .filter(
            Contact.workspace_id == workspace.id,
            (Contact.last_visit_date.is_(None)) | (Contact.last_visit_date <= cutoff),
        )
        .order_by(Contact.last_visit_date.asc().nullsfirst())
        .all()
    )


def days_since_visit(contact: Contact, today: date | None = None) -> int | None:
    if contact.last_visit_date is None:
        return None
    today = today or date.today()
    return (today - contact.last_visit_date).days
