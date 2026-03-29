import { apiBase, apiFetch } from "./apiBase";

export interface AppConfig {
  server_label: string;
  defaults: {
    download_duration_sec: number;
    upload_duration_sec: number;
    parallel_streams: number;
    payload_bytes: number;
    ping_samples: number;
    warmup_ping_samples: number;
  };
  download_max_bytes: number;
  upload_max_bytes: number;
  allow_client_self_label: boolean;
  allow_network_label: boolean;
}

export async function fetchConfig(): Promise<AppConfig> {
  const r = await apiFetch("/api/config");
  if (!r.ok) throw new Error(`config ${r.status}`);
  return (await r.json()) as AppConfig;
}

export interface TestRunSummary {
  id: number;
  created_at: string;
  client_id: number | null;
  client_label: string | null;
  network_label: string | null;
  server_label: string;
  download_mbps: number | null;
  upload_mbps: number | null;
  latency_ms_avg: number | null;
  jitter_ms: number | null;
  success: boolean;
  duration_seconds: number | null;
}

export interface TestListResponse {
  items: TestRunSummary[];
  total: number;
  page: number;
  page_size: number;
}

export async function fetchTests(params: URLSearchParams): Promise<TestListResponse> {
  const r = await apiFetch(`/api/tests?${params.toString()}`);
  if (!r.ok) throw new Error(`tests ${r.status}`);
  return (await r.json()) as TestListResponse;
}

export interface TestSample {
  id: number;
  phase: string;
  t_offset_ms: number;
  value: number;
  unit: string;
  metadata: Record<string, unknown>;
}

export interface TestRunDetail {
  id: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  client_id: number | null;
  client_label: string | null;
  network_label: string | null;
  server_label: string;
  latency_ms_avg: number | null;
  jitter_ms: number | null;
  download_mbps: number | null;
  upload_mbps: number | null;
  packet_loss_pct: number | null;
  download_bytes_total: number | null;
  upload_bytes_total: number | null;
  duration_seconds: number | null;
  success: boolean;
  failure_reason: string | null;
  raw_metrics_json: Record<string, unknown> | null;
  browser_user_agent: string | null;
  ip_address: string | null;
  notes: string | null;
  samples: TestSample[];
}

export async function fetchTest(id: number): Promise<TestRunDetail> {
  const r = await apiFetch(`/api/tests/${id}`);
  if (!r.ok) throw new Error(`test ${r.status}`);
  return (await r.json()) as TestRunDetail;
}

export async function postTest(body: Record<string, unknown>): Promise<TestRunDetail> {
  const r = await apiFetch("/api/tests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    let msg = `save failed: ${r.status}`;
    try {
      const j = JSON.parse(t) as { detail?: unknown };
      if (typeof j.detail === "string") msg = j.detail;
      else if (Array.isArray(j.detail)) msg = JSON.stringify(j.detail);
      else if (j.detail) msg = JSON.stringify(j.detail);
    } catch {
      if (t) msg = t;
    }
    throw new Error(msg);
  }
  return (await r.json()) as TestRunDetail;
}

export interface StatsSummary {
  count: number;
  download_mbps_avg: number | null;
  download_mbps_p50: number | null;
  download_mbps_p95: number | null;
  upload_mbps_avg: number | null;
  upload_mbps_p50: number | null;
  upload_mbps_p95: number | null;
  latency_ms_avg: number | null;
  jitter_ms_avg: number | null;
}

export async function fetchStatsSummary(params: URLSearchParams): Promise<StatsSummary> {
  const r = await apiFetch(`/api/stats/summary?${params.toString()}`);
  if (!r.ok) throw new Error(`summary ${r.status}`);
  return (await r.json()) as StatsSummary;
}

export interface TimeseriesPoint {
  bucket_start: string;
  download_mbps_avg: number | null;
  upload_mbps_avg: number | null;
  latency_ms_avg: number | null;
  jitter_ms_avg: number | null;
  run_count: number;
}

export interface TimeseriesResponse {
  bucket: string;
  points: TimeseriesPoint[];
}

export async function fetchTimeseries(params: URLSearchParams): Promise<TimeseriesResponse> {
  const r = await apiFetch(`/api/stats/timeseries?${params.toString()}`);
  if (!r.ok) throw new Error(`timeseries ${r.status}`);
  return (await r.json()) as TimeseriesResponse;
}

export interface ClientRow {
  id: number;
  label: string | null;
  network_label: string | null;
  browser: string | null;
  os: string | null;
  last_seen_at: string;
}

export async function fetchClients(): Promise<{ items: ClientRow[] }> {
  const r = await apiFetch("/api/clients");
  if (!r.ok) throw new Error(`clients ${r.status}`);
  return (await r.json()) as { items: ClientRow[] };
}

export interface AdminSettings {
  server_label: string;
  default_download_duration_sec: number;
  default_upload_duration_sec: number;
  default_parallel_streams: number;
  default_payload_bytes: number;
  default_ping_samples: number;
  default_warmup_ping_samples: number;
  retention_days: number | null;
  allow_client_self_label: boolean;
  allow_network_label: boolean;
  anomaly_baseline_runs: number;
  anomaly_deviation_percent: number;
  download_max_bytes: number;
  upload_max_bytes: number;
}

export async function fetchAdminSettings(): Promise<AdminSettings> {
  const r = await apiFetch("/api/settings");
  if (!r.ok) throw new Error(`settings ${r.status}`);
  return (await r.json()) as AdminSettings;
}

export async function patchAdminSettings(patch: Record<string, unknown>): Promise<AdminSettings> {
  const r = await apiFetch("/api/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`settings patch ${r.status}: ${t}`);
  }
  return (await r.json()) as AdminSettings;
}

/** Legacy path (still supported). Prefer exportTestsNewPath. */
export function exportUrl(format: "csv" | "json", params: URLSearchParams): string {
  const p = new URLSearchParams(params);
  p.set("format", format);
  return `${apiBase()}/api/tests/export?${p.toString()}`;
}

export function exportTestsNewPath(kind: "csv" | "json", params: URLSearchParams): string {
  return `${apiBase()}/api/export/tests.${kind}?${params.toString()}`;
}

export interface AnomalySummary {
  total_recent: number;
  by_metric: Record<string, number>;
  by_severity: Record<string, number>;
}

export async function fetchAnomalySummary(sinceDays = 14): Promise<AnomalySummary> {
  const p = new URLSearchParams();
  p.set("since_days", String(sinceDays));
  const r = await apiFetch(`/api/anomalies/summary?${p.toString()}`);
  if (!r.ok) throw new Error(`anomalies summary ${r.status}`);
  return (await r.json()) as AnomalySummary;
}

export interface AnomalyRow {
  id: number;
  created_at: string;
  test_run_id: number;
  client_id: number | null;
  metric_name: string;
  baseline_value: number | null;
  observed_value: number | null;
  deviation_pct: number | null;
  severity: string;
  metadata: Record<string, unknown>;
}

export async function fetchAnomalies(params: URLSearchParams): Promise<{
  items: AnomalyRow[];
  total: number;
}> {
  const r = await apiFetch(`/api/anomalies?${params.toString()}`);
  if (!r.ok) throw new Error(`anomalies ${r.status}`);
  return (await r.json()) as { items: AnomalyRow[]; total: number };
}
