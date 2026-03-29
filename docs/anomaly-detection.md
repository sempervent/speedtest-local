# Anomaly detection (regression hints)

After each successful `POST /api/tests`, the API may insert rows into `anomaly_events` when a metric deviates sharply from recent history for the same client (when `client_id` is present).

## Configuration

Admin settings (PostgreSQL `app_settings`, editable in the UI **Settings** page):

- **Anomaly baseline runs** — how many prior *successful* runs are considered (minimum 3 used internally).
- **Anomaly deviation (%)** — observed value must fall below `baseline × (1 − threshold/100)` to flag a **low** anomaly (typical for download/upload Mbps regressions). Latency uses the inverse (observed above baseline × `(1 + threshold/100)`).

`retention_days` is separate: it only drives age-based pruning (`scripts/prune.py` or `POST /api/admin/prune`), not anomaly math.

## API

- `GET /api/anomalies` — paginated list (optional `client_id`, time filters).
- `GET /api/anomalies/summary` — counts by metric and severity.

The analytics UI shows a summary and recent events; charts are interpretive overlays, not a separate detection engine.
