import { useCallback, useEffect, useState } from "react";
import {
  exportTestsNewPath,
  exportUrl,
  fetchAdminSettings,
  patchAdminSettings,
  type AdminSettings,
} from "../runtime/api";

export function SettingsPage() {
  const [s, setS] = useState<AdminSettings | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "ok" | "err">("idle");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [formKey, setFormKey] = useState(0);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const x = await fetchAdminSettings();
      setS(x);
      setFormKey((k) => k + 1);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "failed to load settings");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loadError && !s) {
    return (
      <div className="space-y-4">
        <p className="text-amber-300">{loadError}</p>
        <button
          type="button"
          className="rounded-lg border border-ink-700 px-4 py-2 text-sm text-accent"
          onClick={() => void load()}
        >
          Retry
        </button>
      </div>
    );
  }
  if (!s) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-white">Settings</h2>
        <p className="text-sm text-slate-400">
          Values are stored in PostgreSQL (<code className="text-accent">app_settings</code>) and are the
          source of truth for defaults and policy flags after the first startup.
        </p>
      </div>

      <form
        key={formKey}
        className="grid max-w-2xl gap-4 rounded-2xl border border-ink-700 bg-ink-900/40 p-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setSaveState("saving");
          setSaveMessage(null);
          const fd = new FormData(e.currentTarget);
          const retentionRaw = String(fd.get("retention_days") ?? "").trim();
          const patch: Record<string, unknown> = {
            server_label: String(fd.get("server_label") || s.server_label),
            default_download_duration_sec: Number(fd.get("dd")),
            default_upload_duration_sec: Number(fd.get("ud")),
            default_parallel_streams: Number(fd.get("ps")),
            default_payload_bytes: Number(fd.get("pb")),
            default_ping_samples: Number(fd.get("pp")),
            default_warmup_ping_samples: Number(fd.get("pw")),
            retention_days: retentionRaw === "" ? null : Number(retentionRaw),
            allow_client_self_label: fd.get("allow_client") === "on",
            allow_network_label: fd.get("allow_network") === "on",
            anomaly_baseline_runs: Number(fd.get("abr")),
            anomaly_deviation_percent: Number(fd.get("adp")),
          };
          try {
            const next = await patchAdminSettings(patch);
            setS(next);
            setSaveState("ok");
            setSaveMessage("Saved successfully.");
          } catch (err) {
            setSaveState("err");
            setSaveMessage(err instanceof Error ? err.message : "Save failed");
          }
        }}
      >
        <label className="text-sm">
          <span className="text-slate-500">Server label</span>
          <input
            name="server_label"
            required
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 text-white"
            defaultValue={s.server_label}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Default download duration (s)</span>
          <input
            name="dd"
            type="number"
            required
            min={2}
            max={600}
            step={0.5}
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
            defaultValue={s.default_download_duration_sec}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Default upload duration (s)</span>
          <input
            name="ud"
            type="number"
            required
            min={2}
            max={600}
            step={0.5}
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
            defaultValue={s.default_upload_duration_sec}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Parallel streams</span>
          <input
            name="ps"
            type="number"
            required
            min={1}
            max={32}
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
            defaultValue={s.default_parallel_streams}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Payload bytes (hint)</span>
          <input
            name="pb"
            type="number"
            required
            min={262144}
            step={1048576}
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
            defaultValue={s.default_payload_bytes}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Ping samples</span>
          <input
            name="pp"
            type="number"
            required
            min={5}
            max={500}
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
            defaultValue={s.default_ping_samples}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Warmup ping samples</span>
          <input
            name="pw"
            type="number"
            required
            min={0}
            max={100}
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
            defaultValue={s.default_warmup_ping_samples}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-500">Retention (days, empty = not set)</span>
          <input
            name="retention_days"
            type="number"
            min={1}
            max={3650}
            placeholder="e.g. 365 — leave empty to disable policy hint"
            className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
            defaultValue={s.retention_days ?? ""}
          />
        </label>
        <div className="flex flex-col gap-2 text-sm">
          <label className="flex items-center gap-2 text-slate-300">
            <input
              type="checkbox"
              name="allow_client"
              defaultChecked={s.allow_client_self_label}
              className="rounded border-ink-600"
            />
            Allow client self-label on runs
          </label>
          <label className="flex items-center gap-2 text-slate-300">
            <input
              type="checkbox"
              name="allow_network"
              defaultChecked={s.allow_network_label}
              className="rounded border-ink-600"
            />
            Allow network / SSID label on runs
          </label>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm">
            <span className="text-slate-500">Anomaly baseline runs</span>
            <input
              name="abr"
              type="number"
              required
              min={3}
              max={500}
              className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
              defaultValue={s.anomaly_baseline_runs}
            />
          </label>
          <label className="text-sm">
            <span className="text-slate-500">Anomaly deviation (%)</span>
            <input
              name="adp"
              type="number"
              required
              min={1}
              max={200}
              step={0.5}
              className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 font-mono text-white"
              defaultValue={s.anomaly_deviation_percent}
            />
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={saveState === "saving"}
            className="rounded-lg bg-accent px-4 py-2 font-semibold text-ink-950 hover:bg-accent-dim disabled:opacity-50"
          >
            {saveState === "saving" ? "Saving…" : "Save"}
          </button>
          {saveMessage ? (
            <span
              className={
                saveState === "ok" ? "text-sm text-emerald-400" : "text-sm text-amber-300"
              }
              role="status"
            >
              {saveMessage}
            </span>
          ) : null}
        </div>
      </form>

      <div className="space-y-2">
        <h3 className="text-lg font-medium text-white">Export</h3>
        <p className="text-sm text-slate-500">
          Filtered exports (same query params as history). New canonical paths under{" "}
          <code className="text-accent">/api/export/</code>.
        </p>
        <div className="flex flex-wrap gap-2">
          <a
            className="rounded-lg border border-ink-700 px-4 py-2 text-sm text-accent"
            href={exportTestsNewPath("csv", new URLSearchParams())}
          >
            CSV (export API)
          </a>
          <a
            className="rounded-lg border border-ink-700 px-4 py-2 text-sm text-accent"
            href={exportTestsNewPath("json", new URLSearchParams())}
          >
            JSON (export API)
          </a>
          <a
            className="rounded-lg border border-ink-700 px-4 py-2 text-xs text-slate-400"
            href={exportUrl("csv", new URLSearchParams())}
          >
            Legacy CSV
          </a>
        </div>
      </div>
    </div>
  );
}
