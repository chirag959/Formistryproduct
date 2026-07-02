"""End-to-end API tests: auth, tenant isolation, upload idempotency, lapsed, ROI."""
from datetime import date, timedelta

from tests.conftest import login


def test_login_rejects_bad_password(client, seeded):
    r = client.post("/auth/login", json={"email": "a@x.com", "password": "wrong"})
    assert r.status_code == 401


def test_workspace_creation_requires_agency_admin(client, seeded):
    # workspace admin cannot create workspaces
    hdr = login(client, seeded["admin_a"])
    r = client.post("/workspaces", json={"name": "Nope"}, headers=hdr)
    assert r.status_code == 403
    # agency admin can
    hdr = login(client, seeded["agency"])
    r = client.post("/workspaces", json={"name": "Salon C", "avg_ticket": 1000}, headers=hdr)
    assert r.status_code == 201


def test_tenant_isolation(client, seeded):
    """Workspace A's admin must not reach Workspace B's data."""
    hdr_a = login(client, seeded["admin_a"])
    r = client.get(f"/workspaces/{seeded['ws_b']}/contacts", headers=hdr_a)
    assert r.status_code == 404  # existence not leaked

    # agency admin can reach both
    hdr_ag = login(client, seeded["agency"])
    assert client.get(f"/workspaces/{seeded['ws_a']}/contacts", headers=hdr_ag).status_code == 200
    assert client.get(f"/workspaces/{seeded['ws_b']}/contacts", headers=hdr_ag).status_code == 200


def _csv(rows):
    header = "name,phone,last_visit_date\n"
    return (header + "\n".join(rows)).encode()


def test_upload_is_idempotent(client, seeded):
    hdr = login(client, seeded["admin_a"])
    ws = seeded["ws_a"]
    files = {"file": ("c.csv", _csv(["Asha,9876543210,2024-01-01"]), "text/csv")}
    r1 = client.post(f"/workspaces/{ws}/contacts/upload", files=files, headers=hdr)
    assert r1.status_code == 200 and r1.json()["created"] == 1

    # re-upload same phone → update, not duplicate
    files = {"file": ("c.csv", _csv(["Asha Rao,9876543210,2024-02-01"]), "text/csv")}
    r2 = client.post(f"/workspaces/{ws}/contacts/upload", files=files, headers=hdr)
    assert r2.json()["updated"] == 1 and r2.json()["created"] == 0

    contacts = client.get(f"/workspaces/{ws}/contacts", headers=hdr).json()
    assert len(contacts) == 1
    assert contacts[0]["phone"] == "+919876543210"  # normalized to E.164
    assert contacts[0]["name"] == "Asha Rao"


def test_lapsed_detection_respects_threshold(client, seeded):
    hdr = login(client, seeded["admin_a"])
    ws = seeded["ws_a"]  # threshold 45 days
    recent = (date.today() - timedelta(days=10)).isoformat()
    old = (date.today() - timedelta(days=100)).isoformat()
    rows = [
        f"Recent,9000000001,{recent}",
        f"Lapsed,9000000002,{old}",
        "NeverSeen,9000000003,",  # no last visit → lapsed
    ]
    files = {"file": ("c.csv", _csv(rows), "text/csv")}
    client.post(f"/workspaces/{ws}/contacts/upload", files=files, headers=hdr)

    lapsed = client.get(f"/workspaces/{ws}/contacts/lapsed", headers=hdr).json()
    phones = {c["phone"] for c in lapsed}
    assert "+919000000002" in phones
    assert "+919000000003" in phones
    assert "+919000000001" not in phones


def test_campaign_requires_whatsapp_config(client, seeded, monkeypatch):
    hdr = login(client, seeded["admin_a"])
    ws = seeded["ws_a"]
    # No WHATSAPP_ACCESS_TOKEN configured in tests → 503
    r = client.post(f"/workspaces/{ws}/campaigns", json={"template_name": "t"}, headers=hdr)
    assert r.status_code == 503
