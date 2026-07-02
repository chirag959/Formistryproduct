"""Bootstrap an agency admin on first startup if the users table is empty.

Credentials come from SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD env vars only.
No default password is ever created (PRD §10).
"""
import logging

from app.config import get_settings
from app.db import SessionLocal
from app.models import Role, User
from app.security import hash_password

logger = logging.getLogger("seed")
settings = get_settings()


def seed_admin() -> None:
    if not settings.seed_admin_email or not settings.seed_admin_password:
        return
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        admin = User(
            email=settings.seed_admin_email.lower(),
            password_hash=hash_password(settings.seed_admin_password),
            role=Role.admin,
            workspace_id=None,  # agency admin — cross-workspace
        )
        db.add(admin)
        db.commit()
        logger.info("Seeded agency admin %s", admin.email)
    finally:
        db.close()
