#!/bin/bash
# =============================================================================
# Health Check Script for TradingAgents-CN ChartingArtist Service
# Comprehensive health monitoring with graceful degradation
# =============================================================================

set -euo pipefail

# Configuration
HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-30}
API_BASE_URL=${CHARTING_ARTIST_API_URL:-"http://localhost:8002/api"}
REDIS_URL=${TRADINGAGENTS_REDIS_URL:-"redis://localhost:6379"}
MONGODB_URL=${TRADINGAGENTS_MONGODB_URL:-"mongodb://localhost:27017/tradingagents"}
SERVICE_NAME="ChartingArtist"
LOG_FILE="/app/logs/health_check.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Exit codes
EXIT_SUCCESS=0
EXIT_WARNING=1
EXIT_CRITICAL=2
EXIT_UNKNOWN=3

# Metrics collection
declare -A HEALTH_METRICS

# Logging function
log() {
    local level=$1
    shift
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $*" | tee -a "$LOG_FILE"
}

# Health check functions
check_api_health() {
    local endpoint="$API_BASE_URL/charts/health"
    local timeout=$HEALTH_CHECK_TIMEOUT
    
    log "INFO" "Checking API health at $endpoint"
    
    if response=$(curl -s -f --max-time "$timeout" "$endpoint" 2>/dev/null); then
        local status=$(echo "$response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        local timestamp=$(echo "$response" | jq -r '.timestamp // "unknown"' 2>/dev/null || echo "unknown")
        
        if [[ "$status" == "healthy" ]]; then
            log "INFO" "API health check PASSED - Status: $status, Timestamp: $timestamp"
            HEALTH_METRICS["api_health"]="healthy"
            return 0
        else
            log "ERROR" "API health check FAILED - Status: $status"
            HEALTH_METRICS["api_health"]="unhealthy"
            return 1
        fi
    else
        log "ERROR" "API health check FAILED - Unable to connect to $endpoint"
        HEALTH_METRICS["api_health"]="unavailable"
        return 1
    fi
}

check_chart_generation() {
    local endpoint="$API_BASE_URL/charts/list"
    local timeout=$HEALTH_CHECK_TIMEOUT
    
    log "INFO" "Checking chart generation capability"
    
    if response=$(curl -s -f --max-time "$timeout" "$endpoint?limit=1" 2>/dev/null); then
        local total=$(echo "$response" | jq -r '.total // 0' 2>/dev/null || echo "0")
        log "INFO" "Chart generation check PASSED - Total charts: $total"
        HEALTH_METRICS["chart_generation"]="operational"
        return 0
    else
        log "ERROR" "Chart generation check FAILED"
        HEALTH_METRICS["chart_generation"]="failed"
        return 1
    fi
}

check_queue_status() {
    local endpoint="$API_BASE_URL/charts/queue/metrics"
    local timeout=$HEALTH_CHECK_TIMEOUT
    
    log "INFO" "Checking queue status"
    
    if response=$(curl -s -f --max-time "$timeout" "$endpoint" 2>/dev/null); then
        local pending=$(echo "$response" | jq -r '.pending_tasks // 0' 2>/dev/null || echo "0")
        local processing=$(echo "$response" | jq -r '.processing_tasks // 0' 2>/dev/null || echo "0")
        
        # Check if queue is reasonable
        if [[ $pending -lt 100 ]]; then
            log "INFO" "Queue status HEALTHY - Pending: $pending, Processing: $processing"
            HEALTH_METRICS["queue_status"]="healthy"
            return 0
        else
            log "WARN" "Queue status WARNING - High pending tasks: $pending"
            HEALTH_METRICS["queue_status"]="congested"
            return 1
        fi
    else
        log "ERROR" "Queue status check FAILED"
        HEALTH_METRICS["queue_status"]="unavailable"
        return 1
    fi
}

check_storage_health() {
    local charts_dir="/app/data/attachments/charts"
    local cache_dir="/app/data/chart_cache"
    
    log "INFO" "Checking storage health"
    
    # Check if directories exist and are writable
    if [[ -d "$charts_dir" && -w "$charts_dir" ]]; then
        local chart_count=$(find "$charts_dir" -type f -name "*.html" -o -name "*.json" | wc -l)
        local dir_size=$(du -sh "$charts_dir" 2>/dev/null | cut -f1 || echo "unknown")
        
        log "INFO" "Charts directory HEALTHY - Files: $chart_count, Size: $dir_size"
        HEALTH_METRICS["storage_charts"]="healthy"
    else
        log "ERROR" "Charts directory UNHEALTHY - Not accessible: $charts_dir"
        HEALTH_METRICS["storage_charts"]="failed"
        return 1
    fi
    
    if [[ -d "$cache_dir" && -w "$cache_dir" ]]; then
        local cache_size=$(du -sh "$cache_dir" 2>/dev/null | cut -f1 || echo "unknown")
        log "INFO" "Cache directory HEALTHY - Size: $cache_size"
        HEALTH_METRICS["storage_cache"]="healthy"
    else
        log "WARN" "Cache directory WARNING - Not accessible: $cache_dir"
        HEALTH_METRICS["storage_cache"]="degraded"
    fi
    
    return 0
}

check_dependencies() {
    log "INFO" "Checking service dependencies"
    
    local redis_status="unknown"
    local mongodb_status="unknown"
    
    # Check Redis connection
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -u "$REDIS_URL" ping >/dev/null 2>&1; then
            redis_status="healthy"
            log "INFO" "Redis connection HEALTHY"
        else
            redis_status="failed"
            log "ERROR" "Redis connection FAILED"
        fi
    else
        log "WARN" "Redis client not available for health check"
        redis_status="unknown"
    fi
    
    # Check MongoDB connection
    if command -v mongosh >/dev/null 2>&1 || command -v mongo >/dev/null 2>&1; then
        local mongo_cmd="mongosh"
        if ! command -v mongosh >/dev/null 2>&1; then
            mongo_cmd="mongo"
        fi
        
        if timeout 10 $mongo_cmd --eval "db.adminCommand('ping')" "$MONGODB_URL" >/dev/null 2>&1; then
            mongodb_status="healthy"
            log "INFO" "MongoDB connection HEALTHY"
        else
            mongodb_status="failed"
            log "ERROR" "MongoDB connection FAILED"
        fi
    else
        log "WARN" "MongoDB client not available for health check"
        mongodb_status="unknown"
    fi
    
    HEALTH_METRICS["redis_status"]="$redis_status"
    HEALTH_METRICS["mongodb_status"]="$mongodb_status"
    
    # Return success if at least one dependency is healthy
    if [[ "$redis_status" == "healthy" && "$mongodb_status" == "healthy" ]]; then
        return 0
    elif [[ "$redis_status" == "healthy" || "$mongodb_status" == "healthy" ]]; then
        log "WARN" "Dependencies PARTIALLY HEALTHY"
        return 1
    else
        log "ERROR" "Dependencies CRITICAL - Both Redis and MongoDB unavailable"
        return 2
    fi
}

check_system_resources() {
    log "INFO" "Checking system resources"
    
    # Memory usage
    local mem_usage=""
    if command -v free >/dev/null 2>&1; then
        mem_usage=$(free | awk '/^Mem:/{printf "%.1f", $3/$2 * 100.0}')
        log "INFO" "Memory usage: ${mem_usage}%"
        HEALTH_METRICS["memory_usage"]="$mem_usage"
        
        if (( $(echo "$mem_usage > 90" | bc -l) )); then
            log "ERROR" "CRITICAL: High memory usage: ${mem_usage}%"
            return 2
        elif (( $(echo "$mem_usage > 80" | bc -l) )); then
            log "WARN" "WARNING: High memory usage: ${mem_usage}%"
        fi
    fi
    
    # Disk usage
    local disk_usage=""
    if command -v df >/dev/null 2>&1; then
        disk_usage=$(df /app 2>/dev/null | awk 'NR==2{print $5}' | sed 's/%//' || echo "unknown")
        log "INFO" "Disk usage: ${disk_usage}%"
        HEALTH_METRICS["disk_usage"]="$disk_usage"
        
        if [[ "$disk_usage" != "unknown" ]]; then
            if (( disk_usage > 90 )); then
                log "ERROR" "CRITICAL: High disk usage: ${disk_usage}%"
                return 2
            elif (( disk_usage > 80 )); then
                log "WARN" "WARNING: High disk usage: ${disk_usage}%"
            fi
        fi
    fi
    
    # CPU load (if available)
    if command -v uptime >/dev/null 2>&1; then
        local load_avg=$(uptime | awk '{print $(NF-2)}' | sed 's/,//')
        log "INFO" "CPU Load (1min): $load_avg"
        HEALTH_METRICS["cpu_load"]="$load_avg"
    fi
    
    return 0
}

generate_health_report() {
    local overall_status="HEALTHY"
    local critical_issues=0
    local warning_issues=0
    
    log "INFO" "=== ChartingArtist Health Check Report ==="
    
    # Analyze health metrics
    for check in "${!HEALTH_METRICS[@]}"; do
        local status="${HEALTH_METRICS[$check]}"
        case "$status" in
            "healthy"|"operational")
                log "INFO" "✓ $check: $status"
                ;;
            "degraded"|"congested"|"warning")
                log "WARN" "⚠ $check: $status"
                ((warning_issues++))
                if [[ "$overall_status" == "HEALTHY" ]]; then
                    overall_status="DEGRADED"
                fi
                ;;
            "failed"|"unavailable"|"critical")
                log "ERROR" "✗ $check: $status"
                ((critical_issues++))
                overall_status="CRITICAL"
                ;;
            *)
                log "WARN" "? $check: $status (unknown)"
                ((warning_issues++))
                if [[ "$overall_status" == "HEALTHY" ]]; then
                    overall_status="UNKNOWN"
                fi
                ;;
        esac
    done
    
    log "INFO" "=== Summary ==="
    log "INFO" "Overall Status: $overall_status"
    log "INFO" "Critical Issues: $critical_issues"
    log "INFO" "Warning Issues: $warning_issues"
    log "INFO" "Total Checks: ${#HEALTH_METRICS[@]}"
    
    # Generate JSON report for monitoring systems
    local report_file="/app/logs/health_report.json"
    cat > "$report_file" << EOF
{
    "service": "$SERVICE_NAME",
    "timestamp": "$(date -Iseconds)",
    "overall_status": "$overall_status",
    "critical_issues": $critical_issues,
    "warning_issues": $warning_issues,
    "total_checks": ${#HEALTH_METRICS[@]},
    "checks": $(printf '%s\n' "${!HEALTH_METRICS[@]}" | jq -R . | jq -s 'map({key: ., value: "'"${HEALTH_METRICS[@]}"'"}) | from_entries'),
    "next_check": "$(date -d '+1 minute' -Iseconds)"
}
EOF
    
    # Return appropriate exit code
    case "$overall_status" in
        "HEALTHY") return $EXIT_SUCCESS ;;
        "DEGRADED") return $EXIT_WARNING ;;
        "CRITICAL") return $EXIT_CRITICAL ;;
        *) return $EXIT_UNKNOWN ;;
    esac
}

