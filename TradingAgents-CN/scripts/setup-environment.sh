#!/bin/bash
# =============================================================================
# Environment Setup Script for TradingAgents-CN
# Automates environment configuration and secrets management
# =============================================================================

set -euo pipefail

# Default values
DEFAULT_CONFIG_DIR="config"
DEFAULT_ENVIRONMENT="development"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Help function
show_help() {
    cat << EOF
TradingAgents-CN Environment Setup Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    setup <environment>     Setup a new environment
    validate <environment>  Validate environment configuration
    export <environment>    Export environment configuration
    secrets <environment>   Update environment secrets
    list                   List available environments

Options:
    -h, --help             Show this help message
    -c, --config-dir DIR   Configuration directory (default: config)
    -f, --format FORMAT    Export format: env, json, yaml, k8s_secret (default: env)
    -o, --output FILE      Output file path
    --interactive          Interactive mode for secrets input
    --dry-run             Show what would be done without making changes

Examples:
    $0 setup development
    $0 setup production --interactive
    $0 validate staging
    $0 export production --format k8s_secret --output prod-secrets.yaml
    $0 secrets staging --interactive

EOF
}

# Parse command line arguments
parse_args() {
    CONFIG_DIR="$DEFAULT_CONFIG_DIR"
    FORMAT="env"
    OUTPUT=""
    INTERACTIVE=false
    DRY_RUN=false
    COMMAND=""
    ENVIRONMENT=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -c|--config-dir)
                CONFIG_DIR="$2"
                shift 2
                ;;
            -f|--format)
                FORMAT="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT="$2"
                shift 2
                ;;
            --interactive)
                INTERACTIVE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            setup|validate|export|secrets|list)
                COMMAND="$1"
                shift
                ;;
            *)
                if [[ -z "$ENVIRONMENT" && "$COMMAND" != "list" ]]; then
                    ENVIRONMENT="$1"
                else
                    log_error "Unknown option: $1"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Validate required arguments
    if [[ -z "$COMMAND" ]]; then
        log_error "Command is required"
        show_help
        exit 1
    fi
    
    if [[ "$COMMAND" != "list" && -z "$ENVIRONMENT" ]]; then
        log_error "Environment name is required for command: $COMMAND"
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    local missing_tools=()
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    # Check required Python packages
    if ! python3 -c "import yaml" &> /dev/null; then
        missing_tools+=("PyYAML")
    fi
    
    if ! python3 -c "import cryptography" &> /dev/null; then
        missing_tools+=("cryptography")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools/packages:"
        for tool in "${missing_tools[@]}"; do
            echo "  - $tool"
        done
        log_info "Install missing packages with: pip install PyYAML cryptography"
        exit 1
    fi
}

# Setup environment
setup_environment() {
    local env_name="$1"
    
    log_info "Setting up environment: $env_name"
    
    # Create configuration directories
    mkdir -p "$CONFIG_DIR"/{environments,secrets,templates}
    
    # Check if environment already exists
    if [[ -f "$CONFIG_DIR/environments/$env_name.yaml" ]]; then
        log_warning "Environment $env_name already exists"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Setup cancelled"
            return 0
        fi
    fi
    
    # Use config manager to create environment
    if [[ "$INTERACTIVE" == true ]]; then
        log_info "Starting interactive setup..."
        python3 "$SCRIPT_DIR/config_manager.py" create "$env_name" \
            --config-dir "$CONFIG_DIR" \
            --description "Environment created via setup script"
    else
        # Use template-based setup
        local template_file=""
        case "$env_name" in
            "development"|"dev")
                template_file="$CONFIG_DIR/environments/development.yaml"
                ;;
            "staging"|"stage")
                template_file="$CONFIG_DIR/environments/staging.yaml"
                ;;
            "production"|"prod")
                template_file="$CONFIG_DIR/environments/production.yaml"
                ;;
        esac
        
        if [[ -n "$template_file" && -f "$template_file" ]]; then
            log_info "Using existing template: $template_file"
        else
            log_info "Creating environment from base template"
            python3 "$SCRIPT_DIR/config_manager.py" create "$env_name" \
                --config-dir "$CONFIG_DIR" \
                --template "$CONFIG_DIR/templates/base_environment.json" \
                --description "Environment created via setup script"
        fi
    fi
    
    log_success "Environment $env_name created successfully"
    
    # Setup secrets if interactive mode
    if [[ "$INTERACTIVE" == true ]]; then
        log_info "Setting up secrets..."
        setup_secrets "$env_name"
    else
        log_info "Secrets can be configured later with: $0 secrets $env_name --interactive"
    fi
}

