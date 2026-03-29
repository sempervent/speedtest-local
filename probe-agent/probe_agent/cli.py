"""Typer CLI: probe run | config show | healthcheck."""

from __future__ import annotations

import json
import time
import uuid
from typing import Annotated, Any

import httpx
import typer

from probe_agent.measure import measure_download_mbps, measure_ping, measure_upload_mbps
from probe_agent.stats import mean, successive_jitter_ms

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _client(base: str, timeout: float, verify: bool) -> httpx.Client:
    return httpx.Client(base_url=base.rstrip("/"), timeout=timeout, verify=verify)


@app.command("healthcheck")
def healthcheck(
    server: Annotated[str, typer.Option("--server", "-s", help="API base URL")] = "http://127.0.0.1:8080",
    timeout: Annotated[float, typer.Option("--timeout")] = 30.0,
    insecure: Annotated[bool, typer.Option("--insecure", help="Disable TLS verify")] = False,
) -> None:
    with _client(server, timeout, not insecure) as c:
        r = c.get("/ready")
        r.raise_for_status()
        typer.echo(r.json())


@app.command("config")
def config_show(
    server: Annotated[str, typer.Option("--server", "-s")] = "http://127.0.0.1:8080",
    timeout: Annotated[float, typer.Option("--timeout")] = 30.0,
    insecure: Annotated[bool, typer.Option("--insecure")] = False,
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
) -> None:
    with _client(server, timeout, not insecure) as c:
        r = c.get("/api/config")
        r.raise_for_status()
        data = r.json()
    if output == "json":
        typer.echo(json.dumps(data, indent=2))
    else:
        typer.echo(json.dumps(data, indent=2))


@app.command("run")
def run_probe(
    server: Annotated[str, typer.Option("--server", "-s")] = "http://127.0.0.1:8080",
    client_label: Annotated[str | None, typer.Option("--client-label")] = None,
    network_label: Annotated[str | None, typer.Option("--network-label")] = None,
    download_seconds: Annotated[float | None, typer.Option("--download-seconds")] = None,
    upload_seconds: Annotated[float | None, typer.Option("--upload-seconds")] = None,
    parallel_streams: Annotated[int | None, typer.Option("--parallel-streams")] = None,
    payload_bytes: Annotated[int | None, typer.Option("--payload-bytes")] = None,
    timeout: Annotated[float, typer.Option("--timeout")] = 120.0,
    insecure: Annotated[bool, typer.Option("--insecure")] = False,
    output: Annotated[str, typer.Option("--output", "-o")] = "table",
    stable_id: Annotated[str | None, typer.Option("--stable-id", help="UUID for client correlation")] = None,
) -> None:
    sid = stable_id or str(uuid.uuid4())
    with _client(server, timeout, not insecure) as c:
        cr = c.get("/api/config")
        cr.raise_for_status()
        cfg = cr.json()
        d = cfg["defaults"]
        dl_s = download_seconds if download_seconds is not None else float(d["download_duration_sec"])
        ul_s = upload_seconds if upload_seconds is not None else float(d["upload_duration_sec"])
        streams = parallel_streams if parallel_streams is not None else int(d["parallel_streams"])
        chunk = payload_bytes if payload_bytes is not None else int(d["payload_bytes"])
        ping_n = int(d["ping_samples"])
        warm = int(d["warmup_ping_samples"])
        server_label = str(cfg["server_label"])

        t0 = time.perf_counter()
        rtts, ping_meta = measure_ping(c, warmup=warm, samples=ping_n)
        dl_b, dl_mbps, _ = measure_download_mbps(
            c, duration_sec=dl_s, streams=streams, chunk_bytes=min(chunk, 32 * 1024 * 1024)
        )
        ul_b, ul_mbps, _ = measure_upload_mbps(
            c,
            duration_sec=ul_s,
            streams=streams,
            chunk_bytes=min(max(chunk // 4, 262_144), 8 * 1024 * 1024),
        )
        wall = time.perf_counter() - t0

        samples: list[dict[str, Any]] = []
        ping_t0 = 0.0
        for i, v in enumerate(rtts):
            samples.append(
                {
                    "phase": "ping",
                    "t_offset_ms": i * 25.0,
                    "value": v,
                    "unit": "ms",
                    "metadata": {"index": i, "source": "probe"},
                }
            )
        samples.append(
            {
                "phase": "download",
                "t_offset_ms": wall * 500,
                "value": dl_mbps,
                "unit": "Mbps",
                "metadata": {"aggregate": True, "source": "probe"},
            }
        )
        samples.append(
            {
                "phase": "upload",
                "t_offset_ms": wall * 1000,
                "value": ul_mbps,
                "unit": "Mbps",
                "metadata": {"aggregate": True, "source": "probe"},
            }
        )

        body = {
            "started_at": None,
            "completed_at": None,
            "client_stable_id": sid,
            "client_label": client_label,
            "network_label": network_label,
            "server_label": server_label,
            "latency_ms_avg": mean(rtts),
            "jitter_ms": successive_jitter_ms(rtts),
            "download_mbps": dl_mbps,
            "upload_mbps": ul_mbps,
            "packet_loss_pct": None,
            "download_bytes_total": dl_b,
            "upload_bytes_total": ul_b,
            "duration_seconds": wall,
            "success": True,
            "raw_metrics_json": {**ping_meta, "probe": True},
            "browser_user_agent": "speedtest-local-probe/0.1",
            "samples": samples,
        }
        pr = c.post("/api/tests", json=body)
        if pr.status_code >= 400:
            typer.echo(pr.text, err=True)
            raise typer.Exit(1)
        saved = pr.json()

    if output == "json":
        typer.echo(json.dumps({"saved": saved, "summary": body}, indent=2, default=str))
    else:
        typer.echo(
            f"Saved run #{saved.get('id')}  ↓{dl_mbps:.1f} Mbps  ↑{ul_mbps:.1f} Mbps  "
            f"ping {mean(rtts):.2f} ms  jitter {successive_jitter_ms(rtts):.2f} ms"
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
