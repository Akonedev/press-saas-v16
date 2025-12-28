#!/bin/bash
# =============================================================================
# Development SSL Certificates Setup - ERP SaaS Cloud PRESSE v16
# =============================================================================
# This script sets up mkcert for local development SSL certificates
# Constitution Constraint: Part of erp-saas-cloud-c16 infrastructure
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
CERT_DIR="$(dirname "$0")/../docker/config/traefik/acme"
DOMAINS=(
    "press.platform.local"
    "*.platform.local"
    "localhost"
)

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

# -----------------------------------------------------------------------------
# Check mkcert Installation
# -----------------------------------------------------------------------------
check_mkcert() {
    log_info "Checking mkcert installation..."

    if command -v mkcert &> /dev/null; then
        log_success "mkcert is installed"
        return 0
    fi

    log_warning "mkcert is not installed"
    return 1
}

# -----------------------------------------------------------------------------
# Install mkcert
# -----------------------------------------------------------------------------
install_mkcert() {
    log_info "Installing mkcert..."

    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            log_info "Installing mkcert via apt..."
            sudo apt-get update
            sudo apt-get install -y libnss3-tools
            wget -O mkcert https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
            chmod +x mkcert
            sudo mv mkcert /usr/local/bin/
        elif command -v dnf &> /dev/null; then
            # Fedora
            log_info "Installing mkcert via dnf..."
            sudo dnf install -y mkcert
        elif command -v pacman &> /dev/null; then
            # Arch
            log_info "Installing mkcert via pacman..."
            sudo pacman -S mkcert
        else
            log_error "Unsupported package manager"
            return 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        log_info "Installing mkcert via Homebrew..."
        brew install mkcert
    else
        log_error "Unsupported operating system: $OSTYPE"
        return 1
    fi

    log_success "mkcert installed"
}

# -----------------------------------------------------------------------------
# Setup Local CA
# -----------------------------------------------------------------------------
setup_ca() {
    log_info "Setting up local Certificate Authority..."

    # Install local CA
    mkcert -install

    log_success "Local CA installed"
}

# -----------------------------------------------------------------------------
# Generate Certificates
# -----------------------------------------------------------------------------
generate_certificates() {
    log_info "Generating SSL certificates for development..."

    # Create cert directory if it doesn't exist
    mkdir -p "$CERT_DIR"

    # Generate certificates
    cd "$CERT_DIR"

    log_info "Generating certificate for: ${DOMAINS[*]}"

    mkcert -cert-file cert.pem -key-file key.pem "${DOMAINS[@]}"

    # Set correct permissions
    chmod 600 key.pem
    chmod 644 cert.pem

    log_success "Certificates generated in $CERT_DIR"
}

# -----------------------------------------------------------------------------
# Update Traefik Configuration
# -----------------------------------------------------------------------------
update_traefik_config() {
    log_info "Updating Traefik configuration for dev certificates..."

    local traefik_config="$(dirname "$0")/../docker/config/traefik/dynamic/dev-certs.yml"

    cat > "$traefik_config" << 'EOF'
# =============================================================================
# Development Certificates Configuration
# =============================================================================
# This file configures Traefik to use mkcert certificates for development
# =============================================================================

tls:
  certificates:
    - certFile: /etc/traefik/acme/cert.pem
      keyFile: /etc/traefik/acme/key.pem
      stores:
        - default

  stores:
    default:
      defaultCertificate:
        certFile: /etc/traefik/acme/cert.pem
        keyFile: /etc/traefik/acme/key.pem
EOF

    log_success "Traefik dev certificates configuration created"
}

# -----------------------------------------------------------------------------
# Add Hosts Entries
# -----------------------------------------------------------------------------
add_hosts_entries() {
    log_info "Adding hosts entries..."

    local hosts_file="/etc/hosts"
    local hosts_entries=(
        "127.0.0.1 press.platform.local"
        "127.0.0.1 tenant1.platform.local"
        "127.0.0.1 tenant2.platform.local"
        "127.0.0.1 traefik.platform.local"
    )

    log_warning "You may need to add these entries to $hosts_file:"
    echo ""

    for entry in "${hosts_entries[@]}"; do
        if grep -q "$entry" "$hosts_file" 2>/dev/null; then
            log_success "  $entry (already exists)"
        else
            echo "  $entry"
        fi
    done

    echo ""
    log_info "To add them automatically, run:"
    echo "  sudo tee -a $hosts_file > /dev/null << EOF"
    for entry in "${hosts_entries[@]}"; do
        if ! grep -q "$entry" "$hosts_file" 2>/dev/null; then
            echo "$entry"
        fi
    done
    echo "EOF"
    echo ""
}

# -----------------------------------------------------------------------------
# Verify Setup
# -----------------------------------------------------------------------------
verify_setup() {
    log_info "Verifying certificate setup..."

    if [[ -f "$CERT_DIR/cert.pem" ]] && [[ -f "$CERT_DIR/key.pem" ]]; then
        log_success "Certificate files exist"

        # Check certificate details
        log_info "Certificate details:"
        openssl x509 -in "$CERT_DIR/cert.pem" -noout -subject -dates 2>/dev/null || true
    else
        log_error "Certificate files not found"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    echo "=========================================="
    echo "Development SSL Certificates Setup"
    echo "=========================================="
    echo ""

    # Check if mkcert is installed
    if ! check_mkcert; then
        read -p "Install mkcert? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_mkcert
        else
            log_error "mkcert is required for this script"
            exit 1
        fi
    fi

    # Setup local CA
    setup_ca

    # Generate certificates
    generate_certificates

    # Update Traefik config
    update_traefik_config

    # Add hosts entries
    add_hosts_entries

    # Verify setup
    verify_setup

    echo ""
    echo "=========================================="
    echo -e "${GREEN}Setup Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "Your development SSL certificates are ready."
    echo ""
    echo "Next steps:"
    echo "1. Add the hosts entries shown above to /etc/hosts"
    echo "2. Start Traefik: docker compose up -d traefik"
    echo "3. Access Press: https://press.platform.local:32443"
    echo ""
    echo "Note: These certificates are only trusted on this machine."
    echo "For production, use Let's Encrypt (automatic with Traefik)."
    echo ""
}

# Run main function
main "$@"
