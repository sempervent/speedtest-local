from datetime import datetime, timezone

from app.models import Client, TestRun


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ping_cache_headers(client):
    r = client.get("/api/ping?_cb=1")
    assert r.status_code == 200
    assert "no-store" in r.headers.get("cache-control", "")


def test_download_stream(client):
    r = client.get("/api/download?bytes=4096&_cb=x")
    assert r.status_code == 200
    assert len(r.content) == 4096


def test_post_test_and_list(client, db_session):
    body = {
        "success": True,
        "client_label": "t-client",
        "network_label": "lab-wifi",
        "server_label": "default",
        "latency_ms_avg": 2.5,
        "jitter_ms": 0.4,
        "download_mbps": 120.0,
        "upload_mbps": 95.0,
        "download_bytes_total": 1_000_000,
        "upload_bytes_total": 800_000,
        "duration_seconds": 12.0,
        "browser_user_agent": "pytest",
        "raw_metrics_json": {"unit": "test"},
    }
    r = client.post("/api/tests", json=body)
    assert r.status_code == 200
    tid = r.json()["id"]
    r2 = client.get("/api/tests")
    assert r2.status_code == 200
    data = r2.json()
    assert data["total"] >= 1
    assert any(x["id"] == tid for x in data["items"])
    r3 = client.get(f"/api/tests/{tid}")
    assert r3.status_code == 200


def test_stats_summary(client, db_session):
    db_session.add(
        TestRun(
            created_at=datetime.now(timezone.utc),
            server_label="default",
            download_mbps=100.0,
            upload_mbps=50.0,
            latency_ms_avg=5.0,
            jitter_ms=1.0,
            success=True,
        )
    )
    db_session.commit()
    r = client.get("/api/stats/summary")
    assert r.status_code == 200
    j = r.json()
    assert j["count"] >= 1
    assert j["download_mbps_avg"] is not None


def test_stats_timeseries(client, db_session):
    db_session.add(
        TestRun(
            created_at=datetime.now(timezone.utc),
            server_label="default",
            download_mbps=200.0,
            upload_mbps=100.0,
            latency_ms_avg=3.0,
            jitter_ms=0.5,
            success=True,
        )
    )
    db_session.commit()
    r = client.get("/api/stats/timeseries?bucket=day")
    assert r.status_code == 200
    assert "points" in r.json()


def test_clients_list(client, db_session):
    c = Client(label="x", meta={})
    db_session.add(c)
    db_session.commit()
    r = client.get("/api/clients")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
