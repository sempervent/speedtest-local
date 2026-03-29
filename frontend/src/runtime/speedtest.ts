import { apiBase } from "./apiBase";
import { mean, stddev, successiveJitterMs } from "./stats";
import { randomUUID } from "./uuid";

/** Spec / Firefox cap: getRandomValues may reject more than 65536 bytes per call. */
function fillRandomBytes(buf: Uint8Array): void {
  const c = globalThis.crypto;
  if (!c?.getRandomValues) {
    for (let i = 0; i < buf.length; i++) buf[i] = Math.floor(Math.random() * 256);
    return;
  }
  const max = 65536;
  for (let off = 0; off < buf.length; off += max) {
    c.getRandomValues(buf.subarray(off, off + Math.min(max, buf.length - off)));
  }
}

export type SpeedPhase = "idle" | "warmup" | "ping" | "download" | "upload" | "done" | "error";

export interface SpeedtestProgress {
  phase: SpeedPhase;
  pingMs?: number;
  jitterMs?: number;
  downloadMbps?: number;
  uploadMbps?: number;
  message?: string;
}

export interface SpeedtestParams {
  downloadDurationSec: number;
  uploadDurationSec: number;
  parallelStreams: number;
  payloadBytes: number;
  pingSamples: number;
  warmupPingSamples: number;
  onProgress: (p: SpeedtestProgress) => void;
  signal?: AbortSignal;
}

export interface SpeedtestResult {
  latency_ms_avg: number;
  jitter_ms: number;
  latency_ms_min: number;
  latency_ms_max: number;
  latency_ms_stddev: number;
  download_mbps: number;
  upload_mbps: number;
  download_bytes_total: number;
  upload_bytes_total: number;
  duration_seconds: number;
  ping_rtts_ms: number[];
  samples: Array<{
    phase: "ping" | "download" | "upload";
    t_offset_ms: number;
    value: number;
    unit: string;
    metadata?: Record<string, unknown>;
  }>;
  raw: Record<string, unknown>;
}

function cb(): string {
  return randomUUID();
}

async function pingOnce(base: string, signal?: AbortSignal): Promise<number> {
  const t0 = performance.now();
  const res = await fetch(`${base}/api/ping?_cb=${cb()}`, {
    method: "GET",
    cache: "no-store",
    signal,
    headers: { "Cache-Control": "no-cache", Pragma: "no-cache" },
  });
  if (!res.ok) throw new Error(`ping failed: ${res.status}`);
  await res.json();
  return performance.now() - t0;
}

async function downloadOnce(bytes: number, base: string, signal?: AbortSignal): Promise<number> {
  const res = await fetch(`${base}/api/download?bytes=${bytes}&_cb=${cb()}`, {
    method: "GET",
    cache: "no-store",
    signal,
    headers: { "Cache-Control": "no-cache", Pragma: "no-cache" },
  });
  if (!res.ok) throw new Error(`download failed: ${res.status}`);
  const reader = res.body?.getReader();
  if (!reader) throw new Error("no response body");
  let n = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    n += value.byteLength;
  }
  return n;
}

async function uploadOnce(buf: ArrayBuffer, base: string, signal?: AbortSignal): Promise<number> {
  const res = await fetch(`${base}/api/upload?_cb=${cb()}`, {
    method: "POST",
    body: buf,
    cache: "no-store",
    signal,
    headers: {
      "Content-Type": "application/octet-stream",
      "Cache-Control": "no-cache",
      Pragma: "no-cache",
    },
  });
  if (!res.ok) throw new Error(`upload failed: ${res.status}`);
  const j = (await res.json()) as { bytes_received: number };
  return j.bytes_received;
}

