#!/bin/bash
# =============================================================================
# Backup and Disaster Recovery Script for TradingAgents-CN ChartingArtist
# Comprehensive backup solution for charts, configurations, and metadata
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_BASE_DIR="${BACKUP_STORAGE_PATH:-/app/backups}"
CHARTS_DIR="${CHART_STORAGE_PATH:-/app/data/attachments/charts}"
CACHE_DIR="${CHART_CACHE_PATH:-/app/data/chart_cache}"
CONFIG_DIR="/app/config"
LOGS_DIR="/app/logs"

# Backup settings
BACKUP_RETENTION_DAYS="${CHART_BACKUP_RETENTION:-14}"
COMPRESSION_ENABLED="${CHART_BACKUP_COMPRESSION:-true}"
MONGODB_URL="${TRADINGAGENTS_MONGODB_URL}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
HOSTNAME=$(hostname)

# Logging
LOG_FILE="$LOGS_DIR/backup_$(date '+%Y%m%d').log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log() {
    local level=$1
    shift
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [${level}] $*" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR" "$1"
    exit 1
}

create_backup_structure() {
    local backup_dir="$BACKUP_BASE_DIR/charting_artist_$TIMESTAMP"
    
    log "INFO" "Creating backup directory structure: $backup_dir"
    
    mkdir -p "$backup_dir"/{charts,cache,config,database,logs,metadata}
    echo "$backup_dir"
}

backup_charts() {
    local backup_dir=$1
    local charts_backup_dir="$backup_dir/charts"
    
    log "INFO" "Starting charts backup from $CHARTS_DIR"
    
    if [[ ! -d "$CHARTS_DIR" ]]; then
        log "WARN" "Charts directory does not exist: $CHARTS_DIR"
        return 0
    fi
    
    # Count files to backup
    local file_count=$(find "$CHARTS_DIR" -type f | wc -l)
    log "INFO" "Found $file_count chart files to backup"
    
    if [[ $file_count -eq 0 ]]; then
        log "INFO" "No chart files to backup"
        return 0
    fi
    
    # Create manifest
    find "$CHARTS_DIR" -type f -exec stat --format="%n,%s,%Y" {} \; > "$charts_backup_dir/manifest.csv"
    
    # Copy files with compression if enabled
    if [[ "$COMPRESSION_ENABLED" == "true" ]]; then
        log "INFO" "Creating compressed chart backup"
        tar -czf "$charts_backup_dir/charts_$TIMESTAMP.tar.gz" -C "$(dirname "$CHARTS_DIR")" "$(basename "$CHARTS_DIR")"
        
        # Verify archive
        if tar -tzf "$charts_backup_dir/charts_$TIMESTAMP.tar.gz" > /dev/null; then
            log "INFO" "Chart backup archive verified successfully"
        else
            error_exit "Chart backup archive verification failed"
        fi
    else
        log "INFO" "Creating uncompressed chart backup"
        cp -r "$CHARTS_DIR" "$charts_backup_dir/charts_raw"
    fi
    
    # Generate backup metadata
    cat > "$charts_backup_dir/backup_info.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "hostname": "$HOSTNAME",
    "source_path": "$CHARTS_DIR",
    "file_count": $file_count,
    "compression_enabled": $COMPRESSION_ENABLED,
    "backup_size_mb": $(du -sm "$charts_backup_dir" | cut -f1)
}
EOF
    
    log "INFO" "Charts backup completed successfully"
}

backup_cache() {
    local backup_dir=$1
    local cache_backup_dir="$backup_dir/cache"
    
    log "INFO" "Starting cache backup from $CACHE_DIR"
    
    if [[ ! -d "$CACHE_DIR" ]]; then
        log "WARN" "Cache directory does not exist: $CACHE_DIR"
        return 0
    fi
    
    # Get cache statistics
    local cache_size=$(du -sh "$CACHE_DIR" | cut -f1)
    local cache_files=$(find "$CACHE_DIR" -type f | wc -l)
    
    log "INFO" "Cache statistics - Size: $cache_size, Files: $cache_files"
    
    # Only backup if cache has content and is not too large
    if [[ $cache_files -gt 0 ]] && [[ $(du -sm "$CACHE_DIR" | cut -f1) -lt 1000 ]]; then
        if [[ "$COMPRESSION_ENABLED" == "true" ]]; then
            tar -czf "$cache_backup_dir/cache_$TIMESTAMP.tar.gz" -C "$(dirname "$CACHE_DIR")" "$(basename "$CACHE_DIR")"
            log "INFO" "Cache backup created with compression"
        else
            cp -r "$CACHE_DIR" "$cache_backup_dir/cache_raw"
            log "INFO" "Cache backup created without compression"
        fi
    else
        log "INFO" "Skipping cache backup - empty or too large"
    fi
}

