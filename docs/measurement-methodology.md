# Measurement methodology

## Goals

Quantify **local network** performance (Ethernet + Wi‑Fi) using only browser primitives, while minimizing systematic bias from caches, single-request bursts, and idle link power states.

## Latency & jitter

1. **Warmup:** discard an initial batch of ping requests so the first samples are not dominated by cold connection setup.
2. **Samples:** perform N sequential `GET /api/ping` requests. The browser measures **round-trip time (RTT)** as wall time from immediately before `fetch` starts until the response body is consumed.
3. **Summary stats:** compute average, min, max, and standard deviation across RTT samples.
4. **Jitter proxy:** compute the **mean absolute successive difference** between consecutive RTT samples. This is *not* identical to VoIP-style IPDV, but it is a reproducible, browser-observable indicator of variability.

> **Packet loss:** true packet loss is **not** estimated. HTTP runs over TCP; lost packets are retransmitted transparently. A browser cannot see MAC-layer retries or Wi‑Fi drops the way ICMP or hardware telemetry can. The API field `packet_loss_pct` exists for future instrumentation (e.g., a native agent) but is left `null` for browser-only tests.

## Download throughput

1. **Parallel streams:** spawn M concurrent async workers, each repeatedly downloading fixed-size chunks via `GET /api/download`.
2. **Warmup window:** ignore the first ~10% of the test window (bounded) so startup transients contribute less to the headline number.
3. **Payload:** server streams **cryptographically strong random bytes** (`os.urandom`) with `Cache-Control: no-store` and per-request cache-busting query parameters.
4. **Client accounting:** workers tally bytes received by draining the `ReadableStream` without retaining full payloads in memory.
5. **Mbps:** \((\text{total bytes} \times 8) / 10^6 / \text{wall seconds}\). This is **MAC/IP/TCP payload inclusive** of bytes delivered to the browser over HTTP, not a physical-layer PHY rate.

## Upload throughput

1. **Parallel streams:** M workers repeatedly `POST` fixed-size binary bodies to `/api/upload`.
2. **Warmup:** same idea as download.
3. **Payload:** random buffers generated client-side (`crypto.getRandomValues`) to avoid compressibility artifacts.
4. **Mbps:** same formula as download, using server-reported `bytes_received` per POST summed over the window.

## Interpretation guardrails

- Results are **estimates**. Browsers are not calibrated instruments.
- CPU load, power management, background tabs, and antivirus can depress numbers independently of the network.
- Wi‑Fi is time-shared; concurrent clients on the same channel will depress throughput without showing up as “loss” in HTTP metrics.
- Do not compare these numbers to ISP speedtests; different paths, protocols, and server behaviors make that meaningless.

## Stored diagnostics

Each run stores:

- headline metrics on `test_runs`
- optional `test_samples` rows (ping RTTs + aggregate throughput snapshots)
- `raw_metrics_json` with arrays and timing metadata for deep dives

This supports regression hunting without pretending spurious precision in the headline tiles.
