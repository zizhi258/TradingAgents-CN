#!/bin/bash

# =============================================================================
# TradingAgents-CN Data Pipeline Production Deployment Script
# Comprehensive production deployment with monitoring and validation
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-prod}"
VERSION="${VERSION:-latest}"
REGISTRY="${REGISTRY:-local}"

# Logging
LOG_FILE="${PROJECT_ROOT}/logs/deployment_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

# Error handling
handle_error() {
    local line_number=$1
    log_error "Script failed at line $line_number"
    log_error "Check the log file for details: $LOG_FILE"
    exit 1
}

trap 'handle_error $LINENO' ERR

# =============================================================================
# Utility Functions
# =============================================================================

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "curl" "jq")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check available disk space (at least 10GB)
    local available_space=$(df / | tail -1 | awk '{print $4}')
    local required_space=$((10 * 1024 * 1024)) # 10GB in KB
    
    if [ "$available_space" -lt "$required_space" ]; then
        log_error "Insufficient disk space. At least 10GB required."
        exit 1
    fi
    
    # Check available memory (at least 8GB)
    local available_memory=$(free -k | grep MemTotal | awk '{print $2}')
    local required_memory=$((8 * 1024 * 1024)) # 8GB in KB
    
    if [ "$available_memory" -lt "$required_memory" ]; then
        log_warning "Less than 8GB memory available. Performance may be affected."
    fi
    
    log_success "Prerequisites check passed"
}

