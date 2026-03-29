# speedtest-local API

FastAPI backend. See repository root [README.md](../README.md) for full documentation.

## Local development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://speedtest:speedtest@localhost:5432/speedtest
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI: http://localhost:8000/docs
