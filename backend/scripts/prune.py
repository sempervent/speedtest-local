#!/usr/bin/env python3
"""Prune old test runs (and samples via FK). Use --dry-run first."""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Settings, get_settings  # noqa: E402
from app.services.app_settings_service import get_app_settings  # noqa: E402
from app.services.prune_service import prune_older_than  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Prune speedtest-local history by age")
    p.add_argument("--dry-run", action="store_true", help="Report counts only")
    p.add_argument(
        "--days",
        type=int,
        default=None,
        help="Retention days (defaults to app_settings.retention_days)",
    )
    args = p.parse_args()

    env = get_settings()
    url = os.getenv("DATABASE_URL", env.database_url)
    eng = create_engine(url)
    Session = sessionmaker(bind=eng)
    with Session() as db:
        app_row = get_app_settings(db, env)
        days = args.days if args.days is not None else app_row.retention_days
        if days is None:
            print("retention_days not set (pass --days or set in app_settings)", file=sys.stderr)
            sys.exit(1)
        cutoff, matched, samples, runs = prune_older_than(
            db, retention_days=days, dry_run=args.dry_run
        )
        if not args.dry_run:
            db.commit()
        else:
            db.rollback()
    print(
        f"cutoff={cutoff.isoformat()} matched_runs={matched} "
        f"samples~={samples} runs_deleted={runs} dry_run={args.dry_run}"
    )


if __name__ == "__main__":
    main()
