# syntax=docker/dockerfile:1

FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Set to "true" by the `tests` compose service to add pytest and friends.
ARG INSTALL_DEV=false

# Dependencies are installed in their own layer so that application code
# changes do not invalidate the dependency cache.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --locked --no-install-project; \
    else \
        uv sync --locked --no-dev --no-install-project; \
    fi

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

# Runs unprivileged. On a Linux host the media bind mount must be writable by
# this uid: sudo chown -R 1000:1000 ./data/media
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data/media \
    && chown -R app:app /data /app
USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
