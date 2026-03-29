# HTTP API

Interactive documentation is served at `/docs` (Swagger UI) and `/redoc` when the backend is reachable (also proxied via the Dockerized nginx UI).

## Core endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/health` | Liveness |
| `GET` | `/metrics` | Prometheus text exposition (optional) |
| `GET` | `/api/config` | Public defaults for the UI (durations, streams, caps) |
| `GET` | `/api/ping` | Latency probe (JSON echo + cache-busting headers) |
| `GET` | `/api/download` | Streaming random bytes (`bytes` query param, capped) |
| `POST` | `/api/upload` | Accepts request body stream; returns `bytes_received` |
| `POST` | `/api/tests` | Persist a completed run (+ optional samples) |
| `GET` | `/api/tests` | Paginated history with filters + sorting |
| `GET` | `/api/tests/export?format=csv|json` | Bulk export (bounded `limit`) |
| `GET` | `/api/tests/{id}` | Run detail including samples |
| `GET` | `/api/stats/summary` | Aggregates + PostgreSQL percentiles |
| `GET` | `/api/stats/timeseries` | Bucketed averages (`hour|day|week|month`) |
| `GET` | `/api/clients` | Known clients (for filters) |
| `GET` | `/api/settings` | Admin view of merged defaults |
| `PATCH` | `/api/settings` | In-memory overrides (non-durable) |

## Common query parameters

### `/api/tests`

- `page`, `page_size`
- `from`, `to` (ISO datetimes)
- `client_id`, `network_label`, `server_label`, `success`
- `sort` ∈ `created_at`, `download_mbps`, `upload_mbps`, `latency_ms_avg`
- `order` ∈ `asc`, `desc`

### `/api/stats/*`

- `client_id`, `network_label`, `server_label`, `success`
- `from`, `to`
- `bucket` (timeseries only)

## CORS

`CORS_ORIGINS` is a comma-separated list of allowed browser origins. When serving UI + API on the same host via nginx, CORS is less critical but still matters for local Vite dev.

## Versioning

Phase 1 uses unversioned paths under `/api`. If breaking changes are introduced later, add `/api/v2` routers while keeping v1 for historical clients.
