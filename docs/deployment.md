# Deployment notes

## Docker Compose (recommended)

1. Copy `.env.example` → `.env`.
2. `docker compose up --build -d`.
3. Visit `http://localhost:${FRONTEND_PORT:-8080}`.

The `backend` service runs `alembic upgrade head` before `uvicorn` starts, so fresh databases migrate automatically.

### Health checks

- Postgres: `pg_isready`
- Backend: Python `urllib` probe to `/ready` (DB + migration sanity)
- Frontend container: implicit via nginx start (compose currently keys off backend health before starting UI)

### Logs

`docker compose logs -f backend` shows structured JSON request lines plus uvicorn access logs.

## TLS termination

The bundled nginx config listens on plain HTTP for simplicity on a trusted LAN. For remote access:

- Put **Caddy**, **Traefik**, or another TLS proxy in front of the UI container, or
- Mount certificates into a custom nginx config and terminate TLS there.

Update `CORS_ORIGINS` to match the `https://` origin you expose.

## Backups

Back up the `pgdata` Docker volume (or your external Postgres instance).

## Retention and pruning

Set **retention (days)** in **Settings** (`app_settings.retention_days`) as the policy hint, then run deletes periodically:

- `python scripts/prune.py` in the backend tree (see `--help`), or
- `POST /api/admin/prune` with header `X-Admin-Token: $ADMIN_PRUNE_TOKEN` when that env var is set.

## Scheduled synthetic tests

Use the bundled **probe agent** (`probe-agent/`, `docs/probe-agent.md`) or the Compose profile `probe` (`probe-scheduled` service). For a trivial availability ping only:

```bash
while true; do
  curl -fsS "http://speedtest.lan/ready" >/dev/null
  sleep 300
done
```

Keep concurrency low on Wi‑Fi so probes do not steal airtime from real users.

## Resource limits

Large parallel streams against multi-gigabit LANs can move substantial data. Tune:

- `DOWNLOAD_MAX_BYTES` / `UPLOAD_MAX_BYTES`
- UI durations and stream counts

…and monitor disk I/O on Postgres if you store high-frequency `test_samples`.
