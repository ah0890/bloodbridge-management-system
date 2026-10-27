# Changelog

All notable changes to BloodBridge are recorded here. Dates are in YYYY-MM-DD format.

## [Milestone 2] Relational models and synthetic demo data — 2026-10-27

### Added
- Migration `0002` adds 14 tables:
  - `donors`, `donor_consents` (append-only ledger) and `donor_availability_changes`.
  - `donations` and `contact_attempts`.
  - `inventory_batches` (one status per lot) and `stock_movements` (immutable ledger).
  - `blood_requests`, `request_status_changes`, `match_runs` and `match_results`.
  - `notifications`, `dataset_imports` and `app_settings`.
  - The tables use CHECK constraints (quantities, units, expiry after collection, coordinate ranges), foreign keys and indexes.
- `services/compatibility.py`: explicit, versioned ABO/RhD tables for each component.
  - Red cells and whole blood (ABO-identical) are handled separately from plasma and cryoprecipitate, where compatibility is reversed and RhD is ignored.
  - ABO non-identical platelets are flagged "requires review" rather than accepted.
- `services/lifecycle.py`: the request status transition graph. `FULFILLED` requires all units to be recorded; `PARTIALLY_FULFILLED` requires some.
- Deterministic synthetic generator (`app/seed`). See the README section "Demo data".
- `validate_dataset` consistency checker and the `validate-data` CLI command.
- `seed-demo` CLI command:
  - Refuses to run in production and refuses to mix with operational data.
  - `--reset` removes synthetic rows only.
  - The demo password comes from `BB_DEMO_PASSWORD` or is generated and printed once.
- `/meta/data-status` now counts provenance across organisations, donors, requests and inventory.
- `docs/DATA_SOURCES.md`: review of PBTA, opendata.com.pk and Safe Blood Transfusion Programme sources. None offers live inventory or clear reuse terms, so nothing is integrated.
- Tests (42 backend in total):
  - Seed consistency, reproducibility, provenance and unreachable contacts.
  - Production, duplicate and mixing guards, and reset preserving real records.
  - Validator detection and full-size targets.
  - Compatibility tables and lifecycle rules.

### Fixed
- The generator no longer closes requests that are meant to stay open (caught by the lifecycle guard).
- `BB_DEMO_PASSWORD` is now read through settings, so a value in `.env` works.

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
