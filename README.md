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
| WhatsApp | Meta WhatsApp Cloud API (direct) |
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
   average ticket in ₹; paste the WhatsApp `phone_number_id` from Meta).
3. **Upload contacts** — a CSV with columns `name, phone, last_visit_date`.
   Re-uploading the same phone updates the row (idempotent on
   `workspace_id + phone`); no duplicates.
4. **Review lapsed contacts** — anyone past the threshold (or never seen) is
   highlighted.
5. **New campaign** — pick an approved template name, set the discount/offer,
   preview, and "Send to X lapsed contacts". Sending runs in the background.
6. **Campaign Results** — the ROI panel: sent / delivered / read / replied /
   booked + estimated revenue. Tick **booked** on the replies that became real
   bookings to drive the revenue number (`booked × avg ticket`).

---

## WhatsApp Cloud API setup (required before sending)

Sending and replies only work once Meta is wired up:

1. Create a **Meta Business account** and register a WhatsApp phone number on
   the **Cloud API**. Note its `phone_number_id` → put it on the workspace.
2. Generate a **system-user access token** with `whatsapp_business_messaging`
   permission → `WHATSAPP_ACCESS_TOKEN`.
3. Submit **Marketing-category message templates** for approval. Recipients did
   NOT message first, so Meta must pre-approve the exact wording. Keep copy
   clean — spammy copy gets rejected. Use the approved template's name in the
   campaign form; a single `{{1}}` body variable receives the discount/offer.
4. **Pricing:** Meta bills per message and moved to per-message rates in 2025.
   Confirm current rates on Meta's official pricing page before quoting a
   client — nothing here hardcodes pricing.

### Webhook (replies + status updates)

Meta callbacks need a **public HTTPS URL** — localhost cannot receive them.

- **Dev:** expose the API with ngrok:
  ```bash
  ngrok http 8000
  ```
  Then in Meta → WhatsApp → Configuration, set the callback URL to
  `https://<your-ngrok-domain>/webhooks/whatsapp` and the **Verify Token** to
  the value of `WHATSAPP_VERIFY_TOKEN`. Meta calls `GET /webhooks/whatsapp` and
  the app echoes the challenge.
- **Prod:** point a real domain at the API and use
  `https://your-domain/webhooks/whatsapp`.
- Every `POST /webhooks/whatsapp` is validated against
  `X-Hub-Signature-256` using `WHATSAPP_APP_SECRET`; unsigned/invalid payloads
  are rejected with 403.

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
| `WHATSAPP_API_BASE` | Graph API base, e.g. `https://graph.facebook.com/v21.0` |
| `WHATSAPP_ACCESS_TOKEN` | Meta token used to send |
| `WHATSAPP_VERIFY_TOKEN` | Echoed on the GET verify handshake |
| `WHATSAPP_APP_SECRET` | Validates the webhook signature |
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
POST   /workspaces/{id}/campaigns               (create + send)
GET    /workspaces/{id}/campaigns
GET    /workspaces/{id}/campaigns/{cid}         (status + ROI)
POST   /workspaces/{id}/campaigns/{cid}/messages/{mid}/booked
GET    /webhooks/whatsapp                        (Meta verify handshake)
POST   /webhooks/whatsapp                        (Meta status + replies)
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
