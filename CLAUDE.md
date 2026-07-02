# CLAUDE.md — WhatsApp Lapsed-Customer Rebooking Tool

This file orients Claude Code (and humans) working in this repo. It is derived
from `PRD.md` (v1.0). If the PRD and this file disagree, the PRD wins — update
this file to match.

---

## 1. What this is

A **multi-tenant** web app that re-engages a business's dormant ("lapsed")
customers over WhatsApp and tracks the bookings that result.

Core loop:

> Upload contacts → auto-detect who's lapsed → send an approved WhatsApp
> template → catch replies → show sent / delivered / replied / booked + ROI.

First client: a Mumbai salon. **Never hardcode salon logic.** Every business is
a *workspace*; "lapsed" is a configurable rule. The same engine must re-target
banquet leads or GCC import/export buyers without a rewrite.

---

## 2. Non-negotiables (read before writing any code)

1. **Multi-tenancy from line one.** Every business-data table carries a
   `workspace_id` FK. Every data endpoint scopes to the authenticated user's
   workspace. A user in Workspace A must never see Workspace B's data.
2. **Secrets only in env vars.** No API keys, tokens, DB creds, or verify
   tokens hardcoded or committed. `.env` is gitignored; ship `.env.example`.
3. **Idempotent uploads.** Re-uploading a contact updates, never duplicates —
   match on `(workspace_id, phone)`.
4. **Configurable, not magic.** Lapsed threshold (default 45 days) and avg
   ticket are per-workspace settings, not constants.
5. **Loud failures.** Every WhatsApp API call logs success/failure; failed
   sends are visible in the data, not swallowed.
6. **Rate/quality guardrail.** Do not message the same contact more than once
   per month; over-messaging tanks the number's WhatsApp quality rating.

---

## 3. Tech stack (locked — do not substitute)

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI (async) |
| Frontend | React (Vite) |
| DB | PostgreSQL |
| WhatsApp | **AiSensy** Campaign API (BSP on Meta Cloud API) — see decision below |
| Background jobs | FastAPI `BackgroundTasks` (Celery+Redis only if volume later demands) |
| Deploy | Docker + Docker Compose (api + db + frontend) |

> **WhatsApp provider (supersedes PRD §3):** the PRD specified Meta Cloud API
> *direct, no BSP*. Per the owner, sending goes through **AiSensy** (a BSP on
> Meta) instead. Sends use AiSensy's Campaign API (a "Live" API campaign
> referenced by name + `templateParams`); replies/status arrive via AiSensy's
> webhook. Everything else (multi-tenancy, ROI, guardrails) is unchanged.

---

## 4. Proposed folder structure

```
/
├── CLAUDE.md
├── PRD.md
├── README.md
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + router registration
│   │   ├── config.py          # env-var settings (pydantic-settings)
│   │   ├── db.py              # engine, session, Base
│   │   ├── models/           # SQLAlchemy models (one file per table group)
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── auth/             # login, password hashing, JWT, deps
│   │   ├── routers/          # auth, workspaces, contacts, campaigns, webhooks
│   │   ├── services/         # whatsapp client, csv import, lapsed logic, roi
│   │   └── migrations/       # Alembic
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── pages/            # Login, Workspaces, Contacts, NewCampaign, Results
    │   ├── components/
    │   ├── api/              # fetch wrappers, auth token handling
    │   └── main.tsx
    ├── package.json
    ├── vite.config.ts
    └── Dockerfile
```

> NOTE: The repo root currently contains an unrelated `index.html` (a Formistry
> fashion product page). Confirm with the owner whether this project replaces
> that or lives in a subfolder before scaffolding (see open questions).

---

## 5. Data model

All business tables carry `workspace_id`. Fields may be *added*, not removed.

- **workspaces** — id, name, whatsapp_phone_number_id (informational),
  aisensy_api_key (per-workspace, overrides global env key; secret — never
  returned in API responses), lapsed_threshold_days (default 45), avg_ticket,
  created_at
- **users** — id, workspace_id (nullable → agency admin), email, password_hash,
  role (`admin` | `staff`), created_at
- **contacts** — id, workspace_id, name, phone (E.164), last_visit_date,
  created_at; UNIQUE (workspace_id, phone)
- **campaigns** — id, workspace_id, template_name, discount_offer, status,
  created_at
