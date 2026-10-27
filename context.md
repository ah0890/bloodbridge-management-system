# BloodBridge — Session Handoff Context

Read this first in every new session. Then check the actual repository state (`git status`, `git log`) and resume from **Next steps**.

## Objective and users

BloodBridge is a blood bank management system for Pakistan. It covers inventory, urgent blood requests, consenting donors, donor matching and city-level availability. Users:

- Platform Administrator (`admin`).
- Blood Bank Manager (`bank_manager`), confined to one organisation.
- Donor Coordinator (`coordinator`).
- Public users, who are unauthenticated.

Seeded data is **SYNTHETIC DEMO DATA** and must always be labelled. The system is not connected to any live inventory.

The full product specification is the original task prompt, which isn't stored in the repo. The README summarises scope.

## Current status

- **Milestone 1: Foundation.** Complete. Committed and pushed; see git log.
- **Milestone 2: Models and synthetic data.** Complete. Committed and pushed.
- **Milestone 3: Dashboard and donors.** Complete. Committed and pushed.
- **Milestone 4: Inventory and requests.** Next.
- **Milestones 5–6:** not started.

## Architecture and important paths

```
backend/
  app/core/config.py        Settings (BB_ env prefix, .env or ../.env)
  app/core/security.py      Argon2, JWT session cookie, CSRF, in-process rate limiter
  app/core/permissions.py   Role → permission map (source of truth)
  app/api/deps.py           get_current_user (+CSRF check on unsafe methods), require(perm), org_scope, record_provenance
  app/api/v1/               Routers (auth, meta; more per milestone), mounted at /api/v1
  app/db/base.py            Base, naming convention, UTCDateTime, TimestampMixin
  app/models/               ORM models; enums.py holds all domain enums (stored as constrained strings)
  app/services/audit.py     audit.record(...) — never pass donor PII in details
  app/cli.py                migrate, create-user, seed-demo, validate-data
  app/seed/                 reference data, deterministic generator, validate_dataset
  app/services/compatibility.py  ABO/RhD per-component rules (RULES_VERSION)
  app/services/lifecycle.py      request status transitions
  migrations/               Alembic (render_as_batch for SQLite)
  tests/                    pytest; conftest builds schema via Alembic in a temp SQLite DB
frontend/
  src/styles/tokens.css     Design tokens (single source of colours)
  src/lib/api.ts            fetch wrapper (credentials + X-CSRF-Token from bb_csrf cookie)
  src/lib/auth.tsx          AuthProvider/useAuth (session from /auth/me, can(perm))
  src/app/                  Layout, Sidebar, Header, nav config, routes, RequirePerm, DemoBanner
  src/components/ui/        Button, Badge/StatusBadge/ProvenanceBadge/BloodGroupBadge, Card, states
  src/pages/                LoginPage, UnavailablePage
```

## Key decisions

- **Database:** SQLite by default, PostgreSQL via `BB_DATABASE_URL`. The schema is only ever built by Alembic.
- **Sessions:** HttpOnly SameSite=Lax cookie `bb_session` (JWT) plus a JS-readable `bb_csrf`. Every non-GET request needs an `X-CSRF-Token` header matching the token claim. Vite proxies `/api`, so cookies stay same-origin.
- **Authorisation:**
  - Enforced only on the backend through `require(Perm...)`. The frontend mirrors the `permissions` list returned by `/auth/me`.
  - Bank managers are confined with `org_scope` / `ensure_org_access`.
- **Provenance:** every operational table has `provenance` (synthetic, imported or verified). Records created by demo staff accounts (`users.is_demo`) are labelled synthetic (`record_provenance`).
- **Inventory model (Milestone 2 onwards):** `inventory_batches` hold lots with a single status each. A partial reserve or issue splits the batch. `stock_movements` is an immutable ledger.
- **Python:** the venv uses Python 3.13. The 3.12 launcher entry on this machine points to a missing install.

## Tests actually executed (Milestone 3)

- Backend `pytest`: 68 passed. `ruff check .` passed on the whole backend.
- Frontend: `vitest` 12 passed, `tsc` clean, `vite build` succeeded. The bundle is about 480 kB minified (a chunk-size warning only).
- Playwright screenshots (a scratch script outside the repo) of the dashboard, donors, donor detail, donor form, blood banks and search pages at 1440px, plus the dashboard and donors at 390px.
  - No page-level horizontal overflow.
  - The only console errors were the expected 401 from the session check before login and 404s from `/notifications/unread-count` (the endpoint arrives in Milestone 6).

## Tests actually executed (Milestone 2)

- Backend `pytest`: 42 passed (auth 12, seed 11, rules 19). `ruff check` passed on all committed backend files.
- `seed-demo` on a scratch DB and on the local dev DB:
  - 32 banks, 1,000 donors, 1,379 donations, 447 batches, 1,191 movements, 160 requests, 265 contact attempts.
  - `validate_dataset` reported no problems.
  - KPI sanity check: 321 currently available donors and 796 usable units; A−, B− and AB− stock is low, as expected.