setup_environment() {
    log_info "Setting up environment..."
    
    # Create required directories
    local directories=(
        "logs"
        "data/pipeline"
        "data/quality_reports"
        "data/backups"
        "config/secrets"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "${PROJECT_ROOT}/${dir}"
    done
    
    # Set proper permissions
    chmod -R 755 "${PROJECT_ROOT}/logs"
    chmod -R 750 "${PROJECT_ROOT}/config/secrets"
    
    # Copy environment file if it doesn't exist
    if [ ! -f "${PROJECT_ROOT}/.env" ] && [ -f "${PROJECT_ROOT}/.env.example" ]; then
        log_info "Creating .env file from template..."
        cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
        log_warning "Please review and update the .env file with your configuration"
    fi
    
    log_success "Environment setup completed"
}

validate_configuration() {
    log_info "Validating configuration..."
    
    # Check if .env file exists
    if [ ! -f "${PROJECT_ROOT}/.env" ]; then
        log_error ".env file not found. Please create one based on .env.example"
        exit 1
    fi
    
    # Load environment variables
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
    
    # Validate required environment variables
    local required_vars=(
        "MONGODB_PASSWORD"
        "REDIS_PASSWORD"
        "POSTGRES_PASSWORD"
        "AIRFLOW_DB_PASSWORD"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate API keys (optional but recommended)
    local optional_vars=(
        "FINNHUB_API_KEY"
        "TUSHARE_TOKEN"
        "OPENAI_API_KEY"
    )
    
    for var in "${optional_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_warning "Optional API key $var is not set. Some features may be limited."
        fi
    done
    
    log_success "Configuration validation completed"
}

build_images() {
    log_info "Building Docker images..."
    
    # Build main application image
    log_info "Building main application image..."
    docker build \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        --build-arg VERSION="$VERSION" \
        -f "${PROJECT_ROOT}/Dockerfile.production" \
        -t "${REGISTRY}/tradingagents-cn-web:${VERSION}" \
        "${PROJECT_ROOT}"
    
    # Build API image
    log_info "Building API image..."
    docker build \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VCS_REF="$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" \
        --build-arg VERSION="$VERSION" \
        -f "${PROJECT_ROOT}/Dockerfile.api" \
        -t "${REGISTRY}/tradingagents-cn-api:${VERSION}" \
        "${PROJECT_ROOT}"
    
    log_success "Docker images built successfully"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure services..."
    
    cd "${PROJECT_ROOT}"
    
    # Deploy core infrastructure first
    log_info "Starting database services..."
    docker-compose -f docker-compose.data-pipeline.yml up -d \
        mongodb redis timescaledb zookeeper kafka
    
    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."
    
    # Wait for MongoDB
    log_info "Waiting for MongoDB..."
    local mongodb_ready=false
    for i in {1..60}; do
        if docker-compose -f docker-compose.data-pipeline.yml exec -T mongodb mongosh --eval "db.runCommand('ping')" &>/dev/null; then
            mongodb_ready=true
            break
        fi
        sleep 5
    done
    
    if [ "$mongodb_ready" != true ]; then
        log_error "MongoDB failed to start within expected time"
        exit 1
    fi
    
    # Wait for Redis
    log_info "Waiting for Redis..."
    local redis_ready=false
    for i in {1..30}; do
        if docker-compose -f docker-compose.data-pipeline.yml exec -T redis redis-cli ping &>/dev/null; then
            redis_ready=true
            break
        fi
        sleep 2
    done
    
    if [ "$redis_ready" != true ]; then
        log_error "Redis failed to start within expected time"
        exit 1
    fi
    
    # Wait for TimescaleDB
    log_info "Waiting for TimescaleDB..."
    local timescale_ready=false
    for i in {1..60}; do
        if docker-compose -f docker-compose.data-pipeline.yml exec -T timescaledb pg_isready -U postgres &>/dev/null; then
            timescale_ready=true
            break
        fi
        sleep 5
    done
    
    if [ "$timescale_ready" != true ]; then
        log_error "TimescaleDB failed to start within expected time"
        exit 1
    fi
    
    # Wait for Kafka
    log_info "Waiting for Kafka..."
    local kafka_ready=false
    for i in {1..60}; do
        if docker-compose -f docker-compose.data-pipeline.yml exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 &>/dev/null; then
            kafka_ready=true
            break
        fi
        sleep 5
    done
    
    if [ "$kafka_ready" != true ]; then
        log_error "Kafka failed to start within expected time"
        exit 1
    fi
    
    log_success "Infrastructure services deployed successfully"
}

deploy_airflow() {
    log_info "Deploying Airflow services..."
    
    cd "${PROJECT_ROOT}"
    
    # Set Airflow UID
    export AIRFLOW_UID=$(id -u)
    
    # Initialize Airflow database
    log_info "Initializing Airflow database..."
    docker-compose -f docker-compose.data-pipeline.yml --profile airflow run --rm airflow-init
    
    # Start Airflow services
    log_info "Starting Airflow services..."
    docker-compose -f docker-compose.data-pipeline.yml --profile airflow up -d \
        airflow-postgres airflow-webserver airflow-scheduler airflow-worker
    
    # Wait for Airflow webserver
    log_info "Waiting for Airflow webserver..."
    local airflow_ready=false
    for i in {1..60}; do
        if curl -f "http://localhost:${AIRFLOW_WEB_PORT:-8080}/health" &>/dev/null; then
            airflow_ready=true
            break
        fi
        sleep 5
    done
    
    if [ "$airflow_ready" != true ]; then
        log_warning "Airflow webserver not responding, but continuing deployment"
    fi
    
    log_success "Airflow services deployed"
}

deploy_application() {
    log_info "Deploying application services..."
    
    cd "${PROJECT_ROOT}"
    
    # Deploy data pipeline services
    log_info "Starting data pipeline services..."
    docker-compose -f docker-compose.data-pipeline.yml up -d \
        streaming-pipeline data-quality-monitor
    
    # Deploy main application
    log_info "Starting main application services..."
    docker-compose -f docker-compose.data-pipeline.yml up -d \
        web api
    
    # Wait for services to be ready
    log_info "Waiting for application services..."
    
    # Wait for API
    local api_ready=false
    for i in {1..30}; do
        if curl -f "http://localhost:${API_PORT:-8000}/health" &>/dev/null; then
            api_ready=true
            break
        fi
        sleep 5
    done
    
    if [ "$api_ready" != true ]; then
        log_warning "API service not responding on health check"
    fi
    
    # Wait for Web UI
    local web_ready=false
    for i in {1..30}; do
        if curl -f "http://localhost:${WEB_PORT:-8501}/health" &>/dev/null; then
            web_ready=true
            break
        fi
        sleep 5
    done
    
    if [ "$web_ready" != true ]; then
        log_warning "Web UI not responding on health check"
    fi
    
    log_success "Application services deployed"
}

deploy_monitoring() {
    log_info "Deploying monitoring services..."
    
    cd "${PROJECT_ROOT}"
    
    # Deploy monitoring stack
    docker-compose -f docker-compose.data-pipeline.yml --profile monitoring up -d \
        prometheus grafana
    
    # Wait for Prometheus
    local prometheus_ready=false
    for i in {1..30}; do
        if curl -f "http://localhost:${PROMETHEUS_PORT:-9090}/-/ready" &>/dev/null; then
            prometheus_ready=true
            break
        fi
        sleep 3
    done
    
    if [ "$prometheus_ready" != true ]; then
        log_warning "Prometheus not responding"
    fi
    
    # Wait for Grafana
    local grafana_ready=false
    for i in {1..30}; do
        if curl -f "http://localhost:${GRAFANA_PORT:-3000}/api/health" &>/dev/null; then
            grafana_ready=true
            break
        fi
        sleep 3
    done
    
    if [ "$grafana_ready" != true ]; then
        log_warning "Grafana not responding"
    fi
    
    log_success "Monitoring services deployed"
}

run_health_checks() {
    log_info "Running comprehensive health checks..."
    
    local health_check_results=()
    
    # Check service health
    local services=(
        "web:${WEB_PORT:-8501}:/health"
        "api:${API_PORT:-8000}:/health"
        "grafana:${GRAFANA_PORT:-3000}:/api/health"
        "prometheus:${PROMETHEUS_PORT:-9090}/-/ready"
    )
    
    for service_check in "${services[@]}"; do
        IFS=':' read -r service_name port path <<< "$service_check"
        
        log_info "Checking $service_name health..."
        
        if curl -f "http://localhost:${port}${path}" &>/dev/null; then
            log_success "$service_name is healthy"
            health_check_results+=("$service_name:healthy")
        else
            log_error "$service_name health check failed"
            health_check_results+=("$service_name:unhealthy")
        fi
    done
    
    # Check database connectivity
    log_info "Checking database connectivity..."
    
    # MongoDB check
    if docker-compose -f docker-compose.data-pipeline.yml exec -T mongodb mongosh --eval "db.runCommand('ping')" &>/dev/null; then
        log_success "MongoDB is accessible"
        health_check_results+=("mongodb:healthy")
    else
        log_error "MongoDB connectivity failed"
        health_check_results+=("mongodb:unhealthy")
    fi
    
    # Redis check
    if docker-compose -f docker-compose.data-pipeline.yml exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis is accessible"
        health_check_results+=("redis:healthy")
    else
        log_error "Redis connectivity failed"
        health_check_results+=("redis:unhealthy")
    fi
    
    # TimescaleDB check
    if docker-compose -f docker-compose.data-pipeline.yml exec -T timescaledb pg_isready -U postgres &>/dev/null; then
        log_success "TimescaleDB is accessible"
        health_check_results+=("timescaledb:healthy")
    else
        log_error "TimescaleDB connectivity failed"
        health_check_results+=("timescaledb:unhealthy")
    fi
    
    # Count healthy vs unhealthy services
    local healthy_count=$(printf '%s\n' "${health_check_results[@]}" | grep -c ":healthy" || true)
    local total_count=${#health_check_results[@]}
    
    log_info "Health check summary: $healthy_count/$total_count services healthy"
    
    if [ "$healthy_count" -eq "$total_count" ]; then
        log_success "All health checks passed"
        return 0
    else
        log_error "Some health checks failed"
        return 1
    fi
}

generate_deployment_report() {
    log_info "Generating deployment report..."
    
    local report_file="${PROJECT_ROOT}/deployment_report_$(date +%Y%m%d_%H%M%S).json"
    
    # Get deployment info
    local deployment_info=$(cat <<EOF
{
    "deployment": {
        "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
        "environment": "$ENVIRONMENT",
        "version": "$VERSION",
        "registry": "$REGISTRY"
    },
    "services": {
        "web": {
            "port": ${WEB_PORT:-8501},
            "status": "$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${WEB_PORT:-8501}/health || echo "unreachable")"
        },
        "api": {
            "port": ${API_PORT:-8000},
            "status": "$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${API_PORT:-8000}/health || echo "unreachable")"
        },
        "mongodb": {
            "port": ${MONGODB_PORT:-27017},
            "status": "$(docker-compose -f docker-compose.data-pipeline.yml exec -T mongodb mongosh --eval "db.runCommand('ping')" &>/dev/null && echo "healthy" || echo "unhealthy")"
        },
        "redis": {
            "port": ${REDIS_PORT:-6379},
            "status": "$(docker-compose -f docker-compose.data-pipeline.yml exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG" && echo "healthy" || echo "unhealthy")"
        },
        "timescaledb": {
            "port": ${TIMESCALEDB_PORT:-5432},
            "status": "$(docker-compose -f docker-compose.data-pipeline.yml exec -T timescaledb pg_isready -U postgres &>/dev/null && echo "healthy" || echo "unhealthy")"
        }
    },
    "urls": {
        "web_ui": "http://localhost:${WEB_PORT:-8501}",
        "api": "http://localhost:${API_PORT:-8000}",
        "grafana": "http://localhost:${GRAFANA_PORT:-3000}",
        "prometheus": "http://localhost:${PROMETHEUS_PORT:-9090}",
        "airflow": "http://localhost:${AIRFLOW_WEB_PORT:-8080}"
    },
    "next_steps": [
        "Review the deployment log: $LOG_FILE",
        "Access the web UI at http://localhost:${WEB_PORT:-8501}",
        "Monitor system health via Grafana at http://localhost:${GRAFANA_PORT:-3000}",
        "Check Airflow DAGs at http://localhost:${AIRFLOW_WEB_PORT:-8080}",
        "Review the API documentation at http://localhost:${API_PORT:-8000}/docs"
    ]
}
EOF
)
    
    echo "$deployment_info" | jq '.' > "$report_file"
    
    log_success "Deployment report generated: $report_file"
    
    # Display summary
    echo
    log_info "=== DEPLOYMENT SUMMARY ==="
    echo "$deployment_info" | jq -r '.next_steps[]' | while read -r step; do
        log_info "• $step"
    done
    echo
}

show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS] COMMAND

Commands:
    deploy          Full deployment (default)
    build           Build Docker images only
    start           Start services (assumes images exist)
    stop            Stop all services
    restart         Restart all services
    health          Run health checks only
    logs            Show service logs
    cleanup         Clean up stopped containers and unused images
    
Options:
    -e, --environment   Set environment (default: prod)
    -v, --version      Set version tag (default: latest)
    -r, --registry     Set registry (default: local)
    -h, --help         Show this help message

Examples:
    $0 deploy                           # Full deployment
    $0 -e staging deploy               # Deploy to staging environment
    $0 -v v1.2.0 build                # Build with specific version
    $0 health                          # Run health checks
    $0 logs web                        # Show web service logs

EOF
}

