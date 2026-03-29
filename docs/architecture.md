# Architecture

## Components

### Frontend (`frontend/`)

- **Stack:** React 18, TypeScript, Vite, Tailwind CSS, Recharts.
- **Routing:** `react-router-dom` with pages for run, history, analytics, detail, and settings.
- **Networking:** relative `/api` calls in Docker (nginx proxy) or Vite dev proxy locally.
- **Client identity:** stable UUID in `localStorage` (`speedtest_client_stable_id`) sent as `client_stable_id` when saving runs so rows can be correlated across sessions.

### Backend (`backend/`)

- **Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, `psycopg` (v3) against PostgreSQL.
- **Measurement endpoints:** intentionally boring HTTP primitives:
  - `GET /api/ping` — tiny JSON echo; RTT measured in the browser.
  - `GET /api/download?bytes=…` — streaming, non-cacheable random bytes.
  - `POST /api/upload` — streaming request body counter (rejects oversize bodies).
- **Persistence endpoints:** CRUD-ish access to runs, clients, exports, and aggregated stats used by charts.
- **Settings:** `GET/PATCH /api/settings` read and update the singleton row in PostgreSQL (`app_settings`). Environment variables seed that row on first boot only.
- **Anomalies:** after successful saves, optional regression hints in `anomaly_events` (see `docs/anomaly-detection.md`).
- **Export:** streaming `GET /api/export/tests.{csv,json}` with the same filters as history.
- **Admin:** optional `POST /api/admin/prune` (token header) and `scripts/prune.py` for age-based cleanup.

### Database

Tables (see Alembic migrations `0001`+):

- `clients` — optional `stable_id` (UUID), parsed hints from UA, `metadata` JSONB.
- `test_runs` — summarized metrics + `raw_metrics_json` JSONB + failure info.
- `test_samples` — optional per-sample rows (phase, offset, value, unit, metadata).
- `app_settings` — singleton policy and default test parameters.
- `anomaly_events` — optional regression hints tied to runs.

Indexes focus on `(created_at)`, `(client_id, created_at)`, `(network_label, created_at)`, `(server_label, created_at)`, and `(success, created_at)`.

### Reverse proxy

The production image bundles **nginx** (`frontend/nginx.conf`) to:

- serve the SPA (`try_files … /index.html`)
- proxy API, OpenAPI, metrics, and health to the backend container

This yields a single origin for browsers, minimizing CORS friction on a LAN.

## Request path & observability

- **Structured-ish logs:** `TimingMiddleware` emits one JSON line per request with duration.
- **Prometheus:** `/metrics` exposes counters for bytes moved by upload/download handlers (plus default process metrics), gated by `ENABLE_METRICS`.
- **Health:** `/health` liveness; `/ready` checks database connectivity (and migration version) for orchestration.

## Threat model (home lab)

This service is aimed at **trusted LANs**. It does not ship authentication. If you expose it beyond your network, put it behind SSO/VPN and rate limits.
