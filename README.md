# speedtest-local

Self-hosted **LAN / Wi‑Fi** throughput and latency lab. Any device on your network opens a browser UI, runs a test against **your** server, and results land in **PostgreSQL** for history, filters, and charts.

This is intentionally **not** a public WAN speedtest clone: defaults, methodology, and UI are tuned for saturated local links (Ethernet + Wi‑Fi) with parallel streams, warmup, and cache-busting.

## Architecture (short)

- **Browser UI (React + Vite + Tailwind + Recharts)** drives measurements using `fetch()` against the API. The UI saves completed runs via `POST /api/tests`.
- **API (FastAPI + SQLAlchemy 2 + Alembic)** serves measurement endpoints (`/api/ping`, `/api/download`, `/api/upload`) and persistence/analytics (`/api/tests`, `/api/stats/*`, `/api/clients`, `/api/settings`, `/api/anomalies`, `/api/export/*`, optional `/api/admin/prune`). Durable defaults and policy live in `app_settings`.
- **PostgreSQL** stores long-lived history with indexes aimed at time ranges + client/network filters. Optional `test_samples` rows capture per-phase series (ping RTTs, aggregate throughput snapshots).
- **Docker Compose** brings up `postgres`, `backend`, and `frontend` (nginx serving the SPA and reverse-proxying `/api/*` to the API). See `frontend/nginx.conf`.

```mermaid
flowchart LR
  Browser -->|same origin /api| Nginx
  Nginx -->|proxy| API
  API --> Postgres
```

## Repository layout

```
.
├── backend/                 # FastAPI app, Alembic migrations, pytest
├── frontend/                # React SPA, nginx.conf for docker image
├── probe-agent/             # optional headless CLI (`probe run`)
├── docker-compose.yml
├── Makefile
├── docs/
└── .env.example
```

## Why this stack

- **FastAPI (vs Go Fiber here)**: automatic OpenAPI, excellent request/response typing with Pydantic v2, and a mature Python story for SQL analytics (`percentile_cont`, `date_trunc`, JSONB). This project is I/O-heavy and iterates on measurement rules and reporting—Python keeps that loop fast without sacrificing production rigor.
- **PostgreSQL**: durable history, flexible `JSONB` for raw browser metrics, and straightforward time-bucket aggregations for charts. SQLite would be a poor fit for long retention + concurrent writers on a busy LAN.
- **React + Vite + Tailwind + Recharts**: fast dev UX, accessible components, and charting that is “good enough” for home-lab analytics without shipping a full BI suite.

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8080` (override `FRONTEND_PORT` in `.env`).

- API OpenAPI: `http://localhost:8080/docs`
- Health: `http://localhost:8080/health`
- Metrics: `http://localhost:8080/metrics` (Prometheus text format; toggle with `ENABLE_METRICS`)

### Demo data

```bash
make migrate   # usually already applied by backend entrypoint
make seed
```

## Makefile targets

| Target    | Purpose                                  |
| --------- | ---------------------------------------- |
| `make up` | `docker compose up --build -d`           |
| `make down` | tear down stack                        |
| `make logs` | follow compose logs                    |
| `make test` | backend `pytest` + frontend `vitest` + probe `pytest` |
| `make probe-run` | one-shot headless run against `http://127.0.0.1:8080` |
| `make prune` | dry-run age prune (needs `DATABASE_URL` DB) |
| `make export` | prints example `curl` for `/api/export/tests.csv` |
| `make lint` | `ruff` + `eslint`                      |
| `make fmt`  | `ruff format` + `prettier`             |
| `make migrate` | `alembic upgrade head` (in container) |
| `make seed` | synthetic history                      |

**Note:** integration tests expect PostgreSQL on `DATABASE_URL` (defaults to `127.0.0.1:5432` with compose port mapping). Unit tests run without a database.

## Local development (without Docker UI)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://speedtest:speedtest@localhost:5432/speedtest
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000` (see `frontend/vite.config.ts`). Set `VITE_API_BASE_URL` only when the UI and API are on different origins.

## Measurement summary & limitations

Browser tests are **estimates**. They vary with CPU scheduling, browser networking stack, Wi‑Fi airtime, driver offload, and concurrent traffic. The implementation avoids fake precision: it records what was measured and stores rich `raw_metrics_json` for debugging.

**Packet loss** is not reported as a reliable metric: ordinary browser `fetch()` cannot observe dropped IP packets or Wi‑Fi retries. See `docs/measurement-methodology.md`.

## Historical visualization

Runs are stored per client (`clients.stable_id` from `localStorage`), label, network tag, user agent, and timestamps. The analytics page queries `/api/stats/summary` (percentiles + averages) and `/api/stats/timeseries` (bucketed `date_trunc` aggregates). The UI adds a simple moving average as a visual aid, not a ground-truth smoother.

## Multi-server testing (today + next step)

Today: set `SERVER_LABEL` (env) or override per run from the UI / API. Filter charts and history by `server_label`.

Next: add a `servers` registry table and UI picker if you deploy multiple measurement endpoints (e.g., wired gateway vs Wi‑Fi AP host).

## Documentation

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/measurement-methodology.md`](docs/measurement-methodology.md)
- [`docs/api.md`](docs/api.md)
- [`docs/deployment.md`](docs/deployment.md)
- [`docs/probe-agent.md`](docs/probe-agent.md)
- [`docs/anomaly-detection.md`](docs/anomaly-detection.md)

## License

See `LICENSE`.