# Setup secrets for environment
setup_secrets() {
    local env_name="$1"
    
    log_info "Configuring secrets for environment: $env_name"
    
    # Create temporary secrets file
    local secrets_file="/tmp/tradingagents_secrets_$$.$RANDOM.json"
    trap "rm -f '$secrets_file'" EXIT
    
    # Collect secrets interactively
    cat > "$secrets_file" << 'EOF'
{
EOF
    
    # Database secrets
    echo "=== Database Configuration ==="
    read -p "MongoDB Username [admin]: " mongodb_user
    mongodb_user="${mongodb_user:-admin}"
    
    read -s -p "MongoDB Password (leave empty to generate): " mongodb_pass
    echo
    if [[ -z "$mongodb_pass" ]]; then
        mongodb_pass="$(openssl rand -base64 32)"
        log_info "Generated MongoDB password"
    fi
    
    read -s -p "Redis Password (leave empty to generate): " redis_pass
    echo
    if [[ -z "$redis_pass" ]]; then
        redis_pass="$(openssl rand -base64 32)"
        log_info "Generated Redis password"
    fi
    
    # AI API Keys
    echo
    echo "=== AI Model API Keys ==="
    read -p "OpenAI API Key: " openai_key
    read -p "Gemini API Key: " gemini_key
    read -p "DeepSeek API Key: " deepseek_key
    read -p "SiliconFlow API Key: " siliconflow_key
    
    # Data Provider API Keys
    echo
    echo "=== Data Provider API Keys ==="
    read -p "Tushare Token: " tushare_token
    read -p "Finnhub API Key: " finnhub_key
    read -p "Alpha Vantage API Key: " alphavantage_key
    
    # Email Configuration
    echo
    echo "=== Email Configuration ==="
    read -p "SMTP Host [smtp.gmail.com]: " smtp_host
    smtp_host="${smtp_host:-smtp.gmail.com}"
    
    read -p "SMTP Username: " smtp_user
    read -s -p "SMTP Password: " smtp_pass
    echo
    
    # Generate JWT secret
    jwt_secret="$(openssl rand -base64 64)"
    
    # Build secrets JSON
    cat > "$secrets_file" << EOF
{
  "MONGODB_USERNAME": "$mongodb_user",
  "MONGODB_PASSWORD": "$mongodb_pass",
  "REDIS_PASSWORD": "$redis_pass",
  "TRADINGAGENTS_MONGODB_URL": "mongodb://$mongodb_user:$mongodb_pass@mongodb-service:27017/tradingagents?authSource=admin",
  "TRADINGAGENTS_REDIS_URL": "redis://:$redis_pass@redis-service:6379",
  "OPENAI_API_KEY": "$openai_key",
  "GEMINI_API_KEY": "$gemini_key",
  "DEEPSEEK_API_KEY": "$deepseek_key",
  "SILICONFLOW_API_KEY": "$siliconflow_key",
  "TUSHARE_TOKEN": "$tushare_token",
  "FINNHUB_API_KEY": "$finnhub_key",
  "ALPHA_VANTAGE_API_KEY": "$alphavantage_key",
  "SMTP_HOST": "$smtp_host",
  "SMTP_USERNAME": "$smtp_user",
  "SMTP_PASSWORD": "$smtp_pass",
  "JWT_SECRET_KEY": "$jwt_secret"
}
EOF
    
    # Update secrets using config manager
    if [[ "$DRY_RUN" == true ]]; then
        log_info "Would update secrets for environment: $env_name"
        log_info "Secrets file: $secrets_file"
    else
        python3 "$SCRIPT_DIR/config_manager.py" secrets "$env_name" \
            --config-dir "$CONFIG_DIR" \
            --file "$secrets_file"
        
        log_success "Secrets configured for environment: $env_name"
    fi
    
    # Cleanup
    rm -f "$secrets_file"
}

# Validate environment configuration
validate_environment() {
    local env_name="$1"
    
    log_info "Validating environment: $env_name"
    
    python3 "$SCRIPT_DIR/config_manager.py" validate "$env_name" \
        --config-dir "$CONFIG_DIR"
    
    if [[ $? -eq 0 ]]; then
        log_success "Environment $env_name is valid"
    else
        log_error "Environment $env_name validation failed"
        exit 1
    fi
}

# Export environment configuration
export_environment() {
    local env_name="$1"
    
    log_info "Exporting environment: $env_name (format: $FORMAT)"
    
    local export_args=(
        "$env_name"
        --config-dir "$CONFIG_DIR"
        --format "$FORMAT"
    )
    
    if [[ -n "$OUTPUT" ]]; then
        export_args+=(--output "$OUTPUT")
        log_info "Output will be saved to: $OUTPUT"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "Would export environment $env_name with format $FORMAT"
        return 0
    fi
    
    python3 "$SCRIPT_DIR/config_manager.py" export "${export_args[@]}"
    
    if [[ $? -eq 0 ]]; then
        log_success "Environment $env_name exported successfully"
    else
        log_error "Failed to export environment $env_name"
        exit 1
    fi
}

# List environments
list_environments() {
    log_info "Available environments:"
    
    python3 "$SCRIPT_DIR/config_manager.py" list \
        --config-dir "$CONFIG_DIR"
}

# Main execution function
main() {
    parse_args "$@"
    check_prerequisites
    
    case "$COMMAND" in
        setup)
            setup_environment "$ENVIRONMENT"
            ;;
        validate)
            validate_environment "$ENVIRONMENT"
            ;;
        export)
            export_environment "$ENVIRONMENT"
            ;;
        secrets)
            setup_secrets "$ENVIRONMENT"
            ;;
        list)
            list_environments
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"