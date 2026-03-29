import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchConfig, postTest, type AppConfig } from "../lib/api";
import { getOrCreateClientStableId } from "../lib/clientId";
import { runSpeedtest, type SpeedtestProgress } from "../lib/speedtest";

function formatMbps(v: number | undefined): string {
  if (v === undefined || Number.isNaN(v)) return "—";
  if (v >= 1000) return (v / 1000).toFixed(2);
  return v.toFixed(1);
}

function formatMs(v: number | undefined): string {
  if (v === undefined || Number.isNaN(v)) return "—";
  return v.toFixed(2);
}

export function RunTestPage() {
  const [cfgLoading, setCfgLoading] = useState(true);
  const [cfgError, setCfgError] = useState<string | null>(null);
  const [pubCfg, setPubCfg] = useState<AppConfig | null>(null);
  const [downloadSec, setDownloadSec] = useState(10);
  const [uploadSec, setUploadSec] = useState(10);
  const [streams, setStreams] = useState(4);
  const [payloadBytes, setPayloadBytes] = useState(16 * 1024 * 1024);
  const [clientLabel, setClientLabel] = useState("");
  const [networkLabel, setNetworkLabel] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<SpeedtestProgress>({ phase: "idle" });
  const [summary, setSummary] = useState<string | null>(null);
  const [lastId, setLastId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await fetchConfig();
        if (cancelled) return;
        setPubCfg(c);
        setDownloadSec(c.defaults.download_duration_sec);
        setUploadSec(c.defaults.upload_duration_sec);
        setStreams(c.defaults.parallel_streams);
        setPayloadBytes(c.defaults.payload_bytes);
        setCfgError(null);
      } catch (e) {
        if (!cancelled) setCfgError(e instanceof Error ? e.message : "config failed");
      } finally {
        if (!cancelled) setCfgLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onProgress = useCallback((p: SpeedtestProgress) => setProgress(p), []);

  const start = async () => {
    setSummary(null);
    setLastId(null);
    setRunning(true);
    setProgress({ phase: "warmup", message: "Starting…" });
    try {
      const c = await fetchConfig();
      const res = await runSpeedtest({
        downloadDurationSec: downloadSec,
        uploadDurationSec: uploadSec,
        parallelStreams: streams,
        payloadBytes,
        pingSamples: c.defaults.ping_samples,
        warmupPingSamples: c.defaults.warmup_ping_samples,
        onProgress,
      });
      const stable = getOrCreateClientStableId();
      const saved = await postTest({
        started_at: new Date(Date.now() - res.duration_seconds * 1000).toISOString(),
        completed_at: new Date().toISOString(),
        client_stable_id: stable,
        client_label: c.allow_client_self_label ? clientLabel || null : null,
        network_label: c.allow_network_label ? networkLabel || null : null,
        server_label: c.server_label,
        latency_ms_avg: res.latency_ms_avg,
        jitter_ms: res.jitter_ms,
        download_mbps: res.download_mbps,
        upload_mbps: res.upload_mbps,
        packet_loss_pct: null,
        download_bytes_total: res.download_bytes_total,
        upload_bytes_total: res.upload_bytes_total,
        duration_seconds: res.duration_seconds,
        success: true,
        raw_metrics_json: {
          ...res.raw,
          ping_rtts_ms: res.ping_rtts_ms,
        },
        browser_user_agent: navigator.userAgent,
        samples: res.samples,
      });
      setLastId(saved.id);
      setSummary(
        `Saved run #${saved.id}: ↓ ${formatMbps(res.download_mbps)} Mbps · ↑ ${formatMbps(res.upload_mbps)} Mbps · ping ${formatMs(res.latency_ms_avg)} ms`,
      );
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Test failed";
      setProgress({ phase: "error", message: msg });
      try {
        const c = await fetchConfig();
        const stable = getOrCreateClientStableId();
        const saved = await postTest({
          success: false,
          failure_reason: msg,
          client_stable_id: stable,
          client_label: c.allow_client_self_label ? clientLabel || null : null,
          network_label: c.allow_network_label ? networkLabel || null : null,
          server_label: c.server_label,
          browser_user_agent: navigator.userAgent,
          raw_metrics_json: { error: msg },
        });
        setLastId(saved.id);
      } catch {
        /* ignore secondary failure */
      }
    } finally {
      setRunning(false);
    }
  };

  const phaseLabel = useMemo(() => {
    switch (progress.phase) {
      case "warmup":
        return "Warmup";
      case "ping":
        return "Latency";
      case "download":
        return "Download";
      case "upload":
        return "Upload";
      case "done":
        return "Complete";
      case "error":
        return "Error";
      default:
        return "Idle";
    }
  }, [progress.phase]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Run test</h2>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Measures against this server on your LAN. Uses parallel streams, warmup, and cache-busting.
          </p>
        </div>
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-xl bg-accent px-8 py-4 text-lg font-semibold text-ink-950 shadow-lg shadow-accent/20 transition hover:bg-accent-dim focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-40"
          onClick={() => void start()}
          disabled={running || cfgLoading}
          aria-busy={running}
        >
          {running ? "Running…" : "Start"}
        </button>
      </div>

      {cfgError ? (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          <p>Could not load config ({cfgError}). Is the API reachable?</p>
          <button
            type="button"
            className="mt-2 text-xs text-accent underline"
            onClick={() => {
              setCfgLoading(true);
              setCfgError(null);
              void fetchConfig()
                .then((c) => {
                  setPubCfg(c);
                  setDownloadSec(c.defaults.download_duration_sec);
                  setUploadSec(c.defaults.upload_duration_sec);
                  setStreams(c.defaults.parallel_streams);
                  setPayloadBytes(c.defaults.payload_bytes);
                  setCfgError(null);
                })
                .catch((e) =>
                  setCfgError(e instanceof Error ? e.message : "config failed"),
                )
                .finally(() => setCfgLoading(false));
            }}
          >
            Retry
          </button>
        </div>
      ) : null}

      <div className="rounded-2xl border border-ink-700 bg-ink-900/40 p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Phase</p>
            <p className="text-lg font-medium text-white">{phaseLabel}</p>
            {running ? (
              <p className="text-xs text-slate-500">This can take a while on Wi‑Fi; do not close the tab.</p>
            ) : null}
            {progress.message ? <p className="text-sm text-slate-400">{progress.message}</p> : null}
          </div>
          <div
            className="h-14 w-14 rounded-full border-2 border-accent/40 border-t-accent animate-spin"
            style={{ animationDuration: running ? "0.9s" : "0s", opacity: running ? 1 : 0.2 }}
            aria-hidden
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-ink-700 bg-ink-900/50 p-4">
          <p className="text-xs uppercase text-slate-500">Ping avg</p>
          <p className="mt-2 font-mono text-3xl text-white">{formatMs(progress.pingMs)} ms</p>
        </div>
        <div className="rounded-2xl border border-ink-700 bg-ink-900/50 p-4">
          <p className="text-xs uppercase text-slate-500">Jitter</p>
          <p className="mt-2 font-mono text-3xl text-white">{formatMs(progress.jitterMs)} ms</p>
        </div>
        <div className="rounded-2xl border border-ink-700 bg-ink-900/50 p-4">
          <p className="text-xs uppercase text-slate-500">Download</p>
          <p className="mt-2 font-mono text-3xl text-white">
            {formatMbps(progress.downloadMbps)} <span className="text-accent text-lg">Mbps</span>
          </p>
        </div>
        <div className="rounded-2xl border border-ink-700 bg-ink-900/50 p-4">
          <p className="text-xs uppercase text-slate-500">Upload</p>
          <p className="mt-2 font-mono text-3xl text-white">
            {formatMbps(progress.uploadMbps)} <span className="text-accent text-lg">Mbps</span>
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-ink-700 bg-ink-900/30">
        <button
          type="button"
          className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-slate-200"
          aria-expanded={advancedOpen}
          onClick={() => setAdvancedOpen((v) => !v)}
        >
          Advanced options
          <span className="text-slate-500">{advancedOpen ? "▾" : "▸"}</span>
        </button>
        {advancedOpen ? (
          <div className="grid gap-4 border-t border-ink-800 px-4 py-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-slate-400">Download duration (s)</span>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
                value={downloadSec}
                min={2}
                max={120}
                onChange={(e) => setDownloadSec(Number(e.target.value))}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Upload duration (s)</span>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
                value={uploadSec}
                min={2}
                max={120}
                onChange={(e) => setUploadSec(Number(e.target.value))}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Parallel streams</span>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
                value={streams}
                min={1}
                max={16}
                onChange={(e) => setStreams(Number(e.target.value))}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-400">Payload size (bytes)</span>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
                value={payloadBytes}
                min={262144}
                step={1048576}
                onChange={(e) => setPayloadBytes(Number(e.target.value))}
              />
            </label>
            {pubCfg?.allow_client_self_label ? (
              <label className="block text-sm sm:col-span-2">
                <span className="text-slate-400">Client label</span>
                <input
                  type="text"
                  className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 text-white"
                  value={clientLabel}
                  onChange={(e) => setClientLabel(e.target.value)}
                  placeholder="e.g. office laptop"
                />
              </label>
            ) : (
              <p className="text-xs text-slate-500 sm:col-span-2">
                Client labels are disabled by the server administrator.
              </p>
            )}
            {pubCfg?.allow_network_label ? (
              <label className="block text-sm sm:col-span-2">
                <span className="text-slate-400">Network label (SSID / VLAN)</span>
                <input
                  type="text"
                  className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 text-white"
                  value={networkLabel}
                  onChange={(e) => setNetworkLabel(e.target.value)}
                  placeholder="e.g. IoT-SSID / eth-living-room"
                />
              </label>
            ) : (
              <p className="text-xs text-slate-500 sm:col-span-2">
                Network labels are disabled by the server administrator.
              </p>
            )}
          </div>
        ) : null}
      </div>

      {summary ? (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
          <p>{summary}</p>
          {lastId ? (
            <Link className="mt-2 inline-block text-accent underline" to={`/tests/${lastId}`}>
              Open run detail
            </Link>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
