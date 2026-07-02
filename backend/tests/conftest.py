"""Test fixtures: in-memory SQLite + FastAPI TestClient with seeded users.

Background tasks (campaign dispatch) and the webhook handler open their own
sessions via SessionLocal instead of the request-scoped get_db, so we patch
SessionLocal in those modules onto the same in-memory engine.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (register tables)
from app.db import Base, get_db
from app.main import app
from app.models import Role, User, Workspace
from app.security import hash_password


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture()
def TestingSession(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db_session(TestingSession):
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, TestingSession, monkeypatch):
    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    # Point out-of-request session factories at the same in-memory DB.
    monkeypatch.setattr("app.routers.campaigns.SessionLocal", TestingSession)
    monkeypatch.setattr("app.routers.webhooks.SessionLocal", TestingSession)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded(db_session):
    """Agency admin + two workspaces, each with its own admin user."""
    ws_a = Workspace(name="Salon A", whatsapp_phone_number_id="PN_A", lapsed_threshold_days=45, avg_ticket=800)
    ws_b = Workspace(name="Salon B", whatsapp_phone_number_id="PN_B", lapsed_threshold_days=30, avg_ticket=500)
    db_session.add_all([ws_a, ws_b])
    db_session.flush()

    agency = User(email="agency@x.com", password_hash=hash_password("pw"), role=Role.admin, workspace_id=None)
    admin_a = User(email="a@x.com", password_hash=hash_password("pw"), role=Role.admin, workspace_id=ws_a.id)
    admin_b = User(email="b@x.com", password_hash=hash_password("pw"), role=Role.admin, workspace_id=ws_b.id)
    db_session.add_all([agency, admin_a, admin_b])
    db_session.commit()
    return {
        "ws_a": ws_a.id, "ws_b": ws_b.id,
        "agency": "agency@x.com", "admin_a": "a@x.com", "admin_b": "b@x.com",
    }


def login(client, email, password="pw"):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