- **messages** — id, campaign_id, contact_id, workspace_id, status
  (`sent`|`delivered`|`read`|`failed`|`replied`), whatsapp_message_id, sent_at
- **replies** — id, message_id, contact_id, workspace_id, body, received_at

**Lapsed:** `last_visit_date` older than `workspaces.lapsed_threshold_days`.

**ROI:** sent / delivered / replied / booked; est. revenue = replied × avg_ticket.
(`booked` tracking mechanism is an open question — see below.)

---

## 6. API endpoints (v1)

```
POST   /auth/login
POST   /workspaces                        (agency admin only)
POST   /workspaces/{id}/contacts/upload   (CSV: name, phone, last_visit_date)
GET    /workspaces/{id}/contacts/lapsed
POST   /workspaces/{id}/campaigns         (create + send to lapsed)
GET    /workspaces/{id}/campaigns/{cid}   (status + ROI)
POST   /webhooks/aisensy?token=…          (AiSensy status + replies; token-gated)
```

Every `/workspaces/{id}/...` endpoint enforces that the caller belongs to (or is
agency admin over) that workspace.

---

## 7. Frontend screens (v1)

1. Login
2. Workspace list (admin) → select client
3. Contacts — CSV upload, table with lapsed rows highlighted
4. New Campaign — pick template, set discount, preview, "Send to X lapsed"
5. Campaign Results — ROI panel

Functional over fancy. "A tool that prints a receipt, not a design showcase."

---

## 8. Build phases (do one at a time)

- **Phase 1** — Postgres schema + FastAPI + auth + workspace-scoped CSV upload.
- **Phase 2** — Lapsed-contacts endpoint (configurable threshold).
- **Phase 3** — Send approved WhatsApp template via Meta Cloud API; keys from
  env; log every send.
- **Phase 4** — Webhook: status updates + replies, match to contact, mark
  `replied`; verify Meta signature + verify token.
- **Phase 5** — React dashboard: all screens + ROI panel.
- **Phase 6** — Dockerize (compose: api + db + frontend), env config, README,
  daily pg_dump backup command documented.

---

## 9. WhatsApp integration notes (not code) — via AiSensy

- Sending: `POST {AISENSY_API_BASE}/campaign/t1/api/v2` with `apiKey`,
  `campaignName` (a **Live** API campaign in AiSensy, bound to an approved
  template), `destination`, `userName`, `templateParams` (fills the template's
  variables; v1 sends a single discount/offer). Our `campaigns.template_name`
  column stores the AiSensy campaign name.
- API key resolves per-workspace first (`workspaces.aisensy_api_key`), else the
  global `AISENSY_API_KEY` env fallback.
- Templates (Marketing category) must still be **pre-approved by Meta** (through
  AiSensy) — recipients did not message first. Keep copy clean.
- AiSensy's send response carries **no WhatsApp message id**, so webhook
  status/replies match by **phone within the workspace**, applied to the
  contact's most recent message.
- Webhook: `POST /webhooks/aisensy?token=…` — gated on `AISENSY_WEBHOOK_TOKEN`
  (AiSensy does not sign callbacks like Meta). Needs a **public HTTPS URL**
  (ngrok in dev). Payload parsing is defensive; tighten once a real sample is
  captured.
- Verify current per-message pricing (Meta rate + AiSensy markup) before quoting
  a client — do not hardcode pricing assumptions.

---

## 10. Out of scope for v1

Auto-booking negotiation bot, POS/CRM integration, end-client billing,
multi-channel (SMS/email). WhatsApp only.

---

## 11. Decisions (resolved 2026-07-02)

1. **Repo placement** — the tool lives in `backend/` + `frontend/` subfolders at
   repo root. The existing `index.html` (Formistry fashion page) is left
   untouched.
2. **`booked` tracking** — v1 uses a **manual admin toggle**: an admin marks a
   message/contact as booked in the Campaign Results UI. `messages.booked`
   boolean drives the "booked" count; est. revenue = booked × avg_ticket, with
   replied shown alongside.
3. **Build scope** — full v1 (Phases 1–6) built in one pass: backend, WhatsApp
   send, webhook, React dashboard, Docker Compose.

### Implementation notes
- v1 uses SQLAlchemy `Base.metadata.create_all()` at startup for schema (kept
  simple per PRD); Alembic can be added later without a rewrite.
- A `POST /workspaces/{id}/messages/{mid}/booked` endpoint toggles the booked
  flag.
