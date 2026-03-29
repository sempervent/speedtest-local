FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY probe_agent ./probe_agent
RUN pip install --no-cache-dir .

ENTRYPOINT ["probe"]
