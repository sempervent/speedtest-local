.PHONY: up down logs test lint fmt migrate seed probe-run prune export

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

test:
	cd backend && pip install -q -e ".[dev]" && DATABASE_URL=postgresql+psycopg://speedtest:speedtest@127.0.0.1:5432/speedtest pytest
	cd frontend && npm install && npm run test
	cd probe-agent && pip install -q -e ".[dev]" && pytest

probe-run:
	cd probe-agent && pip install -q -e . && probe run --server http://127.0.0.1:8080

prune:
	cd backend && pip install -q -e ".[dev]" && DATABASE_URL=postgresql+psycopg://speedtest:speedtest@127.0.0.1:5432/speedtest python scripts/prune.py --dry-run

export:
	@echo 'Example (through nginx on 8080): curl -fsS "http://127.0.0.1:8080/api/export/tests.csv" -o tests.csv'

lint:
	cd backend && pip install -q -e ".[dev]" && ruff check app tests scripts
	cd frontend && npm install && npm run lint
	cd probe-agent && pip install -q -e ".[dev]" && ruff check probe_agent tests

fmt:
	cd backend && pip install -q -e ".[dev]" && ruff format app tests scripts
	cd frontend && npm install && npm run fmt
	cd probe-agent && pip install -q -e ".[dev]" && ruff format probe_agent tests

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python scripts/seed.py
