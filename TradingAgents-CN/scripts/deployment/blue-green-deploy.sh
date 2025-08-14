# =============================================================================
# Blue-Green Deployment Script for Zero-Downtime Deployments
# Supports multiple environments with comprehensive safety checks
# =============================================================================

#!/bin/bash

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="tradingagents-cn"
DEFAULT_NAMESPACE="tradingagents-cn"
DEFAULT_TIMEOUT=600

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $1" >&2
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $0 <environment> <image_tag> [options]

Blue-Green Deployment Script for TradingAgents-CN

Arguments:
  environment    Target environment (development|staging|production)
  image_tag      Docker image tag to deploy (e.g., v1.2.3, latest, commit-sha)

Options:
  -n, --namespace NAMESPACE    Kubernetes namespace (default: tradingagents-cn)
  -t, --timeout SECONDS       Deployment timeout in seconds (default: 600)
  -s, --skip-checks           Skip pre-deployment checks
  -d, --debug                 Enable debug logging
  -h, --help                  Show this help message
  --dry-run                   Show what would be deployed without executing
  --force                     Skip confirmation prompts
  --rollback-on-failure       Automatically rollback on deployment failure

Examples:
  $0 production v1.2.3
  $0 staging commit-abc123 --debug
  $0 production v1.2.3 --namespace tradingagents-cn --timeout 900
  $0 staging latest --dry-run

Environment Variables:
  KUBECONFIG      Path to kubectl config file
  DEBUG           Enable debug logging (true/false)
  SLACK_WEBHOOK   Slack webhook URL for notifications

EOF
}

# Parse command line arguments
parse_arguments() {
    if [[ $# -lt 2 ]]; then
        log_error "Missing required arguments"
        usage
        exit 1
    fi

    ENVIRONMENT="$1"
    IMAGE_TAG="$2"
    shift 2

    # Set defaults
    NAMESPACE="${DEFAULT_NAMESPACE}"
    TIMEOUT="${DEFAULT_TIMEOUT}"
    SKIP_CHECKS=false
    DRY_RUN=false
    FORCE=false
    ROLLBACK_ON_FAILURE=false

    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -s|--skip-checks)
                SKIP_CHECKS=true
                shift
                ;;
            -d|--debug)
                DEBUG=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --rollback-on-failure)
                ROLLBACK_ON_FAILURE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate environment
    case "$ENVIRONMENT" in
        development|staging|production)
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT. Must be development, staging, or production."
            exit 1
            ;;
    esac

    log_debug "Parsed arguments: ENVIRONMENT=$ENVIRONMENT, IMAGE_TAG=$IMAGE_TAG, NAMESPACE=$NAMESPACE, TIMEOUT=$TIMEOUT"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check required commands
    local required_commands=("kubectl" "docker" "jq" "curl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done

    # Check kubectl connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Check KUBECONFIG."
        exit 1
    fi

    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi

    # Verify image exists (skip for dry-run)
    if [[ "$DRY_RUN" != "true" ]]; then
        local web_image="ghcr.io/yourusername/${PROJECT_NAME}-web:${IMAGE_TAG}"
        local api_image="ghcr.io/yourusername/${PROJECT_NAME}-api:${IMAGE_TAG}"
        
        log_info "Verifying container images exist..."
        if ! docker manifest inspect "$web_image" &> /dev/null; then
            log_error "Web image not found: $web_image"
            exit 1
        fi
        if ! docker manifest inspect "$api_image" &> /dev/null; then
            log_error "API image not found: $api_image"
            exit 1
        fi
    fi

    log_success "Prerequisites check passed"
}