export async function runSpeedtest(params: SpeedtestParams): Promise<SpeedtestResult> {
  const base = apiBase();
  const { signal } = params;
  const tStart = performance.now();
  const raw: Record<string, unknown> = {
    parallel_streams: params.parallelStreams,
    payload_bytes: params.payloadBytes,
  };

  params.onProgress({ phase: "warmup", message: "Warming up…" });
  for (let i = 0; i < params.warmupPingSamples; i++) {
    await pingOnce(base, signal);
  }

  params.onProgress({ phase: "ping", message: "Measuring latency…" });
  const pingRtts: number[] = [];
  const pingT0 = performance.now();
  for (let i = 0; i < params.pingSamples; i++) {
    const rtt = await pingOnce(base, signal);
    pingRtts.push(rtt);
    params.onProgress({
      phase: "ping",
      pingMs: mean(pingRtts),
      jitterMs: successiveJitterMs(pingRtts),
    });
  }
  const latency_avg = mean(pingRtts);
  const jitter = successiveJitterMs(pingRtts);
  const latency_min = Math.min(...pingRtts);
  const latency_max = Math.max(...pingRtts);
  const latency_std = stddev(pingRtts);

  const samples: SpeedtestResult["samples"] = pingRtts.map((v, idx) => ({
    phase: "ping",
    t_offset_ms: performance.now() - pingT0,
    value: v,
    unit: "ms",
    metadata: { index: idx },
  }));

  params.onProgress({ phase: "download", message: "Measuring download…" });
  const dlStart = performance.now();
  const dlWallSec = params.downloadDurationSec;
  const dlEnd = dlStart + dlWallSec * 1000;
  const warmupDlEnd = dlStart + Math.min(500, dlWallSec * 1000 * 0.1);
  const streams = Math.max(1, Math.floor(params.parallelStreams));
  const chunk = Math.min(
    Math.max(256 * 1024, params.payloadBytes),
    32 * 1024 * 1024,
  );
  const aggDl = { bytes: 0 };

  async function downloadWorker(): Promise<number> {
    let bytes = 0;
    while (performance.now() < dlEnd) {
      if (performance.now() < warmupDlEnd) {
        await downloadOnce(Math.min(chunk, 2 * 1024 * 1024), base, signal);
        continue;
      }
      const got = await downloadOnce(chunk, base, signal);
      bytes += got;
      aggDl.bytes += got;
      const elapsed = (performance.now() - dlStart) / 1000;
      const inst = (aggDl.bytes * 8) / 1e6 / Math.max(elapsed, 1e-6);
      params.onProgress({ phase: "download", downloadMbps: inst });
    }
    return bytes;
  }
  const dlParts = await Promise.all(Array.from({ length: streams }, () => downloadWorker()));
  const download_bytes_total = dlParts.reduce((a, b) => a + b, 0);
  const dlElapsed = (performance.now() - dlStart) / 1000;
  const download_mbps = (download_bytes_total * 8) / 1e6 / Math.max(dlElapsed, 1e-6);
  params.onProgress({ phase: "download", downloadMbps: download_mbps });
  samples.push({
    phase: "download",
    t_offset_ms: performance.now() - tStart,
    value: download_mbps,
    unit: "Mbps",
    metadata: { aggregate: true },
  });

  params.onProgress({ phase: "upload", message: "Measuring upload…" });
  const ulStart = performance.now();
  const ulWallSec = params.uploadDurationSec;
  const ulEnd = ulStart + ulWallSec * 1000;
  const warmupUlEnd = ulStart + Math.min(500, ulWallSec * 1000 * 0.1);
  const ulChunk = Math.min(Math.max(256 * 1024, Math.floor(params.payloadBytes / 4)), 8 * 1024 * 1024);
  const ulBuf = new Uint8Array(ulChunk);
  fillRandomBytes(ulBuf);
  const ulAb = ulBuf.buffer.slice(0);
  const aggUl = { bytes: 0 };

  async function uploadWorker(): Promise<number> {
    let bytes = 0;
    while (performance.now() < ulEnd) {
      if (performance.now() < warmupUlEnd) {
        await uploadOnce(ulAb.slice(0, Math.min(ulChunk, 512 * 1024)), base, signal);
        continue;
      }
      const got = await uploadOnce(ulAb, base, signal);
      bytes += got;
      aggUl.bytes += got;
      const elapsed = (performance.now() - ulStart) / 1000;
      const inst = (aggUl.bytes * 8) / 1e6 / Math.max(elapsed, 1e-6);
      params.onProgress({ phase: "upload", uploadMbps: inst });
    }
    return bytes;
  }
  const ulParts = await Promise.all(Array.from({ length: streams }, () => uploadWorker()));
  const upload_bytes_total = ulParts.reduce((a, b) => a + b, 0);
  const ulElapsed = (performance.now() - ulStart) / 1000;
  const upload_mbps = (upload_bytes_total * 8) / 1e6 / Math.max(ulElapsed, 1e-6);
  params.onProgress({ phase: "upload", uploadMbps: upload_mbps });
  samples.push({
    phase: "upload",
    t_offset_ms: performance.now() - tStart,
    value: upload_mbps,
    unit: "Mbps",
    metadata: { aggregate: true },
  });

  const duration_seconds = (performance.now() - tStart) / 1000;
  raw["ping"] = {
    samples: pingRtts.length,
    min_ms: latency_min,
    max_ms: latency_max,
    stddev_ms: latency_std,
  };
  raw["download"] = { bytes: download_bytes_total, wall_seconds: dlElapsed };
  raw["upload"] = { bytes: upload_bytes_total, wall_seconds: ulElapsed };

  params.onProgress({ phase: "done" });
  return {
    latency_ms_avg: latency_avg,
    jitter_ms: jitter,
    latency_ms_min: latency_min,
    latency_ms_max: latency_max,
    latency_ms_stddev: latency_std,
    download_mbps,
    upload_mbps,
    download_bytes_total,
    upload_bytes_total,
    duration_seconds,
    ping_rtts_ms: pingRtts,
    samples,
    raw,
  };
}
