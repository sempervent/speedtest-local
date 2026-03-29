"""HTTP measurement primitives (no browser). Client must use httpx.Client(base_url=...)."""

from __future__ import annotations

import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from probe_agent.stats import mean, stddev, successive_jitter_ms


def _cb() -> str:
    return str(uuid.uuid4())


def ping_rtt(client: httpx.Client) -> float:
    t0 = time.perf_counter()
    r = client.get("/api/ping", params={"_cb": _cb()})
    r.raise_for_status()
    r.json()
    return (time.perf_counter() - t0) * 1000


def measure_ping(
    client: httpx.Client,
    *,
    warmup: int,
    samples: int,
) -> tuple[list[float], dict[str, Any]]:
    for _ in range(warmup):
        ping_rtt(client)
    rtts: list[float] = []
    for _ in range(samples):
        rtts.append(ping_rtt(client))
    return rtts, {
        "avg_ms": mean(rtts),
        "min_ms": min(rtts),
        "max_ms": max(rtts),
        "stddev_ms": stddev(rtts),
        "jitter_ms": successive_jitter_ms(rtts),
    }


def _download_chunk(client: httpx.Client, nbytes: int) -> int:
    r = client.get("/api/download", params={"bytes": nbytes, "_cb": _cb()})
    r.raise_for_status()
    return len(r.content)


def measure_download_mbps(
    client: httpx.Client,
    *,
    duration_sec: float,
    streams: int,
    chunk_bytes: int,
    warmup_sec: float = 0.5,
) -> tuple[int, float, float]:
    deadline = time.perf_counter() + duration_sec
    warm_end = time.perf_counter() + min(warmup_sec, duration_sec * 0.1)

    lock_time = {"end": deadline, "warm": warm_end}
    total = {"n": 0}

    def worker() -> None:
        while time.perf_counter() < lock_time["end"]:
            if time.perf_counter() < lock_time["warm"]:
                _download_chunk(client, min(chunk_bytes, 2 * 1024 * 1024))
                continue
            total["n"] += _download_chunk(client, chunk_bytes)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=streams) as ex:
        futs = [ex.submit(worker) for _ in range(streams)]
        for f in as_completed(futs):
            f.result()
    elapsed = time.perf_counter() - t0
    b = total["n"]
    mbps = (b * 8) / 1e6 / max(elapsed, 1e-9)
    return b, mbps, elapsed


def _upload_chunk(client: httpx.Client, data: bytes) -> int:
    r = client.post(
        "/api/upload",
        params={"_cb": _cb()},
        content=data,
        headers={"Content-Type": "application/octet-stream"},
    )
    r.raise_for_status()
    j = r.json()
    return int(j.get("bytes_received", 0))


def measure_upload_mbps(
    client: httpx.Client,
    *,
    duration_sec: float,
    streams: int,
    chunk_bytes: int,
    warmup_sec: float = 0.5,
) -> tuple[int, float, float]:
    buf = os.urandom(chunk_bytes)
    deadline = time.perf_counter() + duration_sec
    warm_end = time.perf_counter() + min(warmup_sec, duration_sec * 0.1)
    lock_time = {"end": deadline, "warm": warm_end}
    total = {"n": 0}

    def worker() -> None:
        while time.perf_counter() < lock_time["end"]:
            if time.perf_counter() < lock_time["warm"]:
                _upload_chunk(client, buf[: min(len(buf), 512 * 1024)])
                continue
            total["n"] += _upload_chunk(client, buf)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=streams) as ex:
        futs = [ex.submit(worker) for _ in range(streams)]
        for f in as_completed(futs):
            f.result()
    elapsed = time.perf_counter() - t0
    b = total["n"]
    mbps = (b * 8) / 1e6 / max(elapsed, 1e-9)
    return b, mbps, elapsed
