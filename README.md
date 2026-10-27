# BloodBridge — Blood Bank Management System

BloodBridge helps blood banks, hospitals and authorised donor coordinators manage blood inventory, respond to urgent blood requests and coordinate with consenting donors, with city-level availability across Pakistan.

> **Demonstration data notice.** A fresh installation contains only **SYNTHETIC DEMO DATA** produced by a seeded generator. Donors, organisations, inventory and requests in a demo database are fictional. The interface labels them, and BloodBridge never sends messages to them. The system is **not** connected to any live blood-bank inventory.

> **Clinical notice.** Compatibility rules in BloodBridge are configurable operational aids for coordination. ABO/Rh compatibility, infectious-disease screening, storage, crossmatching and donor medical eligibility must be determined by qualified blood-bank personnel under applicable standards. BloodBridge does not provide medical triage or automated clinical approval.

## Status

Development proceeds in milestones. See [context.md](context.md) for current status and [CHANGELOG.md](CHANGELOG.md) for history.

| Milestone | Scope | Status |
|---|---|---|
| 1 | Foundation, auth, app shell, design system | Complete |
| 2 | Relational models and realistic synthetic data | Planned |
| 3 | Live dashboard, donor management | Planned |
| 4 | Inventory and blood requests | Planned |
| 5 | Donor matching, geographic availability | Planned |
| 6 | Reports, notifications, audit, security and QA | Planned |

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite 6, Tailwind CSS 3, Radix UI primitives (shadcn-style components), Recharts, React Router 6, TanStack Query 5, React Hook Form + Zod |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, Argon2 password hashing, JWT session cookie + CSRF token |
| Database | SQLite for zero-install local development; PostgreSQL 14+ for multi-user deployment (same models and migrations) |
| Testing | Pytest, Vitest + React Testing Library, Playwright (end-to-end, Milestone 6) |

## Prerequisites

- Python 3.12 or 3.13
- Node.js 20+ and npm
- Optional: PostgreSQL 14+

## Setup

### Windows PowerShell

```powershell
# from the repository root
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env        # then edit BB_SECRET_KEY

cd backend
..\.venv\Scripts\python.exe -m app.cli migrate
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# second terminal
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

### macOS / Linux

```bash
python3 -m venv .venv
./.venv/bin/pip install -r backend/requirements-dev.txt
cp .env.example .env

cd backend
../.venv/bin/python -m app.cli migrate
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000

cd ../frontend && npm install && npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`, so session cookies stay same-origin.

If `pip` reports `Cache entry deserialization failed`, add `--no-cache-dir`.

## Environment variables

All backend settings use the `BB_` prefix and are read from the environment or `.env`. See [.env.example](.env.example).

| Variable | Purpose | Default |
|---|---|---|
| `BB_ENVIRONMENT` | `development`, `test` or `production` | `development` |
| `BB_DATABASE_URL` | SQLAlchemy URL | `sqlite:///./bloodbridge.db` |
| `BB_SECRET_KEY` | Session-signing secret (required in production) | development placeholder |
| `BB_SESSION_MINUTES` | Session lifetime | `480` |
| `BB_COOKIE_SECURE` | Mark cookies `Secure` (enable behind HTTPS) | `false` |
| `BB_CORS_ORIGINS` | Comma-separated allowed origins | Vite dev URLs |
| `BB_EXPOSE_DOCS` | Force OpenAPI docs on or off | on except in production |
| `BB_LOW_STOCK_UNITS` | Low-stock threshold per blood group | `10` |
| `BB_EXPIRY_WARNING_DAYS` | "Expiring soon" window | `7` |
| `BB_AVAILABILITY_FRESH_DAYS` | Donor availability counted as current only if confirmed within this many days | `90` |
| `BB_WHOLE_BLOOD_DEFERRAL_DAYS` | Minimum interval after a whole-blood donation used for matching | `90` |
| `BB_DEMO_PASSWORD` | Password applied to demo staff accounts by the seed command | unset |
| `VITE_API_BASE` | Frontend API base path | `/api/v1` |

## Database and migrations

Run all commands from `backend/` using the virtual environment's Python:

```powershell
..\.venv\Scripts\python.exe -m app.cli migrate          # apply migrations (alembic upgrade head)
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

The schema is always built with Alembic migrations, never `create_all`.

To use PostgreSQL, create a database and set `BB_DATABASE_URL=postgresql+psycopg://user:password@host:5432/bloodbridge`.

## Staff accounts

Accounts are created from the command line. Passwords are prompted for, or read from an environment variable, and are never stored in the repository:

```powershell
..\.venv\Scripts\python.exe -m app.cli create-user --email admin@your-org.example --name "Platform Admin" --role admin
..\.venv\Scripts\python.exe -m app.cli create-user --email manager@your-org.example --name "Manager" --role bank_manager --bank-code BB-ISB-001
```

Roles: `admin` (platform administrator), `bank_manager` (one organisation), and `coordinator` (donor coordinator). Public users don't need an account.

## Tests and checks

```powershell
cd backend;  ..\.venv\Scripts\python.exe -m pytest;  ..\.venv\Scripts\python.exe -m ruff check .
cd frontend; npm test; npm run typecheck; npm run build
```

## API documentation

With the backend running in a non-production environment, open <http://127.0.0.1:8000/docs> (Swagger UI) or `/openapi.json`. Docs are disabled by default when `BB_ENVIRONMENT=production`.

## Known limitations

- Login rate limiting is in-process. A multi-instance deployment needs a shared store such as a database table or Redis.
- No external messaging (SMS, email or WhatsApp) is implemented. Nothing is ever sent to any contact.
- Sections scheduled for later milestones are visible in navigation but marked "Not available yet".

## Production deployment considerations

- Set `BB_ENVIRONMENT=production`, a strong `BB_SECRET_KEY` and `BB_COOKIE_SECURE=true`, and serve over HTTPS.
- Use PostgreSQL with regular backups. Run `python -m app.cli migrate` on each deploy.
- Serve the built frontend (`frontend/dist`) and the API from the same origin through a reverse proxy, or set `BB_CORS_ORIGINS` precisely.
- Never run demo seeding against a production database. The seed command refuses to run when `BB_ENVIRONMENT=production`.