## Tests actually executed (Milestone 1)

- Backend: `pytest` gave 12 passed. `ruff check` passed on Milestone 1 files.
- Frontend: `vitest run` gave 4 passed. `tsc -b --noEmit` was clean. `vite build` succeeded.
- Manual smoke test:
  - Ran migrations, then created an admin through the CLI with a random password from an env var.
  - Through uvicorn, `/api/health`, `/auth/login` and `/auth/me` worked, and `/docs` returned 200.
  - The Vite dev server proxied `/api/health` correctly.
- **Not done:** a visual check in a real browser. No browser tooling was available; Playwright is planned for Milestone 6.

## Known issues and limitations

- pip's cache on this machine is corrupted (`Cache entry deserialization failed`). Use `pip install --no-cache-dir`. Python downloads from PyPI are slow here.
- The login rate limiter is in-process and doesn't work across multiple instances.
- Starlette warns that `httpx` with `TestClient` is deprecated (it suggests `httpx2`). This is harmless for now.
- Recharts 2.x is installed. npm flags it as no longer actively developed; consider moving to v3.
- The local dev DB `backend/bloodbridge.db` (gitignored) is seeded with synthetic data. Recreate it with `seed-demo --reset`; set `BB_DEMO_PASSWORD` in `.env` to choose the demo password.
- `/notifications/unread-count` doesn't exist yet. The header bell quietly shows no count until Milestone 6.
- The frontend bundle is a single chunk of about 480 kB. Consider route-level code splitting.
- The seed doesn't create `match_runs`. Requests in `matches_found` have contact attempts but no stored match run until the Milestone 5 engine exists.
- The data-source review (`docs/DATA_SOURCES.md`) found no live inventory and no clearly licensed directory. The CSV/JSON import is planned for Milestone 6.

## Next steps (exact)

1. **Milestone 4: Inventory and requests.**
   1. Inventory API. Add batches (received → quarantined); release after screening passes or discard on failure. Reserve or issue partial quantities by splitting the batch inside a transaction, using a conditional `UPDATE ... WHERE status='available' AND quantity>=n` with a rowcount check. Also cover releasing reservations, transfers (a `transfer_out` row plus a new batch at the destination), expiry write-off, the movement ledger, and manager org isolation through `ensure_org_access`.
   2. Requests API. Public submission (rate-limited, consent required, with a confirmation code and a public status lookup that returns no PII) and staff submission. Enforce the lifecycle through `services/lifecycle.check_transition`, plus assignment, a status history, and fulfilment derived from issued units (`units_fulfilled`). Cancellation.
   3. Frontend pages: inventory list and detail with actions; requests list, detail (timeline, reserve and issue from compatible stock) and form; and the public portal at `/public` (request form, confirmation, emergency guidance, public availability as aggregate counts by city and group with no PII).
   4. Donations page: record a donation, which creates a quarantined batch and updates the donor's `last_donation_date`.
   5. Tests: race and duplicate issuance, unusable-stock issuance rejected, transitions, and permissions.
2. **Milestones 5–6:** follow the spec. Matching uses `services/compatibility.py`; reports, notifications, audit UI, users, settings, imports and Playwright E2E are in Milestone 6.

## Commands

```powershell
# backend (from backend/)
..\.venv\Scripts\python.exe -m app.cli migrate
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check .
# frontend (from frontend/)
npm run dev; npm test; npm run typecheck; npm run build
```

## Configuration variable names

`BB_ENVIRONMENT`, `BB_DATABASE_URL`, `BB_SECRET_KEY`, `BB_SESSION_MINUTES`, `BB_COOKIE_SECURE`, `BB_CORS_ORIGINS`, `BB_EXPOSE_DOCS`, `BB_LOGIN_MAX_ATTEMPTS`, `BB_LOGIN_WINDOW_SECONDS`, `BB_LOW_STOCK_UNITS`, `BB_EXPIRY_WARNING_DAYS`, `BB_AVAILABILITY_FRESH_DAYS`, `BB_WHOLE_BLOOD_DEFERRAL_DAYS`, `BB_DEMO_PASSWORD`, `VITE_API_BASE`, `VITE_API_PROXY_TARGET`.

## Git

- Branch `main`, remote `origin` → github.com/ah0890/bloodbridge-management-system.
- The user confirmed the commit identity `Ahaulakh0890 <Ahaulakh9800@gmail.com>` and authorised a push after each milestone.
- **The user does not want Claude attribution.** Never add `Co-Authored-By: Claude` or "Generated with Claude Code" lines. On 2026-10-27 the Milestone 1 and 2 commits were rewritten without the trailer (trees unchanged) and force-pushed with lease, with the user's explicit approval: Milestone 1 is now `5c9d944` and Milestone 2 is `7ba18d9`.
- Otherwise never force-push.

## Privacy, provenance and security notes

- Never store credentials, tokens or donor data in this file or in commits.
- Synthetic contact data only uses `example.org` / `.example` domains and the unallocated `+92-000` prefix. Nothing is ever sent.
- Audit `details` must contain field names and IDs only, never personal values.
