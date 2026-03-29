import uuid


def test_ready_endpoint(client):
    r = client.get("/ready")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "alembic_version" in data


def test_settings_get_includes_new_fields(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    j = r.json()
    assert "retention_days" in j
    assert "allow_client_self_label" in j
    assert "anomaly_baseline_runs" in j


def test_settings_patch(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    cur = r.json()
    r2 = client.patch(
        "/api/settings",
        json={"anomaly_deviation_percent": 12.5, "retention_days": 90},
    )
    assert r2.status_code == 200
    j = r2.json()
    assert j["anomaly_deviation_percent"] == 12.5
    assert j["retention_days"] == 90
    client.patch(
        "/api/settings",
        json={"anomaly_deviation_percent": cur["anomaly_deviation_percent"]},
    )


def test_export_new_paths(client):
    client.post(
        "/api/tests",
        json={
            "success": True,
            "server_label": "default",
            "download_mbps": 1.0,
            "upload_mbps": 1.0,
            "browser_user_agent": "test",
        },
    )
    r = client.get("/api/export/tests.csv")
    assert r.status_code == 200
    assert "download_mbps" in r.text or "id" in r.text
    rj = client.get("/api/export/tests.json")
    assert rj.status_code == 200
    assert b"[" in rj.content


def test_regression_creates_anomaly(client):
    stable = str(uuid.uuid4())
    base = {
        "success": True,
        "client_stable_id": stable,
        "client_label": "probe-test",
        "server_label": "default",
        "latency_ms_avg": 2.0,
        "jitter_ms": 0.2,
        "upload_mbps": 50.0,
        "browser_user_agent": "pytest",
    }
    for _ in range(3):
        p = {**base, "download_mbps": 100.0}
        pr = client.post("/api/tests", json=p)
        assert pr.status_code == 200
    pr = client.post("/api/tests", json={**base, "download_mbps": 10.0})
    assert pr.status_code == 200
    rid = pr.json()["id"]
    lst = client.get("/api/anomalies")
    assert lst.status_code == 200
    items = lst.json()["items"]
    assert any(x["test_run_id"] == rid and x["metric_name"] == "download_mbps" for x in items)


def test_anomalies_summary(client):
    r = client.get("/api/anomalies/summary?since_days=30")
    assert r.status_code == 200
    j = r.json()
    assert "total_recent" in j
    assert "by_metric" in j