# Graceful degradation functions
enable_degraded_mode() {
    log "WARN" "Enabling degraded mode for ChartingArtist"
    
    # Create a degraded mode marker file
    touch /app/data/.charting_degraded_mode
    
    # Could implement additional degradation logic:
    # - Disable non-essential chart types
    # - Reduce concurrent processing
    # - Use cached charts when possible
    # - Fallback to simple visualization
    
    log "INFO" "Degraded mode enabled - service will continue with limited functionality"
}

disable_degraded_mode() {
    log "INFO" "Disabling degraded mode for ChartingArtist"
    
    # Remove degraded mode marker
    rm -f /app/data/.charting_degraded_mode
    
    log "INFO" "Full functionality restored"
}

# Main health check function
main() {
    local exit_code=$EXIT_SUCCESS
    
    log "INFO" "Starting ChartingArtist health check"
    
    # Create logs directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Initialize metrics
    HEALTH_METRICS=()
    
    # Run all health checks
    check_system_resources || ((exit_code++))
    check_dependencies
    local dep_status=$?
    if [[ $dep_status -eq 2 ]]; then
        exit_code=$EXIT_CRITICAL
    elif [[ $dep_status -eq 1 && $exit_code -lt $EXIT_WARNING ]]; then
        exit_code=$EXIT_WARNING
    fi
    
    check_storage_health || ((exit_code++))
    check_api_health || ((exit_code++))
    check_chart_generation || ((exit_code++))
    check_queue_status || ((exit_code++))
    
    # Generate final report
    generate_health_report
    local report_exit=$?
    
    # Use the more severe exit code
    if [[ $report_exit -gt $exit_code ]]; then
        exit_code=$report_exit
    fi
    
    # Handle degraded mode
    if [[ $exit_code -eq $EXIT_WARNING ]]; then
        if [[ ! -f /app/data/.charting_degraded_mode ]]; then
            enable_degraded_mode
        fi
    elif [[ $exit_code -eq $EXIT_SUCCESS ]]; then
        if [[ -f /app/data/.charting_degraded_mode ]]; then
            disable_degraded_mode
        fi
    fi
    
    log "INFO" "Health check completed with exit code: $exit_code"
    
    exit $exit_code
}

# Handle signals for graceful shutdown
trap 'log "INFO" "Health check interrupted"; exit $EXIT_UNKNOWN' INT TERM

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi