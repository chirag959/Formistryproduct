"""End-to-end: send via AiSensy (mocked) → webhook status/reply → booked ROI."""
import json

from datetime import date, timedelta

from app.config import get_settings
from tests.conftest import login


def _csv(rows):
    return ("name,phone,last_visit_date\n" + "\n".join(rows)).encode()


def test_full_campaign_flow(client, seeded, monkeypatch):
    settings = get_settings()
    # Configure AiSensy (global key) + webhook token for this test.
    monkeypatch.setattr(settings, "aisensy_api_key", "TESTKEY")
    monkeypatch.setattr(settings, "aisensy_webhook_token", "WHTOKEN")

    sent = {}

    def fake_send(*, api_key, campaign_name, destination, user_name=None, template_params=None):
        assert api_key == "TESTKEY"
        assert campaign_name == "winback_v1"
        sent[destination] = template_params
        return None  # AiSensy often returns no message id

    monkeypatch.setattr("app.routers.campaigns.send_campaign_message", fake_send)

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
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert sent == {"+919876543210": ["20% off"]}

    roi = client.get(f"/workspaces/{ws}/campaigns/{cid}", headers=hdr).json()
    assert roi["sent"] == 1 and roi["failed"] == 0

    def post_webhook(body: dict, token="WHTOKEN"):
        return client.post(
            f"/webhooks/aisensy?token={token}",
            content=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )

    # --- Bad token rejected ---
    assert post_webhook({"waId": "919876543210", "status": "delivered"}, token="nope").status_code == 403

    # --- Delivered status (matched by phone, no wamid) ---
    assert post_webhook({"waId": "919876543210", "status": "delivered"}).status_code == 200
    roi = client.get(f"/workspaces/{ws}/campaigns/{cid}", headers=hdr).json()
    assert roi["delivered"] == 1

    # --- Inbound reply ---
    assert post_webhook({"waId": "919876543210", "text": "Yes, book me!"}).status_code == 200
    roi = client.get(f"/workspaces/{ws}/campaigns/{cid}", headers=hdr).json()
    assert roi["replied"] == 1

    # --- Mark booked → revenue = 1 x avg_ticket (800) ---
    mid = roi["messages"][0]["id"]
    client.post(f"/workspaces/{ws}/campaigns/{cid}/messages/{mid}/booked?booked=true", headers=hdr)
    roi = client.get(f"/workspaces/{ws}/campaigns/{cid}", headers=hdr).json()
    assert roi["booked"] == 1 and roi["estimated_revenue"] == 800.0