backup_configuration() {
    local backup_dir=$1
    local config_backup_dir="$backup_dir/config"
    
    log "INFO" "Starting configuration backup"
    
    # Backup ChartingArtist specific configs
    local configs_to_backup=(
        "$CONFIG_DIR/charting_config.yaml"
        "$CONFIG_DIR/agent_roles.yaml" 
        "$CONFIG_DIR/environments"
        "/app/.env"
    )
    
    for config in "${configs_to_backup[@]}"; do
        if [[ -e "$config" ]]; then
            if [[ -d "$config" ]]; then
                cp -r "$config" "$config_backup_dir/"
                log "INFO" "Backed up config directory: $config"
            else
                cp "$config" "$config_backup_dir/"
                log "INFO" "Backed up config file: $config"
            fi
        else
            log "WARN" "Config not found: $config"
        fi
    done
    
    # Create config manifest
    cat > "$config_backup_dir/config_manifest.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "hostname": "$HOSTNAME",
    "backed_up_configs": [
$(printf '        "%s",' "${configs_to_backup[@]}" | sed '$s/,$//')
    ]
}
EOF
    
    log "INFO" "Configuration backup completed"
}

backup_database_metadata() {
    local backup_dir=$1
    local db_backup_dir="$backup_dir/database"
    
    log "INFO" "Starting database metadata backup"
    
    if [[ -z "$MONGODB_URL" ]]; then
        log "WARN" "MongoDB URL not configured, skipping database backup"
        return 0
    fi
    
    # Export ChartingArtist collections
    local collections=(
        "charting_artist_config"
        "chart_metadata"
        "chart_tasks"
        "chart_statistics"
        "chart_type_configs"
    )
    
    for collection in "${collections[@]}"; do
        local output_file="$db_backup_dir/${collection}_$TIMESTAMP.json"
        
        if command -v mongodump >/dev/null 2>&1; then
            # Use mongodump for better performance
            log "INFO" "Dumping collection: $collection"
            mongodump --uri="$MONGODB_URL" --collection="$collection" --out="$db_backup_dir/dump"
        elif command -v mongosh >/dev/null 2>&1 || command -v mongo >/dev/null 2>&1; then
            # Fallback to export
            local mongo_cmd="mongosh"
            if ! command -v mongosh >/dev/null 2>&1; then
                mongo_cmd="mongo"
            fi
            
            log "INFO" "Exporting collection: $collection"
            $mongo_cmd --eval "db.$collection.find().forEach(printjson)" "$MONGODB_URL" > "$output_file"
        else
            log "WARN" "No MongoDB client available for backup"
            break
        fi
    done
    
    # Create database backup manifest
    cat > "$db_backup_dir/db_backup_manifest.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "hostname": "$HOSTNAME", 
    "mongodb_url": "${MONGODB_URL%%/*}/*****",
    "collections": [
$(printf '        "%s",' "${collections[@]}" | sed '$s/,$//')
    ],
    "backup_method": "$(command -v mongodump >/dev/null 2>&1 && echo 'mongodump' || echo 'export')"
}
EOF
    
    log "INFO" "Database metadata backup completed"
}

backup_logs() {
    local backup_dir=$1
    local logs_backup_dir="$backup_dir/logs"
    
    log "INFO" "Starting logs backup"
    
    # Backup ChartingArtist specific logs
    local log_patterns=(
        "$LOGS_DIR/charting_artist*.log"
        "$LOGS_DIR/health_check*.log"
        "$LOGS_DIR/backup_*.log"
        "$LOGS_DIR/chart_generation*.log"
    )
    
    local logs_found=0
    for pattern in "${log_patterns[@]}"; do
        if compgen -G "$pattern" > /dev/null; then
            cp $pattern "$logs_backup_dir/" 2>/dev/null || true
            logs_found=$((logs_found + 1))
        fi
    done
    
    if [[ $logs_found -gt 0 ]]; then
        log "INFO" "Backed up $logs_found log file(s)"
    else
        log "INFO" "No ChartingArtist logs found to backup"
    fi
}

