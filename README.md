# Formistry — WhatsApp Lapsed-Customer Rebooking Tool

Multi-tenant web app that re-engages a business's dormant customers over
WhatsApp and tracks the bookings that result. Built to the spec in
[`PRD.md`](./PRD.md); architecture notes live in [`CLAUDE.md`](./CLAUDE.md).

> **Core loop:** Upload contacts → auto-detect who's lapsed → send an approved
> WhatsApp template → catch replies → show sent / delivered / replied / booked
> + estimated revenue.

Every business is a **workspace**; "lapsed" is a configurable rule. Nothing is
hardcoded to the salon vertical.

> NOTE: The repo root also contains an unrelated `index.html` (a Formistry
> fashion product page) that predates this tool and is left untouched.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11 · FastAPI · SQLAlchemy 2 |
| Frontend | React 18 · Vite · TypeScript |
| Database | PostgreSQL 16 |
| WhatsApp | **AiSensy** Campaign API (BSP on Meta Cloud API) |
| Deploy | Docker Compose (`db` + `api` + `frontend`) |

---

## Quick start (Docker Compose)

```bash
cp .env.example .env
# edit .env: set JWT_SECRET, SEED_ADMIN_EMAIL/PASSWORD, and (for sending)
# the WHATSAPP_* values.

docker compose up --build
```

- Frontend: <http://localhost:8080>
- API + Swagger docs: <http://localhost:8000/docs>

On first boot the API creates the schema and — if `SEED_ADMIN_EMAIL` /
`SEED_ADMIN_PASSWORD` are set and no users exist — an **agency admin** account.
Log in with those credentials, create a workspace, then work inside it.

---

## Local development (without Docker)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://formistry:formistry@localhost:5432/formistry
export JWT_SECRET=dev-secret
export SEED_ADMIN_EMAIL=admin@example.com SEED_ADMIN_PASSWORD=admin123
uvicorn app.main:app --reload            # http://localhost:8000
pytest                                    # run the test suite
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                               # http://localhost:5173 (proxies /api → :8000)
```

---

## Using the tool

1. **Sign in** as the agency admin.
2. **Create a workspace** for the client (set lapsed threshold in days and the
   average ticket in ₹; paste the client's **AiSensy API key** — or leave blank
   to use the global `AISENSY_API_KEY`).
3. **Upload contacts** — a CSV with columns `name, phone, last_visit_date`.
   Re-uploading the same phone updates the row (idempotent on
   `workspace_id + phone`); no duplicates.
4. **Review lapsed contacts** — anyone past the threshold (or never seen) is
   highlighted.
5. **New campaign** — enter the **AiSensy campaign name** (a Live API campaign
   bound to an approved template), set the discount/offer, preview, and "Send to
   X lapsed contacts". Sending runs in the background.
6. **Campaign Results** — the ROI panel: sent / delivered / read / replied /
   booked + estimated revenue. Tick **booked** on the replies that became real
   bookings to drive the revenue number (`booked × avg ticket`).

---

## AiSensy setup (required before sending)

We send through **AiSensy**, a BSP layered on Meta's WhatsApp Cloud API, rather
than calling Meta directly. AiSensy handles the phone number, template approval,
and (optionally) the reply webhook. (This is a deliberate departure from the
PRD's "Meta direct, no BSP" line — see `CLAUDE.md`.)

1. In AiSensy, connect the client's **WhatsApp number** (this runs on Meta's
   Cloud API under the hood) and get an **API key**
   (dashboard → *Manage → API Key*). Put it on the workspace, or set
   `AISENSY_API_KEY` as a global fallback.
2. Get your **Meta-approved Marketing template** approved inside AiSensy.
   Recipients did NOT message first, so the exact wording must be pre-approved;
   keep copy clean. A single `{{1}}` body variable receives the discount/offer.
3. Create an **API Campaign** in AiSensy bound to that template and set its
   status to **Live**. The campaign's name is what you type into the "New
   campaign" form here — it must match exactly.
4. **Pricing:** WhatsApp bills per message (per-message rates since 2025) and
   AiSensy adds its own plan/markup. Confirm current rates before quoting a
   client — nothing here hardcodes pricing.

### Webhook (replies + status updates)

The send path is outbound and needs no public URL, but to capture **replies and
delivery/read status** AiSensy must POST to a **public HTTPS URL**.

1. Set `AISENSY_WEBHOOK_TOKEN` to a random secret.
2. In AiSensy, configure the project/live-chat webhook to:
   `https://<your-host>/webhooks/aisensy?token=<AISENSY_WEBHOOK_TOKEN>`
   - **Dev:** expose the API with `ngrok http 8000` and use the ngrok domain.
   - **Prod:** use your real domain.
