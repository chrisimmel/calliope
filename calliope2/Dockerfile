# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the Clio and Admin SPAs.
#
# Firebase client config is NOT secret (it's always public in the browser),
# but it must be baked in at webpack / vite build time.  Pass these as
# --build-arg flags or via Cloud Build substitutions.
#
# API_BASE_URL is intentionally left empty so Clio uses relative paths
# (served from the same origin as the FastAPI app).  Override only when
# the SPA is hosted separately from the API.
# ---------------------------------------------------------------------------
FROM node:20-slim AS node-builder

# Firebase / API build-time configuration for the Clio SPA.
ARG FIREBASE_API_KEY=""
ARG FIREBASE_AUTH_DOMAIN=""
ARG FIREBASE_PROJECT_ID=""
ARG FIREBASE_STORAGE_BUCKET=""
ARG FIREBASE_MESSAGING_SENDER_ID=""
ARG FIREBASE_APP_ID=""
ARG FIREBASE_MEASUREMENT_ID=""
ARG FIREBASE_DATABASE_ID=""
ARG API_BASE_URL=""

# Expose ARGs as env vars so webpack DefinePlugin picks them up.
ENV FIREBASE_API_KEY=$FIREBASE_API_KEY \
    FIREBASE_AUTH_DOMAIN=$FIREBASE_AUTH_DOMAIN \
    FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID \
    FIREBASE_STORAGE_BUCKET=$FIREBASE_STORAGE_BUCKET \
    FIREBASE_MESSAGING_SENDER_ID=$FIREBASE_MESSAGING_SENDER_ID \
    FIREBASE_APP_ID=$FIREBASE_APP_ID \
    FIREBASE_MEASUREMENT_ID=$FIREBASE_MEASUREMENT_ID \
    FIREBASE_DATABASE_ID=$FIREBASE_DATABASE_ID \
    API_BASE_URL=$API_BASE_URL

WORKDIR /build

# Pre-create static output dirs (mirrors what the npm build scripts do).
RUN mkdir -p apps/api/calliope2/static/clio apps/api/calliope2/static/admin

# ---- Clio (webpack) ----
# Copy manifests first for layer-caching of npm ci.
COPY apps/web/clio/package.json apps/web/clio/package-lock.json ./apps/web/clio/
RUN cd apps/web/clio && npm ci --prefer-offline

COPY apps/web/clio/ ./apps/web/clio/
RUN cd apps/web/clio && \
    npx webpack --mode production && \
    cp -r build/. ../../api/calliope2/static/clio/

# ---- Admin (vite) ----
COPY apps/web/admin/package.json apps/web/admin/package-lock.json ./apps/web/admin/
RUN cd apps/web/admin && npm ci --prefer-offline

COPY apps/web/admin/ ./apps/web/admin/
RUN cd apps/web/admin && \
    npx vite build && \
    cp -r dist/. ../../api/calliope2/static/admin/


# ---------------------------------------------------------------------------
# Stage 2 — Python runtime.
# ---------------------------------------------------------------------------
FROM python:3.11-bookworm AS runtime

# Install uv from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System libraries required at runtime (libpq for asyncpg, libffi/ssl for
# some Python packages that link against them at import time).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Dependency installation ----
# Copy workspace config + both package manifests so uv can resolve the lock.
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml ./apps/api/
COPY apps/cli/pyproject.toml ./apps/cli/

# Install deps only (source not yet present); --no-install-project skips the
# editable installs so we get a fully-cached dep layer.
RUN uv sync --frozen --no-dev --no-install-project

# ---- Application source ----
COPY apps/api/ ./apps/api/
COPY apps/cli/ ./apps/cli/

# Install the workspace packages themselves (editable installs against the
# source we just copied).
RUN uv sync --frozen --no-dev

# Copy the SPA bundles built in Stage 1.
COPY --from=node-builder /build/apps/api/calliope2/static/ ./apps/api/calliope2/static/

# Cloud Run injects $PORT at startup; default to 8080.
ENV PORT=8080
EXPOSE 8080

CMD ["uv", "run", "--no-dev", \
     "uvicorn", "calliope2.app:app", \
     "--app-dir", "apps/api", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "1"]
