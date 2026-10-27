# Changelog

All notable changes to BloodBridge are recorded here. Dates are in YYYY-MM-DD format.

## [Milestone 1] Foundation and application shell — 2026-10-27

### Added
- Backend skeleton (FastAPI, SQLAlchemy 2, Alembic, Pydantic v2), configured through `BB_`-prefixed environment variables.
- Portable `UTCDateTime` column type, plus deterministic constraint naming so the same migrations run on SQLite and PostgreSQL.
- Initial migration `0001` with the `blood_banks`, `users` and `audit_events` tables.
- Authentication:
  - Argon2 password hashing.
  - Signed JWT session in an HttpOnly, SameSite=Lax cookie.
  - CSRF double-submit token tied to the session.
  - Per-account/IP login rate limiting.
  - Generic error for failed logins, with timing equalisation for unknown accounts.
- Role-to-permission map (`admin`, `bank_manager`, `coordinator`) enforced by backend dependencies, plus helpers that confine bank managers to their own organisation.
- Append-only audit events for sign-in, sign-out and failed sign-ins.
- Security headers middleware, a restrictive CORS configuration and a generic 500 handler that doesn't leak internals.
- `GET /api/v1/meta/data-status`, which returns aggregate provenance counts used to show the synthetic data banner.
- Management CLI: `python -m app.cli migrate` and `python -m app.cli create-user`. Passwords are prompted for or read from an env var and never stored.
- Frontend (React 18, TypeScript, Vite 6, Tailwind 3):
  - Design tokens.
  - Shared UI primitives (button, badges, cards, loading/empty/error states, alerts).
  - Collapsible role-aware sidebar, header with breadcrumb, search, notifications and user menu.
  - Skip link, mobile navigation drawer, login page, and route guards.
  - Placeholder pages that say "Not available yet" for unbuilt sections.
- Tests:
  - Backend: 12 pytest tests covering hashing, login, cookie flags, rate limiting, CSRF, token tampering, audit records, security headers and the data-status endpoint.
  - Frontend: 4 Vitest tests covering the login redirect, permission-filtered navigation, direct-URL route blocking and the demo banner.
- `README.md`, `context.md`, `.env.example` and `.gitignore`.

### Fixed
- `BB_CORS_ORIGINS` accepts the documented comma-separated format (pydantic-settings no longer JSON-decodes it).