create_backup_metadata() {
    local backup_dir=$1
    local metadata_dir="$backup_dir/metadata"
    
    log "INFO" "Creating backup metadata"
    
    # Generate comprehensive backup report
    cat > "$metadata_dir/backup_report.json" << EOF
{
    "backup_info": {
        "timestamp": "$TIMESTAMP",
        "hostname": "$HOSTNAME",
        "backup_type": "charting_artist_full",
        "version": "1.0.0",
        "compression_enabled": $COMPRESSION_ENABLED
    },
    "source_paths": {
        "charts": "$CHARTS_DIR",
        "cache": "$CACHE_DIR", 
        "config": "$CONFIG_DIR",
        "logs": "$LOGS_DIR"
    },
    "backup_paths": {
        "base_dir": "$backup_dir",
        "charts": "$backup_dir/charts",
        "cache": "$backup_dir/cache",
        "config": "$backup_dir/config",
        "database": "$backup_dir/database",
        "logs": "$backup_dir/logs"
    },
    "system_info": {
        "disk_usage": "$(df -h $BACKUP_BASE_DIR | tail -1 | awk '{print $5}')",
        "backup_size": "$(du -sh $backup_dir | cut -f1)",
        "available_space": "$(df -h $BACKUP_BASE_DIR | tail -1 | awk '{print $4}')"
    },
    "retention": {
        "retention_days": $BACKUP_RETENTION_DAYS,
        "auto_cleanup": true
    }
}
EOF
    
    # Create checksums for verification
    log "INFO" "Generating backup checksums"
    find "$backup_dir" -type f -not -path "*/metadata/*" -exec sha256sum {} \; > "$metadata_dir/checksums.sha256"
    
    # Create restoration instructions
    cat > "$metadata_dir/RESTORE_INSTRUCTIONS.md" << 'EOF'
# ChartingArtist Backup Restoration Instructions

## Prerequisites
- TradingAgents-CN environment set up
- MongoDB instance available
- Required directories exist with proper permissions

## Restoration Steps

### 1. Stop ChartingArtist Service
```bash
docker-compose stop charting-service
```

### 2. Restore Chart Files
```bash
# For compressed backups
tar -xzf charts/charts_TIMESTAMP.tar.gz -C /app/data/attachments/

# For uncompressed backups  
cp -r charts/charts_raw/* /app/data/attachments/charts/
```

### 3. Restore Configuration
```bash
cp -r config/* /app/config/
```

### 4. Restore Database Metadata
```bash
# Using mongorestore
mongorestore --uri="$MONGODB_URL" database/dump/

# Or import JSON files manually
```

### 5. Restore Cache (Optional)
```bash
tar -xzf cache/cache_TIMESTAMP.tar.gz -C /app/data/
```

### 6. Verify Restoration
```bash
# Check file counts and permissions
ls -la /app/data/attachments/charts/
ls -la /app/config/

# Verify database collections
mongosh --eval "show collections" "$MONGODB_URL"
```

### 7. Restart Services
```bash
docker-compose start charting-service
docker-compose logs -f charting-service
```

## Verification
- Run health checks: `/app/docker/charting-healthcheck.sh`
- Test chart generation via API
- Check logs for any errors
EOF

    log "INFO" "Backup metadata created successfully"
}

cleanup_old_backups() {
    log "INFO" "Starting cleanup of old backups (retention: $BACKUP_RETENTION_DAYS days)"
    
    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        log "WARN" "Backup base directory does not exist: $BACKUP_BASE_DIR"
        return 0
    fi
    
    local deleted_count=0
    while IFS= read -r -d '' backup_dir; do
        local backup_age_days=$(( ($(date +%s) - $(stat -c %Y "$backup_dir")) / 86400 ))
        
        if [[ $backup_age_days -gt $BACKUP_RETENTION_DAYS ]]; then
            log "INFO" "Deleting old backup: $(basename "$backup_dir") (${backup_age_days} days old)"
            rm -rf "$backup_dir"
            ((deleted_count++))
        fi
    done < <(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "charting_artist_*" -print0)
    
    log "INFO" "Cleanup completed - deleted $deleted_count old backup(s)"
}

verify_backup() {
    local backup_dir=$1
    
    log "INFO" "Verifying backup integrity"
    
    # Check if backup directory exists and has content
    if [[ ! -d "$backup_dir" ]]; then
        error_exit "Backup directory does not exist: $backup_dir"
    fi
    
    # Verify checksums if they exist
    local checksums_file="$backup_dir/metadata/checksums.sha256"
    if [[ -f "$checksums_file" ]]; then
        log "INFO" "Verifying backup checksums"
        if (cd "$backup_dir" && sha256sum -c metadata/checksums.sha256 --quiet); then
            log "INFO" "Backup integrity verification passed"
        else
            error_exit "Backup integrity verification failed"
        fi
    fi
    
    # Check minimum expected files
    local expected_files=(
        "$backup_dir/metadata/backup_report.json"
        "$backup_dir/config/config_manifest.json"
    )
    
    for file in "${expected_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log "WARN" "Expected backup file missing: $file"
        fi
    done
    
    log "INFO" "Backup verification completed successfully"
}