# =============================================================================
# Command Handlers
# =============================================================================

cmd_deploy() {
    log_info "Starting full deployment process..."
    
    check_prerequisites
    setup_environment
    validate_configuration
    build_images
    deploy_infrastructure
    deploy_airflow
    deploy_application
    deploy_monitoring
    
    log_info "Waiting for all services to stabilize..."
    sleep 30
    
    if run_health_checks; then
        generate_deployment_report
        log_success "Deployment completed successfully!"
    else
        log_error "Deployment completed with some issues. Check the logs for details."
        exit 1
    fi
}

cmd_build() {
    log_info "Building Docker images..."
    check_prerequisites
    build_images
    log_success "Build completed successfully!"
}

cmd_start() {
    log_info "Starting services..."
    cd "${PROJECT_ROOT}"
    docker-compose -f docker-compose.data-pipeline.yml up -d
    docker-compose -f docker-compose.data-pipeline.yml --profile airflow up -d
    docker-compose -f docker-compose.data-pipeline.yml --profile monitoring up -d
    log_success "Services started successfully!"
}

cmd_stop() {
    log_info "Stopping services..."
    cd "${PROJECT_ROOT}"
    docker-compose -f docker-compose.data-pipeline.yml --profile monitoring down
    docker-compose -f docker-compose.data-pipeline.yml --profile airflow down
    docker-compose -f docker-compose.data-pipeline.yml down
    log_success "Services stopped successfully!"
}

