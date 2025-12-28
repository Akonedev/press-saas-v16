# =============================================================================
# Dockerfile - Press Self-Hosted
# =============================================================================
# Custom image for Frappe Press in self-hosted environment
# Based on official frappe_docker patterns
# =============================================================================

# Build arguments
ARG FRAPPE_VERSION=develop
ARG PYTHON_VERSION=3.11

# =============================================================================
# Stage 1: Base image with Frappe
# =============================================================================
FROM docker.io/frappe/bench:latest as base

# Labels
LABEL maintainer="ERP SaaS Cloud Team <admin@platform.local>"
LABEL org.opencontainers.image.title="Press Self-Hosted"
LABEL org.opencontainers.image.description="Frappe Press for self-hosted deployment"
LABEL org.opencontainers.image.version="0.0.1"

# Environment variables
ENV FRAPPE_BRANCH=${FRAPPE_VERSION}
ENV PRESS_BRANCH=develop
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    vim \
    mariadb-client \
    redis-server \
    redis-tools \
    jq \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch back to frappe user
USER frappe
WORKDIR /home/frappe

# Initialize bench (Frappe v16)
RUN bench init --frappe-branch ${FRAPPE_BRANCH:-develop} --python python3.11 frappe-bench --no-procfile --no-backups

WORKDIR /home/frappe/frappe-bench

# =============================================================================
# Stage 2: Install Press and dependencies
# =============================================================================
FROM base as press

# Get Press app
RUN bench get-app press --branch ${PRESS_BRANCH} || \
    bench get-app https://github.com/frappe/press --branch ${PRESS_BRANCH}

# Get storage integration app (for MinIO)
RUN bench get-app storage_integration || \
    bench get-app https://github.com/frappe/storage_integration || true

# =============================================================================
# Stage 3: Production image
# =============================================================================
FROM press as production

# NOTE: press_selfhosted will be mounted as volume in docker-compose.yml
# No need to copy it during build as it will be mounted at runtime

# Create sites directory structure
RUN mkdir -p sites/assets sites/logs

# NOTE: common_site_config.json will be created at runtime by configurator service
# following the frappe_docker pattern

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/method/ping || exit 1

# Default command
CMD ["bench", "start"]

# =============================================================================
# Stage 4: Development image
# =============================================================================
FROM production as development

# Enable developer mode
ENV DEVELOPER_MODE=1

# Install development dependencies
USER root
RUN pip install pytest pytest-cov pytest-asyncio

USER frappe

# Mount points for development
VOLUME ["/home/frappe/frappe-bench/apps/press_selfhosted"]
VOLUME ["/home/frappe/frappe-bench/sites"]

# Development command with hot reload
CMD ["bench", "start", "--with-coverage"]