# Main backup function
perform_backup() {
    local start_time=$(date +%s)
    
    log "INFO" "=== Starting ChartingArtist Backup ==="
    log "INFO" "Timestamp: $TIMESTAMP"
    log "INFO" "Hostname: $HOSTNAME"
    
    # Create backup directory structure
    local backup_dir
    backup_dir=$(create_backup_structure)
    
    # Perform individual backup components
    backup_charts "$backup_dir"
    backup_cache "$backup_dir"
    backup_configuration "$backup_dir"
    backup_database_metadata "$backup_dir"
    backup_logs "$backup_dir"
    create_backup_metadata "$backup_dir"
    
    # Verify backup
    verify_backup "$backup_dir"
    
    # Cleanup old backups
    cleanup_old_backups
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local backup_size=$(du -sh "$backup_dir" | cut -f1)
    
    log "INFO" "=== Backup Completed Successfully ==="
    log "INFO" "Backup location: $backup_dir"
    log "INFO" "Backup size: $backup_size"
    log "INFO" "Duration: ${duration}s"
    
    # Create symlink to latest backup
    ln -sfn "$backup_dir" "$BACKUP_BASE_DIR/latest_charting_backup"
    
    return 0
}

# Disaster recovery functions
create_disaster_recovery_plan() {
    local plan_file="$BACKUP_BASE_DIR/DISASTER_RECOVERY_PLAN.md"
    
    cat > "$plan_file" << 'EOF'
# ChartingArtist Disaster Recovery Plan

## Recovery Time Objectives (RTO)
- **Critical Services**: 15 minutes
- **Chart Generation**: 30 minutes  
- **Full Service**: 60 minutes

## Recovery Point Objectives (RPO)
- **Chart Data**: 24 hours (daily backups)
- **Configuration**: 1 hour (on change)
- **Database Metadata**: 24 hours

## Emergency Procedures

### 1. Service Outage (RTO: 15 minutes)
```bash
# Check service status
docker-compose ps charting-service

# Restart service
docker-compose restart charting-service

# Check logs
docker-compose logs -f charting-service

# Run health check
./docker/charting-healthcheck.sh
```

### 2. Data Corruption (RTO: 30 minutes)
```bash
# Stop services
docker-compose stop charting-service

# Restore from latest backup
./scripts/backup/restore_charting_artist.sh

# Verify restoration
./docker/charting-healthcheck.sh

# Start services
docker-compose start charting-service
```

### 3. Complete System Failure (RTO: 60 minutes)
```bash
# Restore infrastructure
# ... infrastructure restoration steps ...

# Restore application
git clone <repository>
cp /backups/latest_charting_backup/config/* ./config/

# Restore data
./scripts/backup/restore_charting_artist.sh --full

# Start services
docker-compose up -d

# Verify all services
./docker/charting-healthcheck.sh
```

## Contact Information
- **Operations Team**: ops@yourdomain.com
- **Development Team**: dev@yourdomain.com
- **Emergency Hotline**: +1-555-EMERGENCY

## Recovery Testing Schedule
- **Monthly**: Service restart procedures
- **Quarterly**: Full backup restoration test
- **Annually**: Complete disaster recovery drill
EOF
    
    log "INFO" "Disaster recovery plan created: $plan_file"
}

# Command line interface
case "${1:-backup}" in
    "backup")
        mkdir -p "$(dirname "$LOG_FILE")"
        perform_backup
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "verify")
        if [[ -n "${2:-}" ]]; then
            verify_backup "$2"
        else
            log "ERROR" "Please specify backup directory to verify"
            exit 1
        fi
        ;;
    "create-dr-plan")
        create_disaster_recovery_plan
        ;;
    "help"|"--help"|"-h")
        echo "Usage: $0 [backup|cleanup|verify <backup_dir>|create-dr-plan]"
        echo ""
        echo "Commands:"
        echo "  backup          - Perform full backup (default)"
        echo "  cleanup         - Remove old backups based on retention policy"
        echo "  verify <dir>    - Verify backup integrity"
        echo "  create-dr-plan  - Generate disaster recovery plan"
        echo ""
        echo "Environment variables:"
        echo "  BACKUP_STORAGE_PATH     - Base backup directory"
        echo "  CHART_BACKUP_RETENTION  - Retention period in days"
        echo "  CHART_BACKUP_COMPRESSION - Enable compression (true/false)"
        exit 0
        ;;
    *)
        error_exit "Unknown command: $1. Use --help for usage information."
        ;;
esac