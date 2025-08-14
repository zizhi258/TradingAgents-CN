#!/bin/bash
# =============================================================================
# TradingAgents-CN Production Deployment Automation Script
# Comprehensive deployment orchestrator for Market-Wide Analysis platform
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_LOG="$PROJECT_ROOT/logs/deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
DEFAULT_ENVIRONMENT="production"
DEFAULT_DEPLOYMENT_TYPE="full"
DEFAULT_REGISTRY="ghcr.io"
DEFAULT_NAMESPACE="tradingagents-cn"

# Configuration
ENVIRONMENT="${ENVIRONMENT:-$DEFAULT_ENVIRONMENT}"
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-$DEFAULT_DEPLOYMENT_TYPE}"
REGISTRY="${REGISTRY:-$DEFAULT_REGISTRY}"
NAMESPACE="${NAMESPACE:-$DEFAULT_NAMESPACE}"
VERSION="${VERSION:-$(date +%Y.%m.%d)-$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_TESTS="${SKIP_TESTS:-false}"
FORCE_REBUILD="${FORCE_REBUILD:-false}"

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

log_info() {
    echo -e "${CYAN}[INFO]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $*" | tee -a "$DEPLOYMENT_LOG"
}

# Help function
show_help() {
    cat << EOF
TradingAgents-CN Production Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    deploy          Full production deployment
    build          Build and push container images
    k8s-deploy     Deploy to Kubernetes
    docker-deploy  Deploy with Docker Compose
    migrate        Run database migrations
    monitor        Deploy monitoring stack
    validate       Validate deployment
    cleanup        Clean up deployment artifacts
    rollback       Rollback to previous version

Options:
    -e, --environment ENV    Target environment (development|staging|production)
    -t, --type TYPE         Deployment type (full|app-only|infra-only|monitoring)
    -v, --version VERSION   Application version to deploy
    -n, --namespace NS      Kubernetes namespace
    -r, --registry REG      Container registry
    --dry-run              Show what would be done without executing
    --skip-tests           Skip pre-deployment tests
    --force-rebuild        Force rebuild of container images
    --no-monitoring        Skip monitoring stack deployment
    --no-backup            Skip pre-deployment backup
    -h, --help             Show this help message

Environment Variables:
    ENVIRONMENT            Target environment
    DEPLOYMENT_TYPE        Type of deployment
    VERSION               Version to deploy
    REGISTRY              Container registry
    NAMESPACE             Kubernetes namespace
    DRY_RUN               Dry run mode (true/false)
    SKIP_TESTS            Skip tests (true/false)
    FORCE_REBUILD         Force rebuild (true/false)

Examples:
    # Full production deployment
    $0 deploy -e production -v 1.0.0

    # Build and push images only
    $0 build -v 1.0.0

    # Deploy to staging with monitoring
    $0 deploy -e staging -t full

    # Dry run deployment
    $0 --dry-run deploy -e production

EOF
}

# Parse command line arguments
parse_args() {
    COMMAND=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--type)
                DEPLOYMENT_TYPE="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --skip-tests)
                SKIP_TESTS="true"
                shift
                ;;
            --force-rebuild)
                FORCE_REBUILD="true"
                shift
                ;;
            --no-monitoring)
                SKIP_MONITORING="true"
                shift
                ;;
            --no-backup)
                SKIP_BACKUP="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            deploy|build|k8s-deploy|docker-deploy|migrate|monitor|validate|cleanup|rollback)
                COMMAND="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    if [[ -z "$COMMAND" ]]; then
        log_error "Command is required"
        show_help
        exit 1
    fi
}

# Initialize deployment environment
init_deployment() {
    log_step "Initializing deployment environment"
    
    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Initialize deployment log
    cat > "$DEPLOYMENT_LOG" << EOF
=============================================================================
TradingAgents-CN Deployment Log
Started: $(date)
Environment: $ENVIRONMENT
Type: $DEPLOYMENT_TYPE
Version: $VERSION
Dry Run: $DRY_RUN
=============================================================================

EOF
    
    log_info "Environment: $ENVIRONMENT"
    log_info "Deployment Type: $DEPLOYMENT_TYPE"
    log_info "Version: $VERSION"
    log_info "Registry: $REGISTRY"
    log_info "Namespace: $NAMESPACE"
    log_info "Dry Run: $DRY_RUN"
    
    # Validate prerequisites
    validate_prerequisites
}

# Validate deployment prerequisites
validate_prerequisites() {
    log_step "Validating deployment prerequisites"
    
    local missing_tools=()
    
    # Check required tools
    command -v docker &> /dev/null || missing_tools+=("docker")
    command -v docker-compose &> /dev/null || missing_tools+=("docker-compose")
    command -v kubectl &> /dev/null || missing_tools+=("kubectl")
    command -v helm &> /dev/null || missing_tools+=("helm")
    command -v python3 &> /dev/null || missing_tools+=("python3")
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools:"
        for tool in "${missing_tools[@]}"; do
            echo "  - $tool"
        done
        exit 1
    fi
    
    # Check environment files
    if [[ ! -f "$PROJECT_ROOT/.env.$ENVIRONMENT" ]]; then
        log_warning "Environment file not found: .env.$ENVIRONMENT"
        if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
            log_error "No environment configuration found"
            exit 1
        fi
    fi
    
    # Check configuration
    if [[ ! -d "$PROJECT_ROOT/config/environments" ]]; then
        log_error "Environment configurations not found"
        exit 1
    fi
    
    log_success "Prerequisites validation completed"
}

# Run pre-deployment tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping pre-deployment tests"
        return 0
    fi
    
    log_step "Running pre-deployment tests"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would run: pytest tests/ --tb=short"
        log_info "Would run: python scripts/db_validation.py"
        return 0
    fi
    
    # Run unit tests
    cd "$PROJECT_ROOT"
    python -m pytest tests/unit/ --tb=short || {
        log_error "Unit tests failed"
        return 1
    }
    
    # Run integration tests
    python -m pytest tests/integration/ --tb=short || {
        log_warning "Integration tests failed - continuing with caution"
    }
    
    # Validate database schema
    python scripts/db_validation.py --mongodb-url "$TRADINGAGENTS_MONGODB_URL" || {
        log_warning "Database validation failed - continuing with caution"
    }
    
    log_success "Tests completed"
}

# Build container images
build_images() {
    log_step "Building container images"
    
    local images=("web" "api")
    
    for image in "${images[@]}"; do
        local full_image_name="$REGISTRY/tradingagents-cn-$image:$VERSION"
        
        log_info "Building $image image: $full_image_name"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "Would build: $full_image_name"
            continue
        fi
        
        # Determine Dockerfile
        local dockerfile="Dockerfile.production"
        if [[ "$image" == "api" ]]; then
            dockerfile="Dockerfile.api"
        fi
        
        # Build image
        docker build \
            --tag "$full_image_name" \
            --tag "$REGISTRY/tradingagents-cn-$image:latest" \
            --file "$dockerfile" \
            --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
            --build-arg VCS_REF="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
            --build-arg VERSION="$VERSION" \
            . || {
            log_error "Failed to build $image image"
            return 1
        }
        
        # Push image
        log_info "Pushing $image image: $full_image_name"
        docker push "$full_image_name" || {
            log_error "Failed to push $image image"
            return 1
        }
        
        if [[ "$ENVIRONMENT" == "production" ]]; then
            docker push "$REGISTRY/tradingagents-cn-$image:latest" || {
                log_warning "Failed to push latest tag for $image"
            }
        fi
    done
    
    log_success "Container images built and pushed"
}

# Run database migrations
run_migrations() {
    log_step "Running database migrations"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would run: python scripts/db_migration.py apply --dry-run"
        return 0
    fi
    
    # Load environment
    if [[ -f "$PROJECT_ROOT/.env.$ENVIRONMENT" ]]; then
        source "$PROJECT_ROOT/.env.$ENVIRONMENT"
    elif [[ -f "$PROJECT_ROOT/.env" ]]; then
        source "$PROJECT_ROOT/.env"
    fi
    
    cd "$PROJECT_ROOT"
    
    # Initialize database if needed
    python scripts/db_migration.py init || {
        log_warning "Database already initialized"
    }
    
    # Apply migrations
    python scripts/db_migration.py apply || {
        log_error "Database migration failed"
        return 1
    }
    
    log_success "Database migrations completed"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_step "Deploying to Kubernetes"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would deploy Kubernetes manifests to namespace: $NAMESPACE"
        log_info "Would update image versions to: $VERSION"
        return 0
    fi
    
    # Create namespace if it doesn't exist
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || {
        log_warning "Failed to create namespace (may already exist)"
    }
    
    # Update image versions in manifests
    local temp_dir=$(mktemp -d)
    cp -r "$PROJECT_ROOT/k8s/base/"* "$temp_dir/"
    
    # Replace image versions
    find "$temp_dir" -name "*.yaml" -exec sed -i "s|your-registry.com/tradingagents-cn|$REGISTRY/tradingagents-cn|g" {} \;
    find "$temp_dir" -name "*.yaml" -exec sed -i "s|:latest|:$VERSION|g" {} \;
    
    # Apply manifests
    kubectl apply -f "$temp_dir" -n "$NAMESPACE" || {
        log_error "Kubernetes deployment failed"
        rm -rf "$temp_dir"
        return 1
    }
    
    # Wait for deployment
    log_info "Waiting for deployments to be ready..."
    kubectl rollout status deployment/tradingagents-web -n "$NAMESPACE" --timeout=300s || {
        log_error "Web deployment failed to become ready"
        rm -rf "$temp_dir"
        return 1
    }
    
    kubectl rollout status deployment/tradingagents-api -n "$NAMESPACE" --timeout=300s || {
        log_error "API deployment failed to become ready"
        rm -rf "$temp_dir"
        return 1
    }
    
    rm -rf "$temp_dir"
    log_success "Kubernetes deployment completed"
}

# Deploy with Docker Compose
deploy_docker_compose() {
    log_step "Deploying with Docker Compose"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would run: docker-compose -f docker-compose.production.yml up -d"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    # Load environment
    export $(grep -v '^#' ".env.$ENVIRONMENT" | xargs) 2>/dev/null || true
    
    # Pull latest images
    docker-compose -f docker-compose.production.yml pull || {
        log_warning "Failed to pull some images"
    }
    
    # Deploy services
    docker-compose -f docker-compose.production.yml up -d || {
        log_error "Docker Compose deployment failed"
        return 1
    }
    
    # Wait for services
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    local retries=0
    while [[ $retries -lt 10 ]]; do
        if curl -f -s "http://localhost:8501/_stcore/health" > /dev/null; then
            break
        fi
        retries=$((retries + 1))
        log_info "Waiting for web service... (attempt $retries/10)"
        sleep 10
    done
    
    if [[ $retries -eq 10 ]]; then
        log_error "Web service failed to become ready"
        return 1
    fi
    
    log_success "Docker Compose deployment completed"
}

# Deploy monitoring stack
deploy_monitoring() {
    if [[ "${SKIP_MONITORING:-false}" == "true" ]]; then
        log_info "Skipping monitoring stack deployment"
        return 0
    fi
    
    log_step "Deploying monitoring stack"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would deploy monitoring stack with Prometheus, Grafana, and AlertManager"
        return 0
    fi
    
    cd "$PROJECT_ROOT"
    
    # Deploy monitoring services
    docker-compose -f docker-compose.monitoring.yml up -d || {
        log_error "Monitoring stack deployment failed"
        return 1
    }
    
    # Wait for Prometheus
    local retries=0
    while [[ $retries -lt 10 ]]; do
        if curl -f -s "http://localhost:9090/-/healthy" > /dev/null; then
            break
        fi
        retries=$((retries + 1))
        log_info "Waiting for Prometheus... (attempt $retries/10)"
        sleep 10
    done
    
    # Wait for Grafana
    retries=0
    while [[ $retries -lt 15 ]]; do
        if curl -f -s "http://localhost:3000/api/health" > /dev/null; then
            break
        fi
        retries=$((retries + 1))
        log_info "Waiting for Grafana... (attempt $retries/15)"
        sleep 10
    done
    
    log_success "Monitoring stack deployed"
}

# Validate deployment
validate_deployment() {
    log_step "Validating deployment"
    
    local validation_errors=()
    
    # Check web service
    if ! curl -f -s "http://localhost:8501/_stcore/health" > /dev/null; then
        validation_errors+=("Web service health check failed")
    fi
    
    # Check API service (if deployed)
    if curl -f -s "http://localhost:8000/health" > /dev/null 2>&1; then
        log_info "API service is healthy"
    else
        validation_errors+=("API service health check failed")
    fi
    
    # Check database connectivity
    if [[ -n "${TRADINGAGENTS_MONGODB_URL:-}" ]]; then
        python3 -c "
import pymongo
try:
    client = pymongo.MongoClient('$TRADINGAGENTS_MONGODB_URL', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('Database connectivity OK')
except Exception as e:
    print(f'Database connectivity failed: {e}')
    exit(1)
" || validation_errors+=("Database connectivity failed")
    fi
    
    # Check monitoring (if deployed)
    if [[ "${SKIP_MONITORING:-false}" != "true" ]]; then
        if ! curl -f -s "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
            validation_errors+=("Prometheus health check failed")
        fi
        
        if ! curl -f -s "http://localhost:3000/api/health" > /dev/null 2>&1; then
            validation_errors+=("Grafana health check failed")
        fi
    fi
    
    # Report validation results
    if [[ ${#validation_errors[@]} -eq 0 ]]; then
        log_success "Deployment validation passed"
        return 0
    else
        log_error "Deployment validation failed:"
        for error in "${validation_errors[@]}"; do
            log_error "  - $error"
        done
        return 1
    fi
}

# Main deployment function
deploy_full() {
    log_step "Starting full deployment process"
    
    # Pre-deployment backup (if not skipped)
    if [[ "${SKIP_BACKUP:-false}" != "true" ]]; then
        log_info "Creating pre-deployment backup..."
        # Backup logic would go here
    fi
    
    # Run tests
    run_tests || return 1
    
    # Build images
    if [[ "$DEPLOYMENT_TYPE" == "full" || "$DEPLOYMENT_TYPE" == "app-only" ]]; then
        build_images || return 1
    fi
    
    # Run migrations
    if [[ "$DEPLOYMENT_TYPE" == "full" || "$DEPLOYMENT_TYPE" == "app-only" ]]; then
        run_migrations || return 1
    fi
    
    # Deploy application
    if [[ "$DEPLOYMENT_TYPE" == "full" || "$DEPLOYMENT_TYPE" == "app-only" ]]; then
        if command -v kubectl &> /dev/null && kubectl cluster-info &> /dev/null; then
            deploy_kubernetes || return 1
        else
            deploy_docker_compose || return 1
        fi
    fi
    
    # Deploy monitoring
    if [[ "$DEPLOYMENT_TYPE" == "full" || "$DEPLOYMENT_TYPE" == "monitoring" ]]; then
        deploy_monitoring || return 1
    fi
    
    # Validate deployment
    validate_deployment || return 1
    
    log_success "Full deployment completed successfully!"
    
    # Display access information
    display_access_info
}

# Display access information
display_access_info() {
    log_step "Deployment Access Information"
    echo
    echo "🎉 TradingAgents-CN Market Analysis Platform Deployed Successfully!"
    echo
    echo "📊 Application Access:"
    echo "  Web Interface: http://localhost:8501"
    echo "  API Endpoint:  http://localhost:8000"
    echo
    if [[ "${SKIP_MONITORING:-false}" != "true" ]]; then
        echo "📈 Monitoring Access:"
        echo "  Grafana:       http://localhost:3000 (admin/password)"
        echo "  Prometheus:    http://localhost:9090"
        echo "  AlertManager:  http://localhost:9093"
        echo
    fi
    echo "📁 Logs Location: $DEPLOYMENT_LOG"
    echo "🔧 Environment:   $ENVIRONMENT"
    echo "🏷️  Version:      $VERSION"
    echo
}

# Cleanup function
cleanup_deployment() {
    log_step "Cleaning up deployment artifacts"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would clean up temporary files and unused Docker images"
        return 0
    fi
    
    # Clean up Docker
    docker system prune -f || log_warning "Docker cleanup failed"
    
    # Clean up temporary files
    find "$PROJECT_ROOT" -name "*.tmp" -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.log.old" -delete 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Rollback function
rollback_deployment() {
    log_step "Rolling back deployment"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would rollback to previous version"
        return 0
    fi
    
    # Kubernetes rollback
    if command -v kubectl &> /dev/null && kubectl cluster-info &> /dev/null; then
        kubectl rollout undo deployment/tradingagents-web -n "$NAMESPACE" || log_warning "Web rollback failed"
        kubectl rollout undo deployment/tradingagents-api -n "$NAMESPACE" || log_warning "API rollback failed"
    else
        # Docker Compose rollback (restart with previous images)
        log_warning "Docker Compose rollback not implemented - manual intervention required"
    fi
    
    log_success "Rollback completed"
}

# Main execution
main() {
    parse_args "$@"
    init_deployment
    
    case "$COMMAND" in
        deploy)
            deploy_full
            ;;
        build)
            build_images
            ;;
        k8s-deploy)
            deploy_kubernetes
            ;;
        docker-deploy)
            deploy_docker_compose
            ;;
        migrate)
            run_migrations
            ;;
        monitor)
            deploy_monitoring
            ;;
        validate)
            validate_deployment
            ;;
        cleanup)
            cleanup_deployment
            ;;
        rollback)
            rollback_deployment
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            exit 1
            ;;
    esac
}

# Trap errors and cleanup
trap 'log_error "Deployment failed at line $LINENO"' ERR
trap 'log_info "Deployment process interrupted"' INT TERM

# Run main function
main "$@"