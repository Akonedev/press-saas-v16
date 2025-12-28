#!/bin/bash
# =============================================================================
# Quickstart Validation Script - ERP SaaS Cloud PRESSE v16
# =============================================================================
# Validates that the quickstart deployment is working correctly
# Constitution Constraint: Container prefix erp-saas-cloud-c16-*
# Constitution Constraint: Port range 32300-32500
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
CONTAINER_PREFIX="${CONTAINER_PREFIX:-erp-saas-cloud-c16}"
SITE_NAME="${SITE_NAME:-press.platform.local}"

# Expected containers
EXPECTED_CONTAINERS=(
    "${CONTAINER_PREFIX}-mariadb"
    "${CONTAINER_PREFIX}-redis-cache"
    "${CONTAINER_PREFIX}-redis-queue"
    "${CONTAINER_PREFIX}-press"
    "${CONTAINER_PREFIX}-worker-short"
    "${CONTAINER_PREFIX}-worker-long"
    "${CONTAINER_PREFIX}-worker-default"
    "${CONTAINER_PREFIX}-scheduler"
)

# Expected ports (Constitution: 32300-32500)
EXPECTED_PORTS=(
    "32300"  # Press web
    "32306"  # MariaDB
    "32378"  # Redis queue
    "32379"  # Redis cache
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Detect container runtime
get_runtime() {
    if command -v podman &> /dev/null; then
        echo "podman"
    elif command -v docker &> /dev/null; then
        echo "docker"
    else
        echo ""
    fi
}

RUNTIME=$(get_runtime)

# -----------------------------------------------------------------------------
# Validation: Container Runtime
# -----------------------------------------------------------------------------
validate_runtime() {
    log_info "Checking container runtime..."

    if [ -z "$RUNTIME" ]; then
        log_fail "No container runtime found (docker or podman)"
        return 1
    fi

    log_pass "Container runtime: $RUNTIME"
}

# -----------------------------------------------------------------------------
# Validation: Required Containers
# -----------------------------------------------------------------------------
validate_containers() {
    log_info "Checking required containers..."

    local running_containers
    running_containers=$($RUNTIME ps --format '{{.Names}}' 2>/dev/null || echo "")

    for container in "${EXPECTED_CONTAINERS[@]}"; do
        if echo "$running_containers" | grep -q "^${container}$"; then
            log_pass "Container running: $container"
        else
            log_fail "Container not running: $container"
        fi
    done
}

# -----------------------------------------------------------------------------
# Validation: Container Health
# -----------------------------------------------------------------------------
validate_health() {
    log_info "Checking container health..."

    # Check MariaDB health
    if $RUNTIME exec "${CONTAINER_PREFIX}-mariadb" mysqladmin ping -h localhost --silent 2>/dev/null; then
        log_pass "MariaDB is healthy"
    else
        log_fail "MariaDB health check failed"
    fi

    # Check Redis cache
    if $RUNTIME exec "${CONTAINER_PREFIX}-redis-cache" redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log_pass "Redis cache is healthy"
    else
        log_fail "Redis cache health check failed"
    fi

    # Check Redis queue
    if $RUNTIME exec "${CONTAINER_PREFIX}-redis-queue" redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log_pass "Redis queue is healthy"
    else
        log_fail "Redis queue health check failed"
    fi
}

# -----------------------------------------------------------------------------
# Validation: Port Bindings
# -----------------------------------------------------------------------------
validate_ports() {
    log_info "Checking port bindings (Constitution: 32300-32500)..."

    for port in "${EXPECTED_PORTS[@]}"; do
        if ss -tuln 2>/dev/null | grep -q ":${port} " || \
           netstat -tuln 2>/dev/null | grep -q ":${port} "; then
            log_pass "Port $port is bound"
        else
            log_warn "Port $port is not bound (service may not be exposed)"
        fi
    done

    # Validate no ports outside allowed range
    local bound_ports
    bound_ports=$($RUNTIME port "${CONTAINER_PREFIX}-press" 2>/dev/null | grep -oE '^[0-9]+' || echo "")

    for port in $bound_ports; do
        if [ "$port" -ge 32300 ] && [ "$port" -le 32500 ]; then
            log_pass "Port $port is within Constitution range"
        else
            log_fail "Port $port is OUTSIDE Constitution range (32300-32500)"
        fi
    done
}

# -----------------------------------------------------------------------------
# Validation: Network
# -----------------------------------------------------------------------------
validate_network() {
    log_info "Checking network configuration..."

    local network_name="${CONTAINER_PREFIX}-network"

    if $RUNTIME network ls --format '{{.Name}}' | grep -q "^${network_name}$"; then
        log_pass "Network exists: $network_name"

        # Check containers on network
        local network_containers
        network_containers=$($RUNTIME network inspect "$network_name" --format '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || echo "")

        if [ -n "$network_containers" ]; then
            log_pass "Containers connected to network"
        else
            log_warn "No containers connected to network"
        fi
    else
        log_fail "Network not found: $network_name"
    fi
}

# -----------------------------------------------------------------------------
# Validation: Volumes
# -----------------------------------------------------------------------------
validate_volumes() {
    log_info "Checking volume configuration..."

    local expected_volumes=(
        "${CONTAINER_PREFIX}-mariadb-data"
        "${CONTAINER_PREFIX}-press-sites"
        "${CONTAINER_PREFIX}-press-logs"
    )

    local existing_volumes
    existing_volumes=$($RUNTIME volume ls --format '{{.Name}}' 2>/dev/null || echo "")

    for volume in "${expected_volumes[@]}"; do
        if echo "$existing_volumes" | grep -q "^${volume}$"; then
            log_pass "Volume exists: $volume"
        else
            log_warn "Volume not found: $volume (may be created on first run)"
        fi
    done
}

# -----------------------------------------------------------------------------
# Validation: API Endpoint
# -----------------------------------------------------------------------------
validate_api() {
    log_info "Checking API endpoints..."

    local press_url="http://localhost:32300"

    # Check ping endpoint
    if curl -sf "${press_url}/api/method/ping" --max-time 10 &>/dev/null; then
        log_pass "API ping endpoint accessible"
    else
        log_warn "API ping endpoint not accessible (site may not be initialized)"
    fi

    # Check health endpoint (if implemented)
    local health_response
    health_response=$(curl -sf "${press_url}/api/method/press_selfhosted.api.health.check" --max-time 10 2>/dev/null || echo "")

    if [ -n "$health_response" ]; then
        log_pass "Health endpoint accessible"
    else
        log_warn "Health endpoint not accessible (may not be implemented yet)"
    fi
}

# -----------------------------------------------------------------------------
# Validation: Container Naming Convention
# -----------------------------------------------------------------------------
validate_naming() {
    log_info "Validating container naming convention..."

    local project_containers
    project_containers=$($RUNTIME ps -a --format '{{.Names}}' 2>/dev/null | grep "^erp-saas-cloud-c16" || echo "")

    if [ -z "$project_containers" ]; then
        log_warn "No project containers found"
        return
    fi

    while IFS= read -r container; do
        if [[ "$container" =~ ^erp-saas-cloud-c16-.+ ]]; then
            log_pass "Container naming valid: $container"
        else
            log_fail "Container naming INVALID: $container (should start with erp-saas-cloud-c16-)"
        fi
    done <<< "$project_containers"
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
print_summary() {
    echo ""
    echo "=========================================="
    echo "Quickstart Validation Summary"
    echo "=========================================="
    echo ""
    echo -e "Passed:   ${GREEN}$PASSED${NC}"
    echo -e "Failed:   ${RED}$FAILED${NC}"
    echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
    echo ""

    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ Quickstart validation PASSED${NC}"
        echo ""
        echo "Your Press Self-Hosted platform is ready!"
        echo "Access at: https://${SITE_NAME}:32443"
        return 0
    else
        echo -e "${RED}✗ Quickstart validation FAILED${NC}"
        echo ""
        echo "Please review the failed checks above."
        echo "Run 'docker compose logs' for more details."
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    echo "=========================================="
    echo "Press Self-Hosted Quickstart Validation"
    echo "=========================================="
    echo "Constitution: Container prefix erp-saas-cloud-c16-*"
    echo "Constitution: Port range 32300-32500"
    echo ""

    validate_runtime

    if [ -n "$RUNTIME" ]; then
        validate_containers
        validate_health
        validate_ports
        validate_network
        validate_volumes
        validate_api
        validate_naming
    fi

    print_summary
}

# Run main function
main "$@"
