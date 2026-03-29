# Headless probe agent

The [`probe-agent`](../probe-agent/) package runs the same measurement phases as the browser (ping, download, upload) and submits a completed run with `POST /api/tests`. Use it for unattended baselines on a small host (Raspberry Pi, NUC, always-on server).

## Install

```bash
cd probe-agent
pip install -e .
```

## One-shot run

Against the docker UI (nginx on 8080):

```bash
probe run --server http://127.0.0.1:8080
```

Against the API directly:

```bash
probe run --server http://127.0.0.1:8000
```

## Cron (host)

Run every hour, log failures:

```cron
0 * * * * /usr/local/bin/probe run --server http://192.168.1.10:8080 >>/var/log/speedtest-probe.log 2>&1
```

## systemd timer

`/etc/systemd/system/speedtest-probe.service`:

```ini
[Unit]
Description=speedtest-local headless probe

[Service]
Type=oneshot
ExecStart=/usr/local/bin/probe run --server http://127.0.0.1:8080
```

`/etc/systemd/system/speedtest-probe.timer`:

```ini
[Unit]
Description=Hourly speedtest-local probe

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Then: `systemctl enable --now speedtest-probe.timer`.

## Docker Compose profile

See root `docker-compose.yml`: service `probe-scheduled` under profile `probe` runs `probe run` in a loop (default sleep 3600s).

```bash
docker compose --profile probe up -d probe-scheduled
```
