from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client


def upsert_client_from_test(
    db: Session,
    *,
    stable_id: UUID | None,
    label: str | None,
    network_label: str | None,
    browser_user_agent: str | None,
    parse_hints: dict[str, Any] | None = None,
) -> Client | None:
    """Link test to a client row. Creates or updates by stable_id when provided."""
    hints = parse_hints or {}
    now = datetime.now(timezone.utc)
    if stable_id is None:
        c = Client(
            stable_id=None,
            label=label,
            network_label=network_label,
            browser=hints.get("browser"),
            os=hints.get("os"),
            device_type=hints.get("device_type"),
            last_seen_at=now,
            first_seen_at=now,
            meta={},
        )
        db.add(c)
        db.flush()
        return c

    existing = db.scalar(select(Client).where(Client.stable_id == stable_id))
    if existing:
        existing.last_seen_at = now
        if label:
            existing.label = label
        if network_label is not None:
            existing.network_label = network_label
        if browser_user_agent:
            existing.browser = hints.get("browser") or existing.browser
            existing.os = hints.get("os") or existing.os
            existing.device_type = hints.get("device_type") or existing.device_type
        db.flush()
        return existing

    c = Client(
        stable_id=stable_id,
        label=label,
        network_label=network_label,
        browser=hints.get("browser"),
        os=hints.get("os"),
        device_type=hints.get("device_type"),
        last_seen_at=now,
        first_seen_at=now,
        meta={},
    )
    db.add(c)
    db.flush()
    return c


def parse_ua_simple(ua: str | None) -> dict[str, str | None]:
    """Lightweight UA hints for display filters (not a full UA database)."""
    if not ua:
        return {"browser": None, "os": None, "device_type": None}
    u = ua.lower()
    browser = "unknown"
    if "edg/" in u or "edga/" in u:
        browser = "Edge"
    elif "chrome" in u and "chromium" not in u:
        browser = "Chrome"
    elif "firefox" in u:
        browser = "Firefox"
    elif "safari" in u and "chrome" not in u:
        browser = "Safari"
    os_name = None
    if "windows" in u:
        os_name = "Windows"
    elif "mac os" in u or "macos" in u:
        os_name = "macOS"
    elif "android" in u:
        os_name = "Android"
    elif "iphone" in u or "ipad" in u:
        os_name = "iOS"
    elif "linux" in u:
        os_name = "Linux"
    device = "desktop"
    if "mobile" in u or "android" in u or "iphone" in u:
        device = "mobile"
    return {"browser": browser, "os": os_name, "device_type": device}
