#!/bin/bash
# =============================================================================
# Health Check Script for TradingAgents-CN Container
# Performs comprehensive health checks for web service and dependencies
# =============================================================================

set -euo pipefail

# Configuration
HEALTH_CHECK_URL="http://localhost:8501/_stcore/health"
TIMEOUT=10
MAX_RETRIES=3
LOG_FILE="/app/logs/healthcheck.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTHCHECK: $*" | tee -a "$LOG_FILE" 2>/dev/null || echo "$*"
}

# Function to check Streamlit health endpoint
check_streamlit() {
    local retries=0
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -f -s --max-time $TIMEOUT "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
            log "Streamlit health check passed"
            return 0
        fi
        
        retries=$((retries + 1))
        log "Streamlit health check failed, attempt $retries/$MAX_RETRIES"
        sleep 2
    done
    return 1
}

# Function to check Python process health
check_python_process() {
    if pgrep -f "streamlit run" > /dev/null; then
        log "Streamlit process is running"
        return 0
    else
        log "ERROR: Streamlit process not found"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    local usage
    usage=$(df /app | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$usage" -gt 90 ]; then
        log "WARNING: High disk usage: ${usage}%"
        return 1
    else
        log "Disk usage OK: ${usage}%"
        return 0
    fi
}

# Function to check memory usage
check_memory() {
    local mem_available
    if [ -f /proc/meminfo ]; then
        mem_available=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
        # Convert KB to MB
        mem_available_mb=$((mem_available / 1024))
        
        if [ "$mem_available_mb" -lt 100 ]; then
            log "WARNING: Low memory available: ${mem_available_mb}MB"
            return 1
        else
            log "Memory usage OK: ${mem_available_mb}MB available"
            return 0
        fi
    fi
    return 0
}

# Function to check log directory
check_logs() {
    if [ -w "/app/logs" ]; then
        log "Log directory is writable"
        return 0
    else
        log "ERROR: Log directory not writable"
        return 1
    fi
}

# Function to check configuration
check_config() {
    if [ -f "/app/config/settings.json" ] || [ -f "/app/.env" ]; then
        log "Configuration files present"
        return 0
    else
        log "WARNING: No configuration files found"
        return 1
    fi
}

# Function to check ChartingArtist service (if enabled)
check_charting_artist() {
    local charting_enabled="${CHARTING_ARTIST_ENABLED:-false}"
    
    if [ "$charting_enabled" = "true" ]; then
        local charting_url="${CHARTING_ARTIST_API_URL:-http://charting-service:8002/api}/charts/health"
        
        if curl -f -s --max-time $TIMEOUT "$charting_url" > /dev/null 2>&1; then
            log "ChartingArtist service health check passed"
            return 0
        else
            log "WARNING: ChartingArtist service health check failed"
            return 1
        fi
    else
        log "ChartingArtist service disabled, skipping check"
        return 0
    fi
}

# Function to check chart storage directories
check_chart_storage() {
    local charts_dir="${CHART_STORAGE_PATH:-/app/data/attachments/charts}"
    local cache_dir="${CHART_CACHE_PATH:-/app/data/chart_cache}"
    
    if [ -d "$charts_dir" ] && [ -w "$charts_dir" ]; then
        log "Chart storage directory accessible: $charts_dir"
    else
        log "WARNING: Chart storage directory not accessible: $charts_dir"
        return 1
    fi
    
    if [ -d "$cache_dir" ] && [ -w "$cache_dir" ]; then
        log "Chart cache directory accessible: $cache_dir"
    else
        log "WARNING: Chart cache directory not accessible: $cache_dir"
        # Don't fail for cache directory as it's less critical
    fi
    
    return 0
}

# Main health check routine
main() {
    log "Starting comprehensive health check"
    
    local exit_code=0
    local checks_passed=0
    local total_checks=0
    
    # Critical checks (failure causes container to be marked unhealthy)
    critical_checks=(
        "check_python_process"
        "check_streamlit"
        "check_logs"
    )
    
    # Warning checks (logged but don't fail health check)
    warning_checks=(
        "check_disk_space"
        "check_memory"
        "check_config"
        "check_charting_artist"
        "check_chart_storage"
    )
    
    # Run critical checks
    for check in "${critical_checks[@]}"; do
        total_checks=$((total_checks + 1))
        if $check; then
            checks_passed=$((checks_passed + 1))
        else
            log "CRITICAL: Health check $check failed"
            exit_code=1
        fi
    done
    
    # Run warning checks
    for check in "${warning_checks[@]}"; do
        total_checks=$((total_checks + 1))
        if $check; then
            checks_passed=$((checks_passed + 1))
        else
            log "WARNING: Health check $check failed"
            # Don't fail overall health check for warnings
        fi
    done
    
    # Log summary
    log "Health check completed: $checks_passed/$total_checks checks passed"
    
    if [ $exit_code -eq 0 ]; then
        log "Container is healthy"
    else
        log "Container is unhealthy"
    fi
    
    return $exit_code
}

# Execute main function
main "$@"