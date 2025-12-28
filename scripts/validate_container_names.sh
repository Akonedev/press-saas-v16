#!/bin/bash
# =============================================================================
# validate_container_names.sh - Validate container naming convention
# =============================================================================
# Constitution Constraint: All containers MUST use prefix erp-saas-cloud-c16-
# This script validates that all running containers follow this convention
# =============================================================================

set -euo pipefail

# Configuration
REQUIRED_PREFIX="erp-saas-cloud-c16-"
COMPOSE_DIR="${COMPOSE_DIR:-docker/compose}"
EXIT_CODE=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect container runtime (docker or podman)
detect_runtime() {
    if command -v docker &> /dev/null; then
        echo "docker"
    elif command -v podman &> /dev/null; then
        echo "podman"
    else
        log_error "Neither docker nor podman found"
        exit 1
    fi
}

# Validate container name against prefix
validate_container_name() {
    local name="$1"
    if [[ "$name" == ${REQUIRED_PREFIX}* ]]; then
        return 0
    else
        return 1
    fi
}

# Check running containers
check_running_containers() {
    local runtime="$1"
    log_info "Checking running containers with $runtime..."

    local containers
    containers=$($runtime ps --format '{{.Names}}' 2>/dev/null || true)

    if [[ -z "$containers" ]]; then
        log_info "No running containers found"
        return 0
    fi

    local invalid_count=0
    local valid_count=0

    while IFS= read -r container; do
        if validate_container_name "$container"; then
            log_info "✓ Valid: $container"
            ((valid_count++))
        else
            log_error "✗ Invalid prefix: $container (expected prefix: $REQUIRED_PREFIX)"
            ((invalid_count++))
            EXIT_CODE=1
        fi
    done <<< "$containers"

    echo ""
    log_info "Summary: $valid_count valid, $invalid_count invalid"
}

# Check compose files for container_name definitions
check_compose_files() {
    log_info "Checking compose files in $COMPOSE_DIR..."

    if [[ ! -d "$COMPOSE_DIR" ]]; then
        log_warn "Compose directory not found: $COMPOSE_DIR"
        return 0
    fi

    local invalid_count=0
    local valid_count=0

    # Find all YAML files
    while IFS= read -r -d '' file; do
        # Extract container_name values
        local names
        names=$(grep -E '^\s*container_name:\s*' "$file" 2>/dev/null | sed 's/.*container_name:\s*//' | tr -d '"' | tr -d "'" || true)

        if [[ -z "$names" ]]; then
            continue
        fi

        while IFS= read -r name; do
            # Skip if it's a variable reference
            if [[ "$name" == *'${'* ]] || [[ "$name" == *'$('* ]]; then
                log_info "⚠ Variable reference in $file: $name (manual check required)"
                continue
            fi

            if validate_container_name "$name"; then
                log_info "✓ Valid in $file: $name"
                ((valid_count++))
            else
                log_error "✗ Invalid prefix in $file: $name"
                ((invalid_count++))
                EXIT_CODE=1
            fi
        done <<< "$names"
    done < <(find "$COMPOSE_DIR" -name "*.yml" -o -name "*.yaml" -print0 2>/dev/null)

    echo ""
    log_info "Compose files summary: $valid_count valid, $invalid_count invalid"
}

# Check port range compliance
check_port_range() {
    local runtime="$1"
    local min_port=32300
    local max_port=32500

    log_info "Checking port range compliance (${min_port}-${max_port})..."

    local ports
    ports=$($runtime ps --format '{{.Ports}}' 2>/dev/null | grep -oE ':[0-9]+' | tr -d ':' | sort -u || true)

    if [[ -z "$ports" ]]; then
        log_info "No exposed ports found"
        return 0
    fi

    local invalid_count=0
    local valid_count=0

    while IFS= read -r port; do
        if [[ -n "$port" ]] && [[ "$port" =~ ^[0-9]+$ ]]; then
            if [[ "$port" -ge "$min_port" ]] && [[ "$port" -le "$max_port" ]]; then
                log_info "✓ Valid port: $port"
                ((valid_count++))
            else
                # Check if it's an internal port (not host-mapped)
                if [[ "$port" -lt 1024 ]] || [[ "$port" -gt 65535 ]]; then
                    continue
                fi
                log_error "✗ Port outside allowed range: $port"
                ((invalid_count++))
                EXIT_CODE=1
            fi
        fi
    done <<< "$ports"

    echo ""
    log_info "Port summary: $valid_count valid, $invalid_count invalid"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    echo "=============================================="
    echo "Container Naming Convention Validator"
    echo "Required prefix: $REQUIRED_PREFIX"
    echo "Allowed port range: 32300-32500"
    echo "=============================================="
    echo ""

    local runtime
    runtime=$(detect_runtime)
    log_info "Using container runtime: $runtime"
    echo ""

    # Run validations
    check_running_containers "$runtime"
    echo ""
    check_compose_files
    echo ""
    check_port_range "$runtime"

    echo ""
    echo "=============================================="
    if [[ $EXIT_CODE -eq 0 ]]; then
        log_info "All validations passed!"
    else
        log_error "Some validations failed. Please fix the issues above."
    fi
    echo "=============================================="

    exit $EXIT_CODE
}

# Run main function
main "$@"