3. Requests without the matching token are rejected with 403. Events are matched
   to a contact by **phone within the workspace** (AiSensy's send response
   carries no WhatsApp message id), then applied to that contact's most recent
   message.

> The AiSensy webhook payload schema sits behind a login-gated doc, so the
> handler in `backend/app/routers/webhooks.py` parses the phone/status/text
> defensively across the field names AiSensy is known to use (and also accepts a
> raw Meta-style `entry[]` envelope). Paste a real sample payload and it can be
> tightened.

### Sending guardrail

Do not message the same contact more than **once per month** — over-messaging
tanks the number's quality rating and throttles every workspace on it.

---

## Environment variables

All secrets come from the environment (see `.env.example`); nothing is
hardcoded or committed.

| Var | Purpose |
|---|---|
| `DATABASE_URL` | Postgres DSN (compose builds it from `POSTGRES_*`) |
| `JWT_SECRET` | Signs auth tokens — use a long random string |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | Bootstrap agency admin on first run |
| `AISENSY_API_BASE` | AiSensy API base, `https://backend.aisensy.com` |
| `AISENSY_API_KEY` | Global fallback key; per-workspace key overrides it |
| `AISENSY_SOURCE` | Source tag attached to each AiSensy contact |
| `AISENSY_WEBHOOK_TOKEN` | Shared secret required on the inbound webhook |
| `CORS_ORIGINS` | Comma-separated allowed origins, or `*` |

---

## Database backups

Daily Postgres dump (run from the host; adjust the service/db name if changed):

```bash
# One-off dump
docker compose exec -T db pg_dump -U formistry formistry > "backups/formistry-$(date +%F).sql"

# Restore
cat backups/formistry-YYYY-MM-DD.sql | docker compose exec -T db psql -U formistry formistry
```

Schedule the dump daily via cron on the host, e.g.:

```cron
0 2 * * * cd /path/to/Formistryproduct && docker compose exec -T db pg_dump -U formistry formistry > backups/formistry-$(date +\%F).sql
```

---

## API endpoints (v1)

```
POST   /auth/login
GET    /workspaces
POST   /workspaces                              (agency admin only)
GET    /workspaces/{id}
POST   /workspaces/{id}/contacts/upload         (CSV)
GET    /workspaces/{id}/contacts
GET    /workspaces/{id}/contacts/lapsed
POST   /workspaces/{id}/campaigns               (create + send via AiSensy)
GET    /workspaces/{id}/campaigns
GET    /workspaces/{id}/campaigns/{cid}         (status + ROI)
POST   /workspaces/{id}/campaigns/{cid}/messages/{mid}/booked
POST   /webhooks/aisensy?token=…                (AiSensy status + replies)
```

Every `/workspaces/{id}/…` route enforces tenant scoping: a workspace user can
only reach their own workspace; the agency admin can reach all.

---

## Project layout

```
backend/    FastAPI app, models, routers, services, tests
frontend/   React + Vite dashboard
docker-compose.yml   db + api + frontend
.env.example         copy to .env
PRD.md · CLAUDE.md   product + architecture docs
```

---

## Out of scope for v1

Auto-booking negotiation bot, POS/CRM integration, end-client billing,
multi-channel (SMS/email). WhatsApp only.
