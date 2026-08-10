FROM python:3.11-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache

WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.3
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable --extra serve

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/app/.venv/bin:$PATH \
    AI_ENV=production \
    AI_MODEL_BUNDLE_PATH=/models/current \
    AI_ARTIFACT_ROOT=/models \
    AI_STORE_ID=1

RUN groupadd --system ai && useradd --system --gid ai --home /app ai
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
RUN chown -R ai:ai /app
USER ai
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"
CMD ["ai-serve"]
