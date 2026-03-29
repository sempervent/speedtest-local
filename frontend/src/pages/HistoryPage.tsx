import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { exportTestsNewPath, fetchClients, fetchTests, type TestRunSummary } from "../runtime/api";

type SortKey = "created_at" | "download_mbps" | "upload_mbps" | "latency_ms_avg";

export function HistoryPage() {
  const [items, setItems] = useState<TestRunSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [clientId, setClientId] = useState<string>("");
  const [network, setNetwork] = useState("");
  const [success, setSuccess] = useState<string>("");
  const [sort, setSort] = useState<SortKey>("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [clients, setClients] = useState<{ id: number; label: string | null }[]>([]);

  useEffect(() => {
    void (async () => {
      try {
        const c = await fetchClients();
        setClients(c.items.map((x) => ({ id: x.id, label: x.label })));
      } catch {
        /* optional */
      }
    })();
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const p = new URLSearchParams();
        p.set("page", String(page));
        p.set("page_size", "50");
        if (from) p.set("from", new Date(from).toISOString());
        if (to) p.set("to", new Date(to).toISOString());
        if (clientId) p.set("client_id", clientId);
        if (network) p.set("network_label", network);
        if (success === "ok") p.set("success", "true");
        if (success === "fail") p.set("success", "false");
        p.set("sort", sort);
        p.set("order", order);
        const data = await fetchTests(p);
        if (cancelled) return;
        setItems(data.items);
        setTotal(data.total);
        setError(null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "load failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [page, from, to, clientId, network, success, sort, order]);

  const pages = useMemo(() => Math.max(1, Math.ceil(total / 50)), [total]);

  const exportParams = useMemo(() => {
    const p = new URLSearchParams();
    if (from) p.set("from", new Date(from).toISOString());
    if (to) p.set("to", new Date(to).toISOString());
    if (clientId) p.set("client_id", clientId);
    if (network) p.set("network_label", network);
    if (success === "ok") p.set("success", "true");
    if (success === "fail") p.set("success", "false");
    return p;
  }, [from, to, clientId, network, success]);

  const thBtn = (key: SortKey, label: string) => (
    <button
      type="button"
      className="flex items-center gap-1 font-medium text-slate-300 hover:text-white"
      onClick={() => {
        if (sort === key) setOrder(order === "asc" ? "desc" : "asc");
        else {
          setSort(key);
          setOrder("desc");
        }
      }}
    >
      {label}
      {sort === key ? (order === "asc" ? "↑" : "↓") : ""}
    </button>
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">History</h2>
        <p className="text-sm text-slate-400">Filter and drill into stored runs.</p>
      </div>

      <div className="grid gap-3 rounded-2xl border border-ink-700 bg-ink-900/40 p-4 sm:grid-cols-2 lg:grid-cols-3">
        <label className="text-sm">
          <span className="text-slate-500">From</span>
          <input
            type="datetime-local"
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-2 py-2 text-white"
            value={from}
            onChange={(e) => {
              setPage(1);
              setFrom(e.target.value);
            }}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">To</span>
          <input
            type="datetime-local"
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-2 py-2 text-white"
            value={to}
            onChange={(e) => {
              setPage(1);
              setTo(e.target.value);
            }}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Client</span>
          <select
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-2 py-2 text-white"
            value={clientId}
            onChange={(e) => {
              setPage(1);
              setClientId(e.target.value);
            }}
          >
            <option value="">All</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} {c.label || ""}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Network label</span>
          <input
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-2 py-2 text-white"
            value={network}
            onChange={(e) => {
              setPage(1);
              setNetwork(e.target.value);
            }}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Outcome</span>
          <select
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-2 py-2 text-white"
            value={success}
            onChange={(e) => {
              setPage(1);
              setSuccess(e.target.value);
            }}
          >
            <option value="">All</option>
            <option value="ok">Success</option>
            <option value="fail">Failure</option>
          </select>
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-slate-500">Export filtered:</span>
        <a
          className="rounded-lg border border-ink-700 px-3 py-1 text-accent"
          href={exportTestsNewPath("csv", new URLSearchParams(exportParams))}
        >
          CSV
        </a>
        <a
          className="rounded-lg border border-ink-700 px-3 py-1 text-accent"
          href={exportTestsNewPath("json", new URLSearchParams(exportParams))}
        >
          JSON
        </a>
      </div>

      {error ? <p className="text-sm text-amber-300">{error}</p> : null}

      <div className="overflow-x-auto rounded-2xl border border-ink-700">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-ink-900/80 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-3">{thBtn("created_at", "Time")}</th>
              <th className="px-3 py-3">Client</th>
              <th className="px-3 py-3">Network</th>
              <th className="px-3 py-3">Server</th>
              <th className="px-3 py-3">{thBtn("download_mbps", "↓ Mbps")}</th>
              <th className="px-3 py-3">{thBtn("upload_mbps", "↑ Mbps")}</th>
              <th className="px-3 py-3">{thBtn("latency_ms_avg", "Ping")}</th>
              <th className="px-3 py-3">OK</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-slate-500">
                  Loading…
                </td>
              </tr>
            ) : null}
            {!loading && items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-slate-500">
                  No runs match these filters.
                </td>
              </tr>
            ) : null}
            {!loading &&
              items.map((r) => (
                <tr key={r.id} className="border-t border-ink-800 hover:bg-ink-900/60">
                  <td className="px-3 py-2 font-mono text-xs text-slate-300">
                    <Link className="text-accent underline" to={`/tests/${r.id}`}>
                      {new Date(r.created_at).toLocaleString()}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-slate-200">{r.client_label || r.client_id || "—"}</td>
                  <td className="px-3 py-2 text-slate-300">{r.network_label || "—"}</td>
                  <td className="px-3 py-2 text-slate-300">{r.server_label}</td>
                  <td className="px-3 py-2 font-mono text-slate-100">
                    {r.download_mbps?.toFixed(1) ?? "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-slate-100">
                    {r.upload_mbps?.toFixed(1) ?? "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-slate-100">
                    {r.latency_ms_avg?.toFixed(2) ?? "—"}
                  </td>
                  <td className="px-3 py-2">{r.success ? "✓" : "✗"}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-slate-400">
        <span>
          Page {page} / {pages} — {total} runs
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-lg border border-ink-700 px-3 py-1 disabled:opacity-30"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Prev
          </button>
          <button
            type="button"
            className="rounded-lg border border-ink-700 px-3 py-1 disabled:opacity-30"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