# Pre-deployment checks
pre_deployment_checks() {
    if [[ "$SKIP_CHECKS" == "true" ]]; then
        log_warning "Skipping pre-deployment checks"
        return 0
    fi

    log_info "Running pre-deployment checks..."

    # Check cluster resources
    local nodes_ready
    nodes_ready=$(kubectl get nodes --no-headers | grep -c "Ready" || echo "0")
    if [[ "$nodes_ready" -lt 2 ]]; then
        log_error "Insufficient ready nodes: $nodes_ready (minimum: 2)"
        exit 1
    fi

    # Check persistent volumes
    local pv_status
    pv_status=$(kubectl get pv --no-headers | grep -c "Available\|Bound" || echo "0")
    if [[ "$pv_status" -lt 3 ]]; then
        log_error "Insufficient available persistent volumes: $pv_status (minimum: 3)"
        exit 1
    fi

    # Check database connectivity
    log_info "Checking database connectivity..."
    if ! kubectl exec -n "$NAMESPACE" deployment/tradingagents-api -- python -c "
import os, pymongo, redis
try:
    # MongoDB check
    client = pymongo.MongoClient(os.environ['TRADINGAGENTS_MONGODB_URL'], serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('MongoDB: Connected')
    
    # Redis check  
    r = redis.from_url(os.environ['TRADINGAGENTS_REDIS_URL'])
    r.ping()
    print('Redis: Connected')
except Exception as e:
    print(f'Database check failed: {e}')
    exit(1)
" 2>/dev/null; then
        log_error "Database connectivity check failed"
        exit 1
    fi

    # Check current deployment health
    log_info "Checking current deployment health..."
    local unhealthy_pods
    unhealthy_pods=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/part-of=tradingagents-platform --no-headers | grep -v "Running\|Completed" | wc -l)
    if [[ "$unhealthy_pods" -gt 0 ]]; then
        log_warning "Found $unhealthy_pods unhealthy pods in current deployment"
        kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/part-of=tradingagents-platform --no-headers | grep -v "Running\|Completed" || true
        
        if [[ "$FORCE" != "true" ]]; then
            read -p "Continue with unhealthy pods? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_error "Deployment aborted due to unhealthy pods"
                exit 1
            fi
        fi
    fi

    log_success "Pre-deployment checks passed"
}

# Get current active slot (blue or green)
get_active_slot() {
    local service_selector
    service_selector=$(kubectl get service -n "$NAMESPACE" web-service -o jsonpath='{.spec.selector.slot}' 2>/dev/null || echo "")
    
    if [[ "$service_selector" == "blue" ]]; then
        echo "blue"
    elif [[ "$service_selector" == "green" ]]; then
        echo "green"
    else
        # Default to blue if no slot is set
        echo "blue"
    fi
}

# Get inactive slot
get_inactive_slot() {
    local active_slot="$1"
    if [[ "$active_slot" == "blue" ]]; then
        echo "green"
    else
        echo "blue"
    fi
}

# Update deployment images
update_deployment_images() {
    local slot="$1"
    local web_image="ghcr.io/yourusername/${PROJECT_NAME}-web:${IMAGE_TAG}"
    local api_image="ghcr.io/yourusername/${PROJECT_NAME}-api:${IMAGE_TAG}"
    
    log_info "Updating $slot deployment images..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would update deployments:"
        log_info "[DRY-RUN]   web-$slot: $web_image"
        log_info "[DRY-RUN]   api-$slot: $api_image"
        return 0
    fi

    # Update web deployment
    kubectl set image deployment/web-$slot -n "$NAMESPACE" \
        web="$web_image" \
        --record=true

    # Update API deployment
    kubectl set image deployment/api-$slot -n "$NAMESPACE" \
        api="$api_image" \
        --record=true

    # Update worker deployment if exists
    if kubectl get deployment worker-$slot -n "$NAMESPACE" &>/dev/null; then
        kubectl set image deployment/worker-$slot -n "$NAMESPACE" \
            worker="$api_image" \
            --record=true
    fi

    log_success "Updated $slot deployment images"
}

# Wait for deployment rollout
wait_for_rollout() {
    local slot="$1"
    local deployments=("web-$slot" "api-$slot")
    
    # Add worker if it exists
    if kubectl get deployment worker-$slot -n "$NAMESPACE" &>/dev/null; then
        deployments+=("worker-$slot")
    fi

    log_info "Waiting for $slot deployments to roll out..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would wait for rollout of: ${deployments[*]}"
        return 0
    fi

    for deployment in "${deployments[@]}"; do
        log_info "Waiting for deployment/$deployment to roll out..."
        if ! kubectl rollout status deployment/$deployment -n "$NAMESPACE" --timeout=${TIMEOUT}s; then
            log_error "Deployment $deployment failed to roll out within ${TIMEOUT} seconds"
            return 1
        fi
    done

    log_success "$slot deployments rolled out successfully"
}

