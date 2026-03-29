import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
from starlette.responses import Response

from app.api.routes import admin, anomalies, clients, config as config_route, health, measure, stats, tests
from app.api.routes.export_routes import router as export_router
from app.api.routes.settings import router as settings_router
from app.config import get_settings
from app.database import SessionLocal
from app.middleware.timing import TimingMiddleware
from app.services.app_settings_service import ensure_app_settings_row, row_to_settings_out

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("speedtest.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app
    settings = get_settings()
    try:
        with SessionLocal() as db:
            row = ensure_app_settings_row(db, settings)
            db.commit()
            eff = row_to_settings_out(row, settings)
            log.info(
                "startup effective settings: server_label=%s retention_days=%s anomaly_window=%s",
                eff.server_label,
                eff.retention_days,
                eff.anomaly_baseline_runs,
            )
    except Exception:
        log.exception("startup app_settings bootstrap failed")
        raise
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="speedtest-local API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exc(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "validation_error",
                "errors": exc.errors(),
            },
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TimingMiddleware)

    app.include_router(health.router)
    app.include_router(config_route.router)
    app.include_router(measure.router)
    app.include_router(tests.router)
    app.include_router(export_router)
    app.include_router(stats.router)
    app.include_router(clients.router)
    app.include_router(settings_router)
    app.include_router(anomalies.router)
    app.include_router(admin.router)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        if not settings.enable_metrics:
            return Response(status_code=404)
        data = generate_latest(REGISTRY)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
