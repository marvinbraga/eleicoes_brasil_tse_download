# Builder and runtime are both CPython 3.12.15 / Alpine 3.23 so the venv ABI matches.
FROM ghcr.io/astral-sh/uv:0.12.23-python3.12-alpine3.23 AS builder

RUN apk add --no-cache gcc musl-dev libpq-dev

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

COPY src ./src
RUN uv sync --frozen --no-dev --no-editable --no-cache

FROM python:3.12.15-alpine3.23

RUN apk add --no-cache libpq \
    && addgroup -S appgroup \
    && adduser -S appuser -G appgroup

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/app/.venv

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import eleicoes" || exit 1

CMD ["sleep", "infinity"]