# Run health checks
run_health_checks() {
    local slot="$1"
    
    log_info "Running health checks for $slot deployment..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would run health checks for $slot deployment"
        return 0
    fi

    # Wait for pods to be ready
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        local ready_pods
        ready_pods=$(kubectl get pods -n "$NAMESPACE" -l slot="$slot" --field-selector=status.phase=Running --no-headers | wc -l)
        local total_pods
        total_pods=$(kubectl get pods -n "$NAMESPACE" -l slot="$slot" --no-headers | wc -l)
        
        if [[ "$ready_pods" -eq "$total_pods" && "$total_pods" -gt 0 ]]; then
            log_success "All $slot pods are ready ($ready_pods/$total_pods)"
            break
        fi
        
        log_info "Waiting for $slot pods to be ready: $ready_pods/$total_pods (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        log_error "Health checks failed: pods not ready within timeout"
        return 1
    fi

    # Test web service health
    local web_pod
    web_pod=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=tradingagents-web,slot="$slot" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -n "$web_pod" ]]; then
        log_info "Testing web service health..."
        if kubectl exec -n "$NAMESPACE" "$web_pod" -- curl -f http://localhost:8501/_stcore/health &>/dev/null; then
            log_success "Web service health check passed"
        else
            log_error "Web service health check failed"
            return 1
        fi
    fi

    # Test API service health
    local api_pod
    api_pod=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=tradingagents-api,slot="$slot" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -n "$api_pod" ]]; then
        log_info "Testing API service health..."
        if kubectl exec -n "$NAMESPACE" "$api_pod" -- curl -f http://localhost:8000/health &>/dev/null; then
            log_success "API service health check passed"
        else
            log_error "API service health check failed"
            return 1
        fi
    fi

    log_success "All health checks passed for $slot deployment"
}

# Switch traffic to new deployment
switch_traffic() {
    local new_slot="$1"
    local old_slot="$2"
    
    log_info "Switching traffic from $old_slot to $new_slot..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would switch traffic from $old_slot to $new_slot"
        return 0
    fi

    # Update service selectors
    kubectl patch service web-service -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"slot\":\"$new_slot\"}}}"
    kubectl patch service api-service -n "$NAMESPACE" -p "{\"spec\":{\"selector\":{\"slot\":\"$new_slot\"}}}"

    # Update ingress if exists
    if kubectl get ingress tradingagents-ingress -n "$NAMESPACE" &>/dev/null; then
        kubectl annotate ingress tradingagents-ingress -n "$NAMESPACE" deployment.active-slot="$new_slot" --overwrite
    fi

    log_success "Traffic switched to $new_slot deployment"
}

# Validate traffic switch
validate_traffic_switch() {
    local slot="$1"
    
    log_info "Validating traffic switch to $slot..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would validate traffic switch to $slot"
        return 0
    fi

    # Check service endpoints
    local web_endpoints
    web_endpoints=$(kubectl get endpoints web-service -n "$NAMESPACE" -o jsonpath='{.subsets[0].addresses[*].targetRef.name}' 2>/dev/null || echo "")
    
    if [[ "$web_endpoints" == *"$slot"* ]]; then
        log_success "Web service endpoints correctly point to $slot deployment"
    else
        log_error "Web service endpoints validation failed"
        return 1
    fi

    # Perform end-to-end test
    local ingress_ip
    ingress_ip=$(kubectl get ingress tradingagents-ingress -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "localhost")
    
    # Simple connectivity test
    if command -v curl &> /dev/null; then
        local test_url="http://$ingress_ip"
        if curl -f -s --max-time 10 "$test_url" > /dev/null 2>&1; then
            log_success "End-to-end connectivity test passed"
        else
            log_warning "End-to-end connectivity test failed (this may be expected if ingress is not ready)"
        fi
    fi

    log_success "Traffic switch validation completed"
}

# Cleanup old deployment
cleanup_old_deployment() {
    local old_slot="$1"
    
    log_info "Scaling down $old_slot deployment..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would scale down $old_slot deployment"
        return 0
    fi

    # Scale down old deployments
    kubectl scale deployment web-$old_slot -n "$NAMESPACE" --replicas=0
    kubectl scale deployment api-$old_slot -n "$NAMESPACE" --replicas=0
    
    if kubectl get deployment worker-$old_slot -n "$NAMESPACE" &>/dev/null; then
        kubectl scale deployment worker-$old_slot -n "$NAMESPACE" --replicas=0
    fi

    log_success "Scaled down $old_slot deployment"
}

# Rollback deployment
rollback_deployment() {
    local failed_slot="$1"
    local active_slot="$2"
    
    log_error "Rolling back from failed $failed_slot deployment to $active_slot"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY-RUN] Would rollback from $failed_slot to $active_slot"
        return 0
    fi

    # Ensure old slot is scaled up
    kubectl scale deployment web-$active_slot -n "$NAMESPACE" --replicas=2
    kubectl scale deployment api-$active_slot -n "$NAMESPACE" --replicas=2
    
    # Wait for old deployment to be ready
    kubectl rollout status deployment/web-$active_slot -n "$NAMESPACE" --timeout=300s
    kubectl rollout status deployment/api-$active_slot -n "$NAMESPACE" --timeout=300s

    # Switch traffic back
    switch_traffic "$active_slot" "$failed_slot"

    # Scale down failed deployment
    kubectl scale deployment web-$failed_slot -n "$NAMESPACE" --replicas=0
    kubectl scale deployment api-$failed_slot -n "$NAMESPACE" --replicas=0

    log_success "Rollback completed successfully"
}

