import json
import logging
import time
from collections.abc import Callable

from prometheus_client import Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("speedtest.request")

REQUEST_DURATION = Histogram(
    "speedtest_http_request_duration_seconds",
    "Wall time for handled HTTP requests",
    ["method"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        30.0,
        60.0,
        120.0,
        float("inf"),
    ),
)


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed = time.perf_counter() - start
            elapsed_ms = elapsed * 1000
            status = getattr(response, "status_code", 500)
            payload = {
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": round(elapsed_ms, 3),
            }
            logger.info(json.dumps(payload))
            try:
                REQUEST_DURATION.labels(method=request.method).observe(elapsed)
            except Exception:
                pass
