# speedtest-local probe agent

Headless client for [speedtest-local](../README.md): runs ping / download / upload against the API and submits a completed run (same measurement shape as the browser UI).

## Install (local)

```bash
cd probe-agent
pip install -e ".[dev]"
probe --help
```

## Commands

- `probe healthcheck --server URL` — GET `/ready`
- `probe config show --server URL` — GET `/api/config`
- `probe run --server URL` — measure and POST `/api/tests`

Use `--insecure` only if you terminate TLS with a private CA and need to skip verify.

## Docker / Compose

Build and run on the compose network (hourly loop):

```bash
docker compose --profile probe up -d probe-scheduled
```

Override the sleep interval in `docker-compose.yml`, or run a one-off (joins the default network so `backend` resolves):

```bash
docker compose run --rm probe-scheduled sh -c "probe run --server http://backend:8000"
```

## Scheduling elsewhere

See [docs/probe-agent.md](../docs/probe-agent.md) for cron and systemd examples.