# Send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    if [[ -z "${SLACK_WEBHOOK:-}" ]]; then
        return 0
    fi

    local color
    case "$status" in
        success) color="good" ;;
        warning) color="warning" ;;
        error) color="danger" ;;
        *) color="good" ;;
    esac

    local payload
    payload=$(cat <<EOF
{
  "attachments": [
    {
      "color": "$color",
      "title": "TradingAgents-CN Deployment - $ENVIRONMENT",
      "text": "$message",
      "fields": [
        {
          "title": "Environment",
          "value": "$ENVIRONMENT",
          "short": true
        },
        {
          "title": "Image Tag",
          "value": "$IMAGE_TAG",
          "short": true
        },
        {
          "title": "Namespace",
          "value": "$NAMESPACE",
          "short": true
        },
        {
          "title": "Timestamp",
          "value": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
          "short": true
        }
      ]
    }
  ]
}
EOF
)

    if ! curl -X POST -H 'Content-type: application/json' --data "$payload" "$SLACK_WEBHOOK" &>/dev/null; then
        log_warning "Failed to send Slack notification"
    fi
}

# Main deployment function
main() {
    local start_time
    start_time=$(date +%s)
    
    log_info "Starting blue-green deployment for $PROJECT_NAME"
    log_info "Environment: $ENVIRONMENT"
    log_info "Image Tag: $IMAGE_TAG"
    log_info "Namespace: $NAMESPACE"
    
    # Get current state
    local active_slot inactive_slot
    active_slot=$(get_active_slot)
    inactive_slot=$(get_inactive_slot "$active_slot")
    
    log_info "Current active slot: $active_slot"
    log_info "Deploying to inactive slot: $inactive_slot"

    # Confirm deployment in production
    if [[ "$ENVIRONMENT" == "production" && "$FORCE" != "true" ]]; then
        echo
        log_warning "You are about to deploy to PRODUCTION environment!"
        log_warning "Active slot: $active_slot -> New slot: $inactive_slot"
        log_warning "Image tag: $IMAGE_TAG"
        echo
        read -p "Are you sure you want to continue? (yes/NO): " -r
        if [[ ! $REPLY =~ ^yes$ ]]; then
            log_error "Deployment aborted by user"
            exit 1
        fi
    fi

    # Pre-deployment checks
    check_prerequisites
    pre_deployment_checks

    # Deploy to inactive slot
    log_info "Step 1: Deploying to $inactive_slot slot..."
    update_deployment_images "$inactive_slot"

    # Wait for rollout
    log_info "Step 2: Waiting for $inactive_slot deployment to be ready..."
    if ! wait_for_rollout "$inactive_slot"; then
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            rollback_deployment "$inactive_slot" "$active_slot"
        fi
        send_notification "error" "Deployment failed during rollout phase"
        exit 1
    fi

    # Health checks
    log_info "Step 3: Running health checks on $inactive_slot deployment..."
    if ! run_health_checks "$inactive_slot"; then
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            rollback_deployment "$inactive_slot" "$active_slot"
        fi
        send_notification "error" "Deployment failed during health checks"
        exit 1
    fi

    # Switch traffic
    log_info "Step 4: Switching traffic to $inactive_slot deployment..."
    if ! switch_traffic "$inactive_slot" "$active_slot"; then
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            rollback_deployment "$inactive_slot" "$active_slot"
        fi
        send_notification "error" "Deployment failed during traffic switch"
        exit 1
    fi

    # Validate traffic switch
    log_info "Step 5: Validating traffic switch..."
    if ! validate_traffic_switch "$inactive_slot"; then
        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
            rollback_deployment "$inactive_slot" "$active_slot"
        fi
        send_notification "error" "Deployment failed during traffic validation"
        exit 1
    fi

    # Cleanup old deployment
    log_info "Step 6: Cleaning up $active_slot deployment..."
    cleanup_old_deployment "$active_slot"

    # Calculate deployment time
    local end_time duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    log_success "Blue-green deployment completed successfully!"
    log_success "New active slot: $inactive_slot"
    log_success "Deployment time: ${duration} seconds"

    send_notification "success" "Deployment completed successfully in ${duration} seconds. New active slot: $inactive_slot"
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    parse_arguments "$@"
    main
fi