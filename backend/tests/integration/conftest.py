import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://speedtest:speedtest@localhost:5432/speedtest")
os.environ.setdefault("CORS_ORIGINS", "http://test")

from app.database import get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    url = os.environ["DATABASE_URL"]
    eng = create_engine(url, pool_pre_ping=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OSError as exc:
        pytest.skip(
            f"PostgreSQL unavailable ({exc}); start docker compose postgres for integration tests."
        )
    except Exception as exc:
        pytest.skip(
            f"PostgreSQL unavailable ({exc}); start docker compose postgres for integration tests."
        )
    return eng


@pytest.fixture(autouse=True)
def _truncate_tables(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE anomaly_events, test_samples, test_runs, clients, app_settings "
                "RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest.fixture
def db_session(engine) -> Session:
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session):
    app = create_app()

    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
