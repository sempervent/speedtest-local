import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import {
  fetchAnomalies,
  fetchAnomalySummary,
  fetchClients,
  fetchStatsSummary,
  fetchTimeseries,
} from "../runtime/api";

function ma3(xs: (number | null)[]): (number | null)[] {
  const out: (number | null)[] = [];
  for (let i = 0; i < xs.length; i++) {
    const a = xs[i - 1] ?? null;
    const b = xs[i] ?? null;
    const c = xs[i + 1] ?? null;
    const vals = [a, b, c].filter((v): v is number => v !== null && !Number.isNaN(v));
    out.push(vals.length ? vals.reduce((x, y) => x + y, 0) / vals.length : null);
  }
  return out;
}

export function AnalyticsPage() {
  const [bucket, setBucket] = useState<"hour" | "day" | "week" | "month">("day");
  const [clientId, setClientId] = useState("");
  const [clients, setClients] = useState<{ id: number; label: string | null }[]>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof fetchStatsSummary>> | null>(null);
  const [series, setSeries] = useState<Awaited<ReturnType<typeof fetchTimeseries>> | null>(null);
  const [anomSum, setAnomSum] = useState<Awaited<ReturnType<typeof fetchAnomalySummary>> | null>(null);
  const [anomRows, setAnomRows] = useState<Awaited<ReturnType<typeof fetchAnomalies>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const c = await fetchClients();
        setClients(c.items.map((x) => ({ id: x.id, label: x.label })));
      } catch {
        /* ignore */
      }
    })();
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const sp = new URLSearchParams();
        if (clientId) sp.set("client_id", clientId);
        const s = await fetchStatsSummary(sp);
        const tp = new URLSearchParams(sp);
        tp.set("bucket", bucket);
        const t = await fetchTimeseries(tp);
        const as = await fetchAnomalySummary(14);
        const ap = new URLSearchParams();
        if (clientId) ap.set("client_id", clientId);
        ap.set("page_size", "30");
        const ar = await fetchAnomalies(ap);
        if (cancelled) return;
        setSummary(s);
        setSeries(t);
        setAnomSum(as);
        setAnomRows(ar);
        setError(null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [bucket, clientId]);

  const chartData = useMemo(() => {
    if (!series) return [];
    const dl = series.points.map((p) => p.download_mbps_avg);
    const ul = series.points.map((p) => p.upload_mbps_avg);
    const dlMa = ma3(dl);
    const ulMa = ma3(ul);
    return series.points.map((p, i) => ({
      t: new Date(p.bucket_start).toLocaleString(),
      download: p.download_mbps_avg,
      upload: p.upload_mbps_avg,
      latency: p.latency_ms_avg,
      jitter: p.jitter_ms_avg,
      download_ma: dlMa[i],
      upload_ma: ulMa[i],
      runs: p.run_count,
    }));
  }, [series]);

  const scatterMarks = useMemo(() => {
    if (!series?.points.length || !anomRows?.items.length) return [];
    const pts = series.points.map((p) => ({
      t: new Date(p.bucket_start).toLocaleString(),
      download: p.download_mbps_avg,
    }));
    const out: { t: string; download: number | null }[] = [];
    for (const a of anomRows.items) {
      if (a.metric_name !== "download_mbps") continue;
      const runDate = new Date(a.created_at).toLocaleString();
      const hit = pts.find((p) => p.t === runDate);
      if (hit && hit.download != null) {
        out.push({ t: hit.t, download: hit.download });
      }
    }
    return out;
  }, [series, anomRows]);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-white">Analytics</h2>
        <p className="text-sm text-slate-400">
          Aggregated from PostgreSQL. Regressions compare each successful run to the mean of prior runs
          (per client when available).
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <label className="text-sm text-slate-400">
          Bucket
          <select
            className="ml-2 rounded-lg border border-ink-700 bg-ink-950 px-2 py-2 text-white"
            value={bucket}
            onChange={(e) => setBucket(e.target.value as typeof bucket)}
          >
            <option value="hour">Hour</option>
            <option value="day">Day</option>
            <option value="week">Week</option>
            <option value="month">Month</option>
          </select>
        </label>
        <label className="text-sm text-slate-400">
          Client
          <select
            className="ml-2 rounded-lg border border-ink-700 bg-ink-950 px-2 py-2 text-white"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
          >
            <option value="">All clients</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} {c.label || ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading ? <p className="text-sm text-slate-500">Loading analytics…</p> : null}
      {error ? <p className="text-sm text-amber-300">{error}</p> : null}

      {!loading && !error && summary && summary.count === 0 ? (
        <p className="rounded-xl border border-ink-700 bg-ink-900/40 px-4 py-6 text-center text-slate-400">
          No runs match the current filters. Run a test from the home page or widen the client filter.
        </p>
      ) : null}

      {anomSum ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-500/5 p-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-rose-200/90">
            Regression signals (14d)
          </h3>
          <p className="mt-1 font-mono text-2xl text-white">{anomSum.total_recent}</p>
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-400">
            <span>By metric: {JSON.stringify(anomSum.by_metric)}</span>
            <span>By severity: {JSON.stringify(anomSum.by_severity)}</span>
          </div>
        </div>
      ) : null}

      {summary && summary.count > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-ink-700 bg-ink-900/50 p-4">
            <p className="text-xs uppercase text-slate-500">Runs (filtered)</p>
            <p className="mt-1 font-mono text-2xl text-white">{summary.count}</p>
          </div>
          <div className="rounded-xl border border-ink-700 bg-ink-900/50 p-4">
            <p className="text-xs uppercase text-slate-500">↓ p50 / p95 Mbps</p>
            <p className="mt-1 font-mono text-lg text-white">
              {(summary.download_mbps_p50 ?? 0).toFixed(1)} / {(summary.download_mbps_p95 ?? 0).toFixed(1)}
            </p>
          </div>
          <div className="rounded-xl border border-ink-700 bg-ink-900/50 p-4">
            <p className="text-xs uppercase text-slate-500">↑ p50 / p95 Mbps</p>
            <p className="mt-1 font-mono text-lg text-white">
              {(summary.upload_mbps_p50 ?? 0).toFixed(1)} / {(summary.upload_mbps_p95 ?? 0).toFixed(1)}
            </p>
          </div>
          <div className="rounded-xl border border-ink-700 bg-ink-900/50 p-4">
            <p className="text-xs uppercase text-slate-500">Avg latency / jitter</p>
            <p className="mt-1 font-mono text-lg text-white">
              {(summary.latency_ms_avg ?? 0).toFixed(2)} ms / {(summary.jitter_ms_avg ?? 0).toFixed(2)} ms
            </p>
          </div>
        </div>
      ) : null}

      {chartData.length > 0 ? (
        <div className="h-80 w-full rounded-2xl border border-ink-700 bg-ink-900/40 p-2">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="t" tick={{ fill: "#94a3b8", fontSize: 10 }} />
              <YAxis yAxisId="left" tick={{ fill: "#94a3b8", fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fill: "#94a3b8", fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: "#0c1220", border: "1px solid #1b2740" }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="download" name="↓ Mbps" stroke="#5eead4" dot={false} />
              <Line yAxisId="left" type="monotone" dataKey="upload" name="↑ Mbps" stroke="#38bdf8" dot={false} />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="download_ma"
                name="↓ MA(3)"
                stroke="#99f6e4"
                strokeDasharray="4 4"
                dot={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="upload_ma"
                name="↑ MA(3)"
                stroke="#7dd3fc"
                strokeDasharray="4 4"
                dot={false}
              />
              <Line yAxisId="right" type="monotone" dataKey="latency" name="Latency ms" stroke="#fbbf24" dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="jitter" name="Jitter ms" stroke="#fb7185" dot={false} />
              {scatterMarks.length > 0 ? (
                <Scatter
                  yAxisId="left"
                  name="Download regression"
                  data={scatterMarks}
                  fill="#fb7185"
                  shape="cross"
                />
              ) : null}
              {scatterMarks.length > 0 ? <ZAxis range={[40, 40]} /> : null}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ) : null}

      {anomRows && anomRows.items.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-lg font-medium text-white">Recent anomalies</h3>
          <div className="overflow-x-auto rounded-xl border border-ink-700">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-ink-900/80 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Run</th>
                  <th className="px-3 py-2">Metric</th>
                  <th className="px-3 py-2">Baseline</th>
                  <th className="px-3 py-2">Observed</th>
                  <th className="px-3 py-2">Δ%</th>
                  <th className="px-3 py-2">Severity</th>
                </tr>
              </thead>
              <tbody>
                {anomRows.items.map((a) => (
                  <tr key={a.id} className="border-t border-ink-800">
                    <td className="px-3 py-2 font-mono text-xs text-slate-400">
                      {new Date(a.created_at).toLocaleString()}
                    </td>
                    <td className="px-3 py-2">
                      <Link className="text-accent underline" to={`/tests/${a.test_run_id}`}>
                        #{a.test_run_id}
                      </Link>
                    </td>
                    <td className="px-3 py-2">{a.metric_name}</td>
                    <td className="px-3 py-2 font-mono">{a.baseline_value?.toFixed(2) ?? "—"}</td>
                    <td className="px-3 py-2 font-mono">{a.observed_value?.toFixed(2) ?? "—"}</td>
                    <td className="px-3 py-2 font-mono">{a.deviation_pct?.toFixed(1) ?? "—"}</td>
                    <td className="px-3 py-2">{a.severity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}
