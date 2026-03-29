#!/usr/bin/env python3
"""Insert synthetic test runs for demo dashboards (idempotent-ish: creates new rows each run)."""

import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Client, SamplePhase, TestRun, TestSample  # noqa: E402


def main() -> None:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://speedtest:speedtest@localhost:5432/speedtest",
    )
    engine = create_engine(url)
    SessionLocal = sessionmaker(bind=engine)

    stable = uuid.uuid4()
    with SessionLocal() as db:
        c = Client(
            stable_id=stable,
            label="demo-laptop",
            network_label="Home-5G",
            browser="Chrome",
            os="macOS",
            device_type="desktop",
            meta={"seed": True},
        )
        db.add(c)
        db.flush()

        now = datetime.now(timezone.utc)
        for i in range(40):
            day_offset = random.randint(0, 45)
            ts = now - timedelta(days=day_offset, hours=random.randint(0, 23))
            dl = random.uniform(80, 950)
            ul = random.uniform(40, 800)
            lat = random.uniform(0.8, 12.0)
            jit = random.uniform(0.1, 3.0)
            run = TestRun(
                created_at=ts,
                started_at=ts,
                completed_at=ts + timedelta(seconds=random.uniform(8, 35)),
                client_id=c.id,
                client_label=c.label,
                server_label="default",
                latency_ms_avg=lat,
                jitter_ms=jit,
                download_mbps=dl,
                upload_mbps=ul,
                packet_loss_pct=None,
                download_bytes_total=int(dl * 1e6 / 8 * random.uniform(0.5, 1.2)),
                upload_bytes_total=int(ul * 1e6 / 8 * random.uniform(0.5, 1.2)),
                duration_seconds=random.uniform(10, 30),
                success=random.random() > 0.05,
                failure_reason=None,
                raw_metrics_json={"seed": True, "scenario": "synthetic"},
                browser_user_agent="Mozilla/5.0 (demo)",
                ip_address="10.0.0." + str(random.randint(2, 200)),
                notes=None,
                network_label=c.network_label,
            )
            if not run.success:
                run.failure_reason = "aborted (synthetic)"
            db.add(run)
            db.flush()
            for j in range(5):
                db.add(
                    TestSample(
                        test_run_id=run.id,
                        phase=SamplePhase.ping,
                        t_offset_ms=float(j * 20),
                        value=lat + random.uniform(-0.5, 0.5),
                        unit="ms",
                        meta={},
                    )
                )
        db.commit()
    print("Seed complete: demo client + synthetic runs.")


if __name__ == "__main__":
    main()
