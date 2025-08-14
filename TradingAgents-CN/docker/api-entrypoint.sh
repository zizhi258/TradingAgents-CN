#!/bin/bash
# =============================================================================
# API Service Entrypoint Script
# Handles different service modes: api, scheduler, worker, beat
# =============================================================================

set -euo pipefail

SERVICE_TYPE=${1:-api}
LOG_FILE="/app/logs/${SERVICE_TYPE}.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${SERVICE_TYPE^^}: $*" | tee -a "$LOG_FILE"
}

# Wait for dependencies
wait_for_deps() {
    log "Waiting for database dependencies..."
    
    # Wait for MongoDB (parse host/port from TRADINGAGENTS_MONGODB_URL)
    if [ -n "${TRADINGAGENTS_MONGODB_URL:-}" ]; then
        mongo_host=$(echo "$TRADINGAGENTS_MONGODB_URL" | sed -E 's|^mongodb://([^@]+)@([^:/]+):?([0-9]*)/.*$|\2|')
        mongo_port=$(echo "$TRADINGAGENTS_MONGODB_URL" | sed -E 's|^mongodb://([^@]+)@([^:/]+):?([0-9]*)/.*$|\3|')
        if [ -z "$mongo_host" ]; then mongo_host="mongodb"; fi
        if [ -z "$mongo_port" ]; then mongo_port=27017; fi
        while ! nc -z "$mongo_host" "$mongo_port" 2>/dev/null; do
            log "Waiting for MongoDB at ${mongo_host}:${mongo_port}..."
            sleep 5
        done
    fi
    
    # Wait for Redis
    if [ -n "${TRADINGAGENTS_REDIS_URL:-}" ]; then
        local redis_host=$(echo "$TRADINGAGENTS_REDIS_URL" | cut -d'@' -f2 | cut -d':' -f1)
        local redis_port=$(echo "$TRADINGAGENTS_REDIS_URL" | cut -d':' -f3)
        
        while ! nc -z "$redis_host" "$redis_port" 2>/dev/null; do
            log "Waiting for Redis..."
            sleep 5
        done
    fi
    
    log "Dependencies are ready"
}

# Initialize application
init_app() {
    log "Initializing application..."
    
    # Create necessary directories
    mkdir -p /app/{logs,data,reports,config}
    
    # Initialize database if needed
    if [ "$SERVICE_TYPE" = "api" ]; then
        python -c "
from tradingagents.config.database_manager import DatabaseManager
try:
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization failed: {e}')
    exit(1)
"
    fi
    
    log "Application initialized"
}

# Start services based on type
start_service() {
    case "$SERVICE_TYPE" in
        "api")
            log "Starting Market Analysis API server..."
            exec uvicorn tradingagents.api.main:app \
                --host 0.0.0.0 \
                --port 8000 \
                --workers 4 \
                --loop uvloop \
                --http httptools \
                --access-log \
                --log-level info
            ;;
            
        "scheduler")
            log "Starting Market Scheduler service..."
            exec python -m tradingagents.services.scheduler.run
            ;;
            
        "worker")
            log "Starting Celery worker..."
            exec celery -A tradingagents.services.worker worker \
                --loglevel=info \
                --concurrency=4 \
                --max-tasks-per-child=100 \
                --time-limit=3600 \
                --soft-time-limit=3000
            ;;
            
        "beat")
            log "Starting Celery beat scheduler..."
            exec celery -A tradingagents.services.worker beat \
                --loglevel=info \
                --schedule-filename=/app/data/celerybeat-schedule
            ;;
            
        "flower")
            log "Starting Flower monitoring..."
            exec celery -A tradingagents.services.worker flower \
                --port=5555 \
                --address=0.0.0.0
            ;;
            
        *)
            log "ERROR: Unknown service type: $SERVICE_TYPE"
            log "Available types: api, scheduler, worker, beat, flower"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    log "Starting ${SERVICE_TYPE} service..."
    
    # Wait for dependencies
    wait_for_deps
    
    # Initialize application
    init_app
    
    # Start the service
    start_service
}

# Execute main function
main "$@"
