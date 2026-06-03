# syntax=docker/dockerfile:1.7
#
# Foyre validation runner image.
#
# Two roles, one image:
#   1. The uploader sidecar that pushes /foyre/output evidence + result.json
#      back to the Foyre ingest endpoint (uses uploader.py, stdlib only).
#   2. The runtime for the inline-script step tier (custom.script) — carries
#      bash / python / jq / kubectl so admin-authored scripts have tools.
#
# Deliberately slim and app-free: it never contains Foyre application code,
# so it's safe to run inside a tenant validation cluster.

FROM python:3.12-slim AS runner
ARG TARGETARCH=amd64
ARG KUBECTL_VERSION=v1.30.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        jq \
        ca-certificates \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

# kubectl for script-tier checks that inspect the cluster.
RUN curl -fSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
        -o /usr/local/bin/kubectl && \
    chmod +x /usr/local/bin/kubectl

# The uploader sidecar entrypoint (stdlib only; no pip deps).
COPY deploy/runner/uploader.py /opt/foyre/uploader.py
RUN chmod +x /opt/foyre/uploader.py

# Non-root by default; jobs/scripts run unprivileged.
RUN useradd --uid 10002 --create-home --shell /bin/bash foyrerun
USER 10002:10002

ENTRYPOINT ["/usr/bin/tini", "--"]
# Default command runs the uploader; the script tier overrides command/args.
CMD ["python3", "/opt/foyre/uploader.py"]
