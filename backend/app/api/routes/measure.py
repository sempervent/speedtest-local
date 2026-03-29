import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from prometheus_client import Counter

from app.config import Settings, get_settings
from app.schemas import PingResponse, UploadResponse

router = APIRouter(prefix="/api", tags=["measure"])

DOWNLOAD_BYTES = Counter(
    "speedtest_download_bytes_total",
    "Bytes served by download endpoint",
)
UPLOAD_BYTES = Counter(
    "speedtest_upload_bytes_total",
    "Bytes received by upload endpoint",
)


@router.get("/ping", response_model=PingResponse)
def ping(
    cache_bust: Annotated[str | None, Query(alias="_cb")] = None,
) -> JSONResponse:
    """Minimal payload for RTT; client measures wall-clock request time."""
    _ = cache_bust
    payload = PingResponse(server_ts_ms=time.time() * 1000)
    return JSONResponse(
        content=payload.model_dump(),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


def _random_stream(total: int, chunk: int = 256 * 1024):
    import os

    sent = 0
    while sent < total:
        n = min(chunk, total - sent)
        yield os.urandom(n)
        sent += n


@router.get("/download")
def download(
    bytes: Annotated[int, Query(ge=1, alias="bytes", description="Number of bytes to stream")],
    settings: Settings = Depends(get_settings),
    cache_bust: Annotated[str | None, Query(alias="_cb")] = None,
) -> StreamingResponse:
    _ = cache_bust
    cap = min(bytes, settings.download_max_bytes)
    DOWNLOAD_BYTES.inc(cap)

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
        "Content-Length": str(cap),
        "X-Generated-Body": "1",
    }
    return StreamingResponse(
        _random_stream(cap),
        media_type="application/octet-stream",
        headers=headers,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    total = 0
    max_b = settings.upload_max_bytes
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_b:
            raise HTTPException(status_code=413, detail="upload exceeds configured upload_max_bytes")
    UPLOAD_BYTES.inc(total)
    return UploadResponse(bytes_received=total)
