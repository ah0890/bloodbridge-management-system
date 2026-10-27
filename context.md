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
- **Milestone 2: Models and synthetic data.** Next. Draft files already exist in the working tree but are **uncommitted and untested**:
  - `backend/app/models/{donor,inventory,request,system}.py`
  - `backend/app/seed/{reference,generator,validate}.py`
  - `backend/app/services/{lifecycle,compatibility}.py`
- **Milestone 3: Dashboard and donors.** Draft files exist but are uncommitted and untested:
  - `backend/app/services/{metrics,settings,csv_export}.py`
  - `backend/app/schemas/{common,donor}.py`
  - `backend/app/api/v1/{donors,dashboard}.py`
- **Milestones 4–6:** not started.

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
  app/cli.py                migrate, create-user (seed-demo / validate-data arrive in Milestone 2)
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
- The local dev DB `backend/bloodbridge.db` (gitignored) contains a non-demo smoke-test admin. Delete the file before seeding demo data.

## Next steps (exact)

1. **Milestone 2:**
   1. Export the new models from `app/models/__init__.py`.
   2. Autogenerate migration `0002`.
   3. Add CLI commands `seed-demo [--reset] [--seed N] [--anchor-date]` and `validate-data`. The seed must refuse when `BB_ENVIRONMENT=production` and refuse to mix with non-synthetic data. Staff passwords come from `BB_DEMO_PASSWORD`, or are generated and printed once.
   4. Register every provenance-carrying model in `app/api/v1/meta.py` (`PROVENANCE_MODELS`).
   5. Write seed tests: reproducibility for the same seed and anchor, `validate_dataset` returning no problems, counts within targets, and every record synthetic.
   6. Write compatibility and lifecycle unit tests.
   7. Research public data sources (official PK health department and blood transfusion authority sites). Record findings in the README; don't scrape.
2. **Milestone 3:**
   1. Wire the `donors` and `dashboard` routers.
   2. Build the dashboard page (Recharts, filters), the donor list, detail, form and edit pages, and global search.
   3. Add tests.
3. **Milestones 4–6:** follow the spec. The README milestone table tracks scope.

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
- The user confirmed the commit identity `Ahaulakh0890 <Ahaulakh9800@gmail.com>` and authorised a push after each milestone. Never force-push.

## Privacy, provenance and security notes

- Never store credentials, tokens or donor data in this file or in commits.
- Synthetic contact data only uses `example.org` / `.example` domains and the unallocated `+92-000` prefix. Nothing is ever sent.
- Audit `details` must contain field names and IDs only, never personal values.
