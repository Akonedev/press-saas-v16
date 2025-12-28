#!/bin/bash
# =============================================================================
# MinIO Bucket Initialization Script - ERP SaaS Cloud PRESSE v16
# =============================================================================
# This script creates the required buckets in MinIO for Press self-hosted
# Constitution Constraint: Container prefix erp-saas-cloud-c16-*
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
CONTAINER_PREFIX="${CONTAINER_PREFIX:-erp-saas-cloud-c16}"
MINIO_CONTAINER="${CONTAINER_PREFIX}-minio"
MINIO_ALIAS="presscloud"

# MinIO Credentials (from environment or defaults)
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:32390}"

# Required buckets
BUCKET_FILES="${CONTAINER_PREFIX}-files"
BUCKET_BACKUPS="${CONTAINER_PREFIX}-backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect container runtime
get_runtime() {
    if command -v podman &> /dev/null; then
        echo "podman"
    elif command -v docker &> /dev/null; then
        echo "docker"
    else
        log_error "Neither docker nor podman found"
        exit 1
    fi
}

RUNTIME=$(get_runtime)
log_info "Using container runtime: $RUNTIME"

# -----------------------------------------------------------------------------
# Check MinIO Container
# -----------------------------------------------------------------------------
check_minio_running() {
    log_info "Checking if MinIO container is running..."

    if ! $RUNTIME ps --format '{{.Names}}' | grep -q "^${MINIO_CONTAINER}$"; then
        log_error "MinIO container '${MINIO_CONTAINER}' is not running"
        log_info "Start MinIO with: docker compose up -d minio"
        exit 1
    fi

    log_success "MinIO container is running"
}

# -----------------------------------------------------------------------------
# Wait for MinIO to be Ready
# -----------------------------------------------------------------------------
wait_for_minio() {
    log_info "Waiting for MinIO to be ready..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "${MINIO_ENDPOINT}/minio/health/live" &>/dev/null; then
            log_success "MinIO is ready"
            return 0
        fi

        log_info "Waiting for MinIO... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    log_error "MinIO did not become ready in time"
    exit 1
}

# -----------------------------------------------------------------------------
# Install MinIO Client (mc) if needed
# -----------------------------------------------------------------------------
install_mc() {
    log_info "Checking MinIO client (mc)..."

    # Check if mc is available in container
    if $RUNTIME exec "$MINIO_CONTAINER" which mc &>/dev/null; then
        log_success "MinIO client (mc) is available"
        return 0
    fi

    log_warning "MinIO client (mc) not found in container"
    log_info "Installing MinIO client..."

    # Download and install mc in container
    $RUNTIME exec "$MINIO_CONTAINER" sh -c \
        "wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/bin/mc && chmod +x /usr/bin/mc"

    log_success "MinIO client installed"
}

# -----------------------------------------------------------------------------
# Configure MinIO Alias
# -----------------------------------------------------------------------------
configure_alias() {
    log_info "Configuring MinIO alias..."

    $RUNTIME exec "$MINIO_CONTAINER" mc alias set "$MINIO_ALIAS" \
        "http://localhost:9000" \
        "$MINIO_ROOT_USER" \
        "$MINIO_ROOT_PASSWORD" \
        &>/dev/null

    log_success "MinIO alias configured: $MINIO_ALIAS"
}

# -----------------------------------------------------------------------------
# Create Bucket
# -----------------------------------------------------------------------------
create_bucket() {
    local bucket_name=$1
    local description=$2

    log_info "Creating bucket: $bucket_name ($description)"

    # Check if bucket exists
    if $RUNTIME exec "$MINIO_CONTAINER" mc ls "${MINIO_ALIAS}/${bucket_name}" &>/dev/null; then
        log_warning "Bucket '${bucket_name}' already exists"
        return 0
    fi

    # Create bucket
    if $RUNTIME exec "$MINIO_CONTAINER" mc mb "${MINIO_ALIAS}/${bucket_name}"; then
        log_success "Bucket '${bucket_name}' created"
    else
        log_error "Failed to create bucket '${bucket_name}'"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Set Bucket Policy
# -----------------------------------------------------------------------------
set_bucket_policy() {
    local bucket_name=$1

    log_info "Setting policy for bucket: $bucket_name"

    # Set public read policy (can be customized based on needs)
    # For production, use more restrictive policies
    $RUNTIME exec "$MINIO_CONTAINER" mc anonymous set download "${MINIO_ALIAS}/${bucket_name}" &>/dev/null || true

    log_success "Policy set for '${bucket_name}'"
}

# -----------------------------------------------------------------------------
# Enable Versioning
# -----------------------------------------------------------------------------
enable_versioning() {
    local bucket_name=$1

    log_info "Enabling versioning for: $bucket_name"

    $RUNTIME exec "$MINIO_CONTAINER" mc version enable "${MINIO_ALIAS}/${bucket_name}" &>/dev/null

    log_success "Versioning enabled for '${bucket_name}'"
}

# -----------------------------------------------------------------------------
# Verify Buckets
# -----------------------------------------------------------------------------
verify_buckets() {
    log_info "Verifying bucket configuration..."

    echo ""
    echo "=========================================="
    echo "MinIO Buckets"
    echo "=========================================="

    $RUNTIME exec "$MINIO_CONTAINER" mc ls "$MINIO_ALIAS"

    echo ""
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    echo "=========================================="
    echo "MinIO Bucket Initialization"
    echo "=========================================="
    echo ""

    check_minio_running
    wait_for_minio
    install_mc
    configure_alias

    # Create required buckets
    create_bucket "$BUCKET_FILES" "Tenant file storage"
    create_bucket "$BUCKET_BACKUPS" "Site backups"

    # Set bucket policies (optional, customize as needed)
    # set_bucket_policy "$BUCKET_FILES"
    # set_bucket_policy "$BUCKET_BACKUPS"

    # Enable versioning for backups
    enable_versioning "$BUCKET_BACKUPS"

    verify_buckets

    echo ""
    echo "=========================================="
    echo -e "${GREEN}MinIO Initialization Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Buckets created:"
    echo "  - $BUCKET_FILES (Files)"
    echo "  - $BUCKET_BACKUPS (Backups with versioning)"
    echo ""
    echo "MinIO Console: http://localhost:32391"
    echo "MinIO API: http://localhost:32390"
    echo "Credentials: $MINIO_ROOT_USER / $MINIO_ROOT_PASSWORD"
    echo ""
}

# Run main function
main "$@"
