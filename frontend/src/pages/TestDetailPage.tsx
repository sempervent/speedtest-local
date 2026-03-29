import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchTest, type TestRunDetail } from "@/lib/api";

export function TestDetailPage() {
  const { id } = useParams();
  const [run, setRun] = useState<TestRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await fetchTest(Number(id));
        if (!cancelled) {
          setRun(r);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const pingSeries = useMemo(() => {
    if (!run) return [];
    return run.samples
      .filter((s) => s.phase === "ping")
      .map((s) => ({ x: s.t_offset_ms, ms: s.value }));
  }, [run]);

  const copyJson = async () => {
    if (!run) return;
    await navigator.clipboard.writeText(JSON.stringify(run, null, 2));
  };

  if (error) return <p className="text-amber-300">{error}</p>;
  if (!run) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Run #{run.id}</h2>
          <p className="text-sm text-slate-400">{new Date(run.created_at).toLocaleString()}</p>
        </div>
        <button
          type="button"
          className="rounded-lg border border-ink-700 px-4 py-2 text-sm text-slate-200 hover:bg-ink-800"
          onClick={() => void copyJson()}
        >
          Copy JSON
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Download" value={run.download_mbps} suffix="Mbps" />
        <Metric label="Upload" value={run.upload_mbps} suffix="Mbps" />
        <Metric label="Latency" value={run.latency_ms_avg} suffix="ms" />
        <Metric label="Jitter" value={run.jitter_ms} suffix="ms" />
      </div>

      <div className="rounded-2xl border border-ink-700 bg-ink-900/40 p-4 text-sm text-slate-300">
        <p>
          <span className="text-slate-500">Client:</span> {run.client_label || run.client_id || "—"}
        </p>
        <p>
          <span className="text-slate-500">Network:</span> {run.network_label || "—"}
        </p>
        <p>
          <span className="text-slate-500">Server:</span> {run.server_label}
        </p>
        <p>
          <span className="text-slate-500">Success:</span> {run.success ? "yes" : "no"}
          {run.failure_reason ? ` — ${run.failure_reason}` : ""}
        </p>
        <p className="mt-2 break-all text-xs text-slate-500">{run.browser_user_agent}</p>
      </div>

      {pingSeries.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-lg font-medium text-white">Ping samples</h3>
          <div className="h-64 rounded-2xl border border-ink-700 bg-ink-900/40 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={pingSeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="x" name="t ms" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: "#0c1220", border: "1px solid #1b2740" }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Legend />
                <Line type="monotone" dataKey="ms" name="RTT ms" stroke="#5eead4" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : null}

      <div className="space-y-2">
        <h3 className="text-lg font-medium text-white">Raw metrics</h3>
        <pre className="max-h-96 overflow-auto rounded-xl border border-ink-800 bg-ink-950 p-4 font-mono text-xs text-slate-300">
          {JSON.stringify(run.raw_metrics_json ?? {}, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  suffix,
}: {
  label: string;
  value: number | null | undefined;
  suffix: string;
}) {
  const v = value === null || value === undefined ? "—" : suffix === "Mbps" ? value.toFixed(1) : value.toFixed(2);
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-900/50 p-4">
      <p className="text-xs uppercase text-slate-500">{label}</p>
      <p className="mt-1 font-mono text-2xl text-white">
        {v} <span className="text-accent text-sm">{suffix}</span>
      </p>
    </div>
  );
}
