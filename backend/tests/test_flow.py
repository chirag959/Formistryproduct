"""End-to-end: send campaign (mocked Meta) → webhook status/reply → booked ROI."""
import hashlib
import hmac
import json
from datetime import date, timedelta

from app.config import get_settings
from tests.conftest import login


def _csv(rows):
    return ("name,phone,last_visit_date\n" + "\n".join(rows)).encode()


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_full_campaign_flow(client, seeded, monkeypatch):
    settings = get_settings()
    # Configure WhatsApp for the duration of this test.
    monkeypatch.setattr(settings, "whatsapp_access_token", "TESTTOKEN")
    monkeypatch.setattr(settings, "whatsapp_app_secret", "APPSECRET")

    sent = {}

    def fake_send(*, phone_number_id, to_phone, template_name, language_code="en", body_params=None):
        wamid = f"wamid.{to_phone}"
        sent[to_phone] = wamid
        return wamid

    # Patch where it's used (campaigns router imported the symbols).
    monkeypatch.setattr("app.routers.campaigns.is_configured", lambda: True)
    monkeypatch.setattr("app.routers.campaigns.send_template", fake_send)

    hdr = login(client, seeded["admin_a"])
    ws = seeded["ws_a"]
    old = (date.today() - timedelta(days=100)).isoformat()
    client.post(
        f"/workspaces/{ws}/contacts/upload",
        files={"file": ("c.csv", _csv([f"Asha,9876543210,{old}"]), "text/csv")},
        headers=hdr,
    )

    # Fire the campaign (BackgroundTasks run synchronously in TestClient).
    r = client.post(
        f"/workspaces/{ws}/campaigns",
        json={"template_name": "winback_v1", "discount_offer": "20% off"},
        headers=hdr,
    )
    assert r.status_code == 201
    cid = r.json()["id"]
    assert sent  # the mocked send was called

    roi = client.get(f"/workspaces/{ws}/campaigns/{cid}", headers=hdr).json()
    assert roi["sent"] == 1
    assert roi["failed"] == 0
    wamid = roi["messages"][0]["whatsapp_message_id"]

    # --- Webhook: delivered status ---
    delivered = json.dumps(
        {"entry": [{"changes": [{"value": {"statuses": [{"id": wamid, "status": "delivered"}]}}]}]}
    ).encode()
    r = client.post(
        "/webhooks/whatsapp", content=delivered,
        headers={"X-Hub-Signature-256": _sign(delivered, "APPSECRET"), "Content-Type": "application/json"},
    )
    assert r.status_code == 200
    roi = client.get(f"/workspaces/{ws}/campaigns/{cid}", headers=hdr).json()
    assert roi["delivered"] == 1

    # --- Webhook: inbound reply ---
    reply = json.dumps(
        {"entry": [{"changes": [{"value": {
            "messages": [{"from": "919876543210", "type": "text", "text": {"body": "Yes book me!"}}],
        }}]}]}
    ).encode()
    r = client.post(
        "/webhooks/whatsapp", content=reply,
        headers={"X-Hub-Signature-256": _sign(reply, "APPSECRET"), "Content-Type": "application/json"},
    )
    assert r.status_code == 200
    roi = client.get(f"/workspaces/{ws}/campaigns/{cid}", headers=hdr).json()
    assert roi["replied"] == 1

    # --- Bad signature rejected ---
    r = client.post(
        "/webhooks/whatsapp", content=reply,
        headers={"X-Hub-Signature-256": "sha256=deadbeef", "Content-Type": "application/json"},
    )
    assert r.status_code == 403

    # --- Mark booked → revenue = 1 x avg_ticket (800) ---
    mid = roi["messages"][0]["id"]
    client.post(f"/workspaces/{ws}/campaigns/{cid}/messages/{mid}/booked?booked=true", headers=hdr)
    roi = client.get(f"/workspaces/{ws}/campaigns/{cid}", headers=hdr).json()
    assert roi["booked"] == 1
    assert roi["estimated_revenue"] == 800.0
