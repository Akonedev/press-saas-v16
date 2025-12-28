#!/bin/bash
# =============================================================================
# Press Site Setup Script - ERP SaaS Cloud PRESSE v16
# =============================================================================
# This script initializes the Press site and configures essential settings
# Constitution Constraint: Container prefix erp-saas-cloud-c16-*
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
CONTAINER_PREFIX="${CONTAINER_PREFIX:-erp-saas-cloud-c16}"
PRESS_CONTAINER="${CONTAINER_PREFIX}-press"
MARIADB_CONTAINER="${CONTAINER_PREFIX}-mariadb"
SITE_NAME="${SITE_NAME:-press.platform.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
MARIADB_ROOT_PASSWORD="${MARIADB_ROOT_PASSWORD:-}"

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
# Pre-flight Checks
# -----------------------------------------------------------------------------
preflight_checks() {
    log_info "Running pre-flight checks..."

    # Check if Press container is running
    if ! $RUNTIME ps --format '{{.Names}}' | grep -q "^${PRESS_CONTAINER}$"; then
        log_error "Press container '${PRESS_CONTAINER}' is not running"
        log_info "Start containers with: docker compose up -d"
        exit 1
    fi

    # Check if MariaDB is healthy
    if ! $RUNTIME exec "$MARIADB_CONTAINER" mysqladmin ping -h localhost --silent 2>/dev/null; then
        log_error "MariaDB is not responding"
        exit 1
    fi

    log_success "Pre-flight checks passed"
}

# -----------------------------------------------------------------------------
# Wait for Services
# -----------------------------------------------------------------------------
wait_for_services() {
    log_info "Waiting for services to be ready..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if $RUNTIME exec "$PRESS_CONTAINER" bench --help &>/dev/null; then
            log_success "Press container is ready"
            return 0
        fi
        log_info "Waiting for Press container... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done

    log_error "Press container did not become ready in time"
    exit 1
}

# -----------------------------------------------------------------------------
# Create Site
# -----------------------------------------------------------------------------
create_site() {
    log_info "Creating site: $SITE_NAME"

    # Check if site already exists
    if $RUNTIME exec "$PRESS_CONTAINER" ls -la "sites/$SITE_NAME" &>/dev/null; then
        log_warning "Site '$SITE_NAME' already exists"
        read -p "Do you want to reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping site creation"
            return 0
        fi
        log_info "Reinstalling site..."
        $RUNTIME exec "$PRESS_CONTAINER" bench reinstall --yes --admin-password "$ADMIN_PASSWORD"
        return 0
    fi

    # Create new site
    $RUNTIME exec "$PRESS_CONTAINER" bench new-site "$SITE_NAME" \
        --mariadb-root-password "$MARIADB_ROOT_PASSWORD" \
        --admin-password "$ADMIN_PASSWORD" \
        --no-mariadb-socket

    log_success "Site created: $SITE_NAME"
}

# -----------------------------------------------------------------------------
# Install Apps
# -----------------------------------------------------------------------------
install_apps() {
    log_info "Installing apps on site: $SITE_NAME"

    # Install Press app
    if $RUNTIME exec "$PRESS_CONTAINER" bench list-apps | grep -q "^press$"; then
        log_info "Installing Press app..."
        $RUNTIME exec "$PRESS_CONTAINER" bench --site "$SITE_NAME" install-app press
        log_success "Press app installed"
    else
        log_warning "Press app not found in bench"
    fi

    # Install press_selfhosted if available
    if $RUNTIME exec "$PRESS_CONTAINER" bench list-apps | grep -q "^press_selfhosted$"; then
        log_info "Installing Press Self-Hosted app..."
        $RUNTIME exec "$PRESS_CONTAINER" bench --site "$SITE_NAME" install-app press_selfhosted
        log_success "Press Self-Hosted app installed"
    fi
}

# -----------------------------------------------------------------------------
# Configure Site
# -----------------------------------------------------------------------------
configure_site() {
    log_info "Configuring site settings..."

    # Set as default site
    $RUNTIME exec "$PRESS_CONTAINER" bench use "$SITE_NAME"

    # Enable scheduler
    $RUNTIME exec "$PRESS_CONTAINER" bench --site "$SITE_NAME" enable-scheduler

    # Build assets
    log_info "Building frontend assets..."
    $RUNTIME exec "$PRESS_CONTAINER" bench build

    log_success "Site configured successfully"
}

# -----------------------------------------------------------------------------
# Verify Installation
# -----------------------------------------------------------------------------
verify_installation() {
    log_info "Verifying installation..."

    # Check site status
    local status
    status=$($RUNTIME exec "$PRESS_CONTAINER" bench --site "$SITE_NAME" doctor 2>&1 || true)

    if echo "$status" | grep -q "error"; then
        log_warning "Some issues detected:"
        echo "$status"
    else
        log_success "Site health check passed"
    fi

    # Display access information
    echo ""
    echo "=========================================="
    echo -e "${GREEN}Press Setup Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Site: $SITE_NAME"
    echo "URL: https://${SITE_NAME}:32443"
    echo "Login: Administrator"
    echo "Password: $ADMIN_PASSWORD"
    echo ""
    echo "API Health Check: curl -k https://${SITE_NAME}:32443/api/method/ping"
    echo ""
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    echo "=========================================="
    echo "Press Self-Hosted Setup Script"
    echo "=========================================="
    echo ""

    preflight_checks
    wait_for_services
    create_site
    install_apps
    configure_site
    verify_installation
}

# Run main function
main "$@"
