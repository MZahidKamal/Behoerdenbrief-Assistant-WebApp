# syntax=docker/dockerfile:1

# One image for the API and, later, the worker (ARCHITECTURE §12.2).
# Build it in `server_side/`:  docker build -t behoerdenbrief-server .
# Settings come as environment variables when the container starts; the
# image itself never contains secrets or a `.env` file.

# ---------------------------------------------------------------------------
# Stage 1 "builder": installs the Python packages with uv.
# ---------------------------------------------------------------------------
# The same Python and uv versions as on the developer's computer.
FROM python:3.14.10-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv

# Compile the packages to bytecode now, so the app starts faster. Copy files
# instead of linking them (the cache is a separate mount). Use the image's own
# Python and never download another one. Put the environment in /app/.venv.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install only the runtime packages, exactly as in uv.lock (`--frozen`,
# `--no-dev`). The two files are only mounted, so they do not stay in a layer,
# and uv's download cache lives outside the image. This layer is rebuilt only
# when the packages change, not when our code changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Stage 2 "runtime": only Python, the finished packages and our code.
# No uv and no build tools, so the image is smaller and has less to attack.
# ---------------------------------------------------------------------------
FROM python:3.14.10-slim-trixie AS runtime

# A system user without a home folder and without a login. The app runs as
# this user, never as root.
RUN groupadd --system --gid 1001 application_group && \
    useradd --system --uid 1001 --gid application_group \
        --no-create-home --shell /usr/sbin/nologin application_user

WORKDIR /app

# Use the packages from the builder stage. Print log lines at once (no
# buffer). Write no bytecode at runtime: the code folder is read-only.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# The files belong to root, so the app can read but never change its code.
COPY --link --from=builder /app/.venv /app/.venv
COPY --link app ./app

# Alembic needs its settings file and the migration scripts, so the same image
# can run `alembic upgrade head` (ARCHITECTURE §12.4, DATA_MODEL §9).
COPY --link alembic.ini ./
COPY --link migrations ./migrations

USER application_user

EXPOSE 8000

LABEL org.opencontainers.image.source="https://github.com/MZahidKamal/Behoerdenbrief-Assistant-WebApp" \
      org.opencontainers.image.description="Behördenbrief Assistant backend (API and worker)"

# The API. The worker and the developer commands use the same image with
# another command, so this is CMD and not ENTRYPOINT.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