cmd_restart() {
    cmd_stop
    sleep 5
    cmd_start
}

cmd_health() {
    log_info "Running health checks..."
    if run_health_checks; then
        log_success "All health checks passed!"
    else
        log_error "Some health checks failed!"
        exit 1
    fi
}

cmd_logs() {
    local service="${1:-}"
    cd "${PROJECT_ROOT}"
    
    if [ -n "$service" ]; then
        docker-compose -f docker-compose.data-pipeline.yml logs -f "$service"
    else
        docker-compose -f docker-compose.data-pipeline.yml logs -f
    fi
}

cmd_cleanup() {
    log_info "Cleaning up Docker resources..."
    
    # Remove stopped containers
    docker container prune -f
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused volumes (be careful with this in production)
    read -p "Remove unused volumes? This may delete data! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
    fi
    
    # Remove unused networks
    docker network prune -f
    
    log_success "Cleanup completed!"
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            deploy|build|start|stop|restart|health|logs|cleanup)
                COMMAND="$1"
                shift
                break
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Default command
    COMMAND="${COMMAND:-deploy}"
    
    log_info "TradingAgents-CN Data Pipeline Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $VERSION"
    log_info "Registry: $REGISTRY"
    log_info "Command: $COMMAND"
    log_info "Log file: $LOG_FILE"
    echo
    
    # Execute command
    case $COMMAND in
        deploy)
            cmd_deploy
            ;;
        build)
            cmd_build
            ;;
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        health)
            cmd_health
            ;;
        logs)
            cmd_logs "$@"
            ;;
        cleanup)
            cmd_cleanup
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"