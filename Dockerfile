# syntax=docker/dockerfile:1.7

###############################################################################
# Stage 1 — build the frontend bundle
###############################################################################
FROM node:20-alpine AS frontend
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build
# `dist/` now contains the production SPA.

###############################################################################
# Stage 2 — fetch external CLIs (vcluster, kubectl)
###############################################################################
FROM alpine:3.20 AS tools
ARG TARGETARCH=amd64
ARG VCLUSTER_VERSION=0.33.1
ARG KUBECTL_VERSION=v1.30.0

RUN apk add --no-cache curl ca-certificates

# vcluster CLI — backend shells out to this for create/delete.
RUN curl -fSL "https://github.com/loft-sh/vcluster/releases/download/v${VCLUSTER_VERSION}/vcluster-linux-${TARGETARCH}" \
        -o /tmp/vcluster && \
    chmod +x /tmp/vcluster

# kubectl — useful for ops/debug; vcluster's CLI invokes it indirectly via
# the embedded Go client, but having it on PATH keeps `kubectl exec` debugging
# simple inside the pod.
RUN curl -fSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
        -o /tmp/kubectl && \
    chmod +x /tmp/kubectl

###############################################################################
# Stage 3 — Python runtime
###############################################################################
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STATIC_DIR=/app/static \
    DATA_DIR=/data \
    DATABASE_URL=sqlite:////data/foyre.db

# Tini for proper PID-1 signal handling, ca-certificates for outbound TLS.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first for layer caching.
COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Application code, frontend bundle, license attribution, and CLIs.
COPY backend/app /app/app
COPY --from=frontend /build/dist /app/static
COPY LICENSE NOTICE /app/
COPY --from=tools /tmp/vcluster /usr/local/bin/vcluster
COPY --from=tools /tmp/kubectl  /usr/local/bin/kubectl

# Non-root user. The Helm chart's PVC is mounted at /data and the chart sets
# fsGroup so this UID can write to it.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin foyre && \
    mkdir -p /data && \
    chown -R foyre:foyre /data /app

USER 10001:10001

EXPOSE 8000

# Liveness / readiness probes hit /healthz (no-auth, 204 OK).
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
