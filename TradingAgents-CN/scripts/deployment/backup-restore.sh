# =============================================================================
# Comprehensive Backup and Disaster Recovery System
# Automated backups, monitoring, and recovery procedures
# =============================================================================

#!/bin/bash

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-/var/backups/tradingagents-cn}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
ENCRYPTION_KEY_FILE="${ENCRYPTION_KEY_FILE:-/etc/tradingagents/backup.key}"
S3_BUCKET="${S3_BUCKET:-tradingagents-cn-backups}"
NOTIFICATION_WEBHOOK="${NOTIFICATION_WEBHOOK:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local required_commands=("kubectl" "mongodump" "redis-cli" "aws" "gpg" "tar" "gzip")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done

    # Check if backup directory exists and is writable
    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        mkdir -p "$BACKUP_BASE_DIR"
    fi
    
    if [[ ! -w "$BACKUP_BASE_DIR" ]]; then
        log_error "Backup directory is not writable: $BACKUP_BASE_DIR"
        exit 1
    fi

    # Check encryption key
    if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
        log_warning "Encryption key file not found. Creating new key..."
        mkdir -p "$(dirname "$ENCRYPTION_KEY_FILE")"
        openssl rand -base64 32 > "$ENCRYPTION_KEY_FILE"
        chmod 600 "$ENCRYPTION_KEY_FILE"
        log_info "Created new encryption key: $ENCRYPTION_KEY_FILE"
    fi

    log_success "Prerequisites check passed"
}

# Create backup metadata
create_backup_metadata() {
    local backup_dir="$1"
    local backup_type="$2"
    local start_time="$3"
    local end_time="$4"
    
    cat > "$backup_dir/backup_metadata.json" << EOF
{
    "backup_type": "$backup_type",
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "start_time": "$start_time",
    "end_time": "$end_time",
    "duration_seconds": $((end_time - start_time)),
    "hostname": "$(hostname)",
    "kubernetes_context": "$(kubectl config current-context)",
    "backup_version": "1.0",
    "components": {
        "mongodb": true,
        "redis": true,
        "application_data": true,
        "kubernetes_configs": true
    },
    "encryption": "AES256",
    "compression": "gzip"
}
EOF
}

# Backup MongoDB
backup_mongodb() {
    local backup_dir="$1"
    local namespace="${2:-tradingagents-cn}"
    
    log_info "Starting MongoDB backup..."
    
    # Get MongoDB connection details from Kubernetes secret
    local mongodb_uri
    mongodb_uri=$(kubectl get secret -n "$namespace" tradingagents-secrets -o jsonpath='{.data.TRADINGAGENTS_MONGODB_URL}' | base64 -d)
    
    if [[ -z "$mongodb_uri" ]]; then
        log_error "Could not retrieve MongoDB connection string"
        return 1
    fi
    
    # Create MongoDB backup directory
    local mongo_backup_dir="$backup_dir/mongodb"
    mkdir -p "$mongo_backup_dir"
    
    # Extract connection components
    local mongo_host mongo_port mongo_user mongo_pass mongo_db
    mongo_host=$(echo "$mongodb_uri" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    mongo_port=$(echo "$mongodb_uri" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    mongo_user=$(echo "$mongodb_uri" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    mongo_pass=$(echo "$mongodb_uri" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    mongo_db=$(echo "$mongodb_uri" | sed -n 's/.*\/\([^?]*\).*/\1/p')
    
    # Port forward to MongoDB service
    log_info "Setting up port forward to MongoDB..."
    kubectl port-forward -n "$namespace" svc/mongodb-service 27017:27017 &
    local pf_pid=$!
    sleep 5
    
    # Perform backup
    log_info "Creating MongoDB dump..."
    if mongodump --host "localhost:27017" \
                 --username "$mongo_user" \
                 --password "$mongo_pass" \
                 --authenticationDatabase admin \
                 --db "$mongo_db" \
                 --out "$mongo_backup_dir" \
                 --gzip; then
        log_success "MongoDB backup completed"
    else
        log_error "MongoDB backup failed"
        kill $pf_pid 2>/dev/null || true
        return 1
    fi
    
    # Cleanup port forward
    kill $pf_pid 2>/dev/null || true
    
    # Create MongoDB backup metadata
    cat > "$mongo_backup_dir/mongodb_backup_info.json" << EOF
{
    "backup_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "database": "$mongo_db",
    "host": "$mongo_host",
    "port": "$mongo_port",
    "collections_count": $(find "$mongo_backup_dir" -name "*.bson.gz" | wc -l),
    "total_size_bytes": $(du -sb "$mongo_backup_dir" | cut -f1)
}
EOF
    
    log_success "MongoDB backup metadata created"
}

# Backup Redis
backup_redis() {
    local backup_dir="$1"
    local namespace="${2:-tradingagents-cn}"
    
    log_info "Starting Redis backup..."
    
    # Get Redis connection details
    local redis_password
    redis_password=$(kubectl get secret -n "$namespace" tradingagents-secrets -o jsonpath='{.data.REDIS_PASSWORD}' | base64 -d)
    
    # Create Redis backup directory
    local redis_backup_dir="$backup_dir/redis"
    mkdir -p "$redis_backup_dir"
    
    # Port forward to Redis service
    log_info "Setting up port forward to Redis..."
    kubectl port-forward -n "$namespace" svc/redis-service 6379:6379 &
    local pf_pid=$!
    sleep 5
    
    # Create Redis backup
    log_info "Creating Redis backup..."
    if redis-cli -h localhost -p 6379 -a "$redis_password" --rdb "$redis_backup_dir/dump.rdb" BGSAVE; then
        # Wait for background save to complete
        while [[ $(redis-cli -h localhost -p 6379 -a "$redis_password" LASTSAVE) == $(redis-cli -h localhost -p 6379 -a "$redis_password" LASTSAVE) ]]; do
            sleep 1
        done
        log_success "Redis backup completed"
    else
        log_error "Redis backup failed"
        kill $pf_pid 2>/dev/null || true
        return 1
    fi
    
    # Get Redis info for metadata
    local redis_info
    redis_info=$(redis-cli -h localhost -p 6379 -a "$redis_password" INFO | head -20)
    
    # Cleanup port forward
    kill $pf_pid 2>/dev/null || true
    
    # Create Redis backup metadata
    cat > "$redis_backup_dir/redis_backup_info.json" << EOF
{
    "backup_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "redis_version": "$(echo "$redis_info" | grep redis_version | cut -d: -f2 | tr -d '\r')",
    "used_memory": "$(echo "$redis_info" | grep used_memory: | cut -d: -f2 | tr -d '\r')",
    "total_keys": "$(redis-cli -h localhost -p 6379 -a "$redis_password" DBSIZE 2>/dev/null || echo "0")",
    "backup_size_bytes": "$(stat -c%s "$redis_backup_dir/dump.rdb" 2>/dev/null || echo "0")"
}
EOF
    
    log_success "Redis backup metadata created"
}

# Backup application data
backup_application_data() {
    local backup_dir="$1"
    local namespace="${2:-tradingagents-cn}"
    
    log_info "Starting application data backup..."
    
    # Create application data backup directory
    local app_backup_dir="$backup_dir/application_data"
    mkdir -p "$app_backup_dir"
    
    # Backup persistent volume data
    log_info "Backing up persistent volume data..."
    local pvs
    pvs=$(kubectl get pvc -n "$namespace" -o jsonpath='{.items[*].metadata.name}')
    
    for pvc in $pvs; do
        log_info "Backing up PVC: $pvc"
        
        # Create a temporary pod to access PVC data
        kubectl apply -f - << EOF
apiVersion: v1
kind: Pod
metadata:
  name: backup-pod-$pvc
  namespace: $namespace
spec:
  restartPolicy: Never
  containers:
  - name: backup
    image: alpine:latest
    command: ["sleep", "3600"]
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: $pvc
EOF
        
        # Wait for pod to be ready
        kubectl wait --for=condition=Ready pod/backup-pod-$pvc -n "$namespace" --timeout=300s
        
        # Create backup archive
        log_info "Creating backup archive for $pvc..."
        kubectl exec -n "$namespace" backup-pod-$pvc -- tar -czf - -C /data . > "$app_backup_dir/${pvc}_data.tar.gz"
        
        # Cleanup backup pod
        kubectl delete pod backup-pod-$pvc -n "$namespace"
        
        log_success "Completed backup of PVC: $pvc"
    done
    
    # Backup configuration files and secrets
    log_info "Backing up Kubernetes configurations..."
    kubectl get secrets -n "$namespace" -o yaml > "$app_backup_dir/secrets.yaml"
    kubectl get configmaps -n "$namespace" -o yaml > "$app_backup_dir/configmaps.yaml"
    kubectl get pvc -n "$namespace" -o yaml > "$app_backup_dir/persistentvolumeclaims.yaml"
    
    log_success "Application data backup completed"
}

# Backup Kubernetes configurations
backup_kubernetes_configs() {
    local backup_dir="$1"
    local namespace="${2:-tradingagents-cn}"
    
    log_info "Starting Kubernetes configurations backup..."
    
    local k8s_backup_dir="$backup_dir/kubernetes"
    mkdir -p "$k8s_backup_dir"
    
    # Backup all Kubernetes resources in the namespace
    local resources=(
        "deployments"
        "services"
        "ingresses"
        "configmaps"
        "secrets"
        "serviceaccounts"
        "roles"
        "rolebindings"
        "networkpolicies"
        "horizontalpodautoscalers"
        "persistentvolumeclaims"
    )
    
    for resource in "${resources[@]}"; do
        log_info "Backing up $resource..."
        if kubectl get "$resource" -n "$namespace" -o yaml > "$k8s_backup_dir/$resource.yaml" 2>/dev/null; then
            log_success "Backed up $resource"
        else
            log_warning "Could not backup $resource (may not exist)"
        fi
    done
    
    # Backup CRDs and cluster-wide resources (if accessible)
    log_info "Backing up custom resources..."
    kubectl get externalsecrets -n "$namespace" -o yaml > "$k8s_backup_dir/externalsecrets.yaml" 2>/dev/null || true
    kubectl get certificates -n "$namespace" -o yaml > "$k8s_backup_dir/certificates.yaml" 2>/dev/null || true
    
    log_success "Kubernetes configurations backup completed"
}

# Encrypt and compress backup
encrypt_backup() {
    local backup_dir="$1"
    local backup_name="$2"
    
    log_info "Encrypting and compressing backup..."
    
    local archive_path="$BACKUP_BASE_DIR/${backup_name}.tar.gz.enc"
    
    # Create compressed encrypted archive
    tar -czf - -C "$backup_dir" . | \
    gpg --symmetric --cipher-algo AES256 --batch --yes --passphrase-file "$ENCRYPTION_KEY_FILE" \
        --output "$archive_path"
    
    if [[ $? -eq 0 ]]; then
        log_success "Backup encrypted and compressed: $archive_path"
        
        # Calculate and store checksum
        sha256sum "$archive_path" > "$archive_path.sha256"
        log_info "Checksum created: $archive_path.sha256"
        
        return 0
    else
        log_error "Failed to encrypt and compress backup"
        return 1
    fi
}

# Upload to S3
upload_to_s3() {
    local archive_path="$1"
    local backup_name="$2"
    
    if [[ -z "$S3_BUCKET" ]]; then
        log_warning "S3 bucket not configured, skipping upload"
        return 0
    fi
    
    log_info "Uploading backup to S3..."
    
    # Upload backup file
    if aws s3 cp "$archive_path" "s3://$S3_BUCKET/backups/$(date +%Y/%m/%d)/$backup_name.tar.gz.enc" \
        --storage-class STANDARD_IA \
        --metadata "backup-type=full,created-by=backup-script"; then
        log_success "Backup uploaded to S3"
    else
        log_error "Failed to upload backup to S3"
        return 1
    fi
    
    # Upload checksum
    aws s3 cp "$archive_path.sha256" "s3://$S3_BUCKET/backups/$(date +%Y/%m/%d)/$backup_name.tar.gz.enc.sha256"
    
    # Set lifecycle policy for backups older than retention period
    log_info "Applying S3 lifecycle policy..."
    cat > /tmp/lifecycle-policy.json << EOF
{
    "Rules": [
        {
            "ID": "backup-retention",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "backups/"
            },
            "Transitions": [
                {
                    "Days": 7,
                    "StorageClass": "STANDARD_IA"
                },
                {
                    "Days": 30,
                    "StorageClass": "GLACIER"
                },
                {
                    "Days": 90,
                    "StorageClass": "DEEP_ARCHIVE"
                }
            ],
            "Expiration": {
                "Days": $((RETENTION_DAYS * 3))
            }
        }
    ]
}
EOF
    
    aws s3api put-bucket-lifecycle-configuration --bucket "$S3_BUCKET" --lifecycle-configuration file:///tmp/lifecycle-policy.json
    rm -f /tmp/lifecycle-policy.json
}

# Cleanup old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Local cleanup
    find "$BACKUP_BASE_DIR" -name "*.tar.gz.enc" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_BASE_DIR" -name "*.sha256" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_BASE_DIR" -type d -empty -delete
    
    # S3 cleanup (handled by lifecycle policy)
    log_success "Old backups cleaned up"
}

# Send notification
send_notification() {
    local status="$1"
    local message="$2"
    local backup_name="$3"
    local duration="$4"
    
    if [[ -z "$NOTIFICATION_WEBHOOK" ]]; then
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
      "title": "TradingAgents-CN Backup Report",
      "text": "$message",
      "fields": [
        {
          "title": "Backup Name",
          "value": "$backup_name",
          "short": true
        },
        {
          "title": "Duration",
          "value": "${duration}s",
          "short": true
        },
        {
          "title": "Timestamp",
          "value": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
          "short": true
        },
        {
          "title": "Host",
          "value": "$(hostname)",
          "short": true
        }
      ]
    }
  ]
}
EOF
)
    
    curl -X POST -H 'Content-type: application/json' --data "$payload" "$NOTIFICATION_WEBHOOK" &>/dev/null || true
}

# Verify backup integrity
verify_backup() {
    local archive_path="$1"
    
    log_info "Verifying backup integrity..."
    
    # Check checksum
    if [[ -f "$archive_path.sha256" ]]; then
        if sha256sum -c "$archive_path.sha256"; then
            log_success "Backup checksum verification passed"
        else
            log_error "Backup checksum verification failed"
            return 1
        fi
    fi
    
    # Test decryption (without extracting)
    if gpg --quiet --batch --yes --passphrase-file "$ENCRYPTION_KEY_FILE" \
           --decrypt "$archive_path" | tar -tzf - > /dev/null; then
        log_success "Backup encryption verification passed"
    else
        log_error "Backup encryption verification failed"
        return 1
    fi
    
    log_success "Backup integrity verification completed"
}

# Main backup function
perform_backup() {
    local backup_type="${1:-full}"
    local namespace="${2:-tradingagents-cn}"
    
    local start_time
    start_time=$(date +%s)
    
    local backup_name
    backup_name="tradingagents-cn-${backup_type}-$(date +%Y%m%d-%H%M%S)"
    
    local temp_backup_dir
    temp_backup_dir="$BACKUP_BASE_DIR/tmp/$backup_name"
    
    log_info "Starting $backup_type backup: $backup_name"
    
    # Create temporary backup directory
    mkdir -p "$temp_backup_dir"
    
    # Perform backups
    backup_mongodb "$temp_backup_dir" "$namespace" || {
        log_error "MongoDB backup failed"
        cleanup_temp_backup "$temp_backup_dir"
        return 1
    }
    
    backup_redis "$temp_backup_dir" "$namespace" || {
        log_error "Redis backup failed"
        cleanup_temp_backup "$temp_backup_dir"
        return 1
    }
    
    backup_application_data "$temp_backup_dir" "$namespace" || {
        log_error "Application data backup failed"
        cleanup_temp_backup "$temp_backup_dir"
        return 1
    }
    
    backup_kubernetes_configs "$temp_backup_dir" "$namespace" || {
        log_error "Kubernetes configurations backup failed"
        cleanup_temp_backup "$temp_backup_dir"
        return 1
    }
    
    # Create backup metadata
    local end_time
    end_time=$(date +%s)
    create_backup_metadata "$temp_backup_dir" "$backup_type" "$start_time" "$end_time"
    
    # Encrypt and compress
    local archive_path="$BACKUP_BASE_DIR/${backup_name}.tar.gz.enc"
    encrypt_backup "$temp_backup_dir" "$backup_name" || {
        log_error "Backup encryption failed"
        cleanup_temp_backup "$temp_backup_dir"
        return 1
    }
    
    # Verify backup integrity
    verify_backup "$archive_path" || {
        log_error "Backup verification failed"
        cleanup_temp_backup "$temp_backup_dir"
        rm -f "$archive_path" "$archive_path.sha256"
        return 1
    }
    
    # Upload to S3
    upload_to_s3 "$archive_path" "$backup_name" || {
        log_warning "S3 upload failed, backup stored locally only"
    }
    
    # Cleanup temporary directory
    rm -rf "$temp_backup_dir"
    
    # Cleanup old backups
    cleanup_old_backups
    
    local duration=$((end_time - start_time))
    log_success "Backup completed successfully in ${duration} seconds"
    log_success "Backup location: $archive_path"
    
    # Send notification
    send_notification "success" "Backup completed successfully" "$backup_name" "$duration"
    
    return 0
}

# Cleanup temporary backup directory
cleanup_temp_backup() {
    local temp_dir="$1"
    if [[ -d "$temp_dir" ]]; then
        rm -rf "$temp_dir"
        log_info "Cleaned up temporary backup directory: $temp_dir"
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS] COMMAND

TradingAgents-CN Backup and Disaster Recovery Script

Commands:
  backup [TYPE] [NAMESPACE]  Create backup (TYPE: full|incremental, default: full)
  restore ARCHIVE_PATH       Restore from backup archive
  verify ARCHIVE_PATH        Verify backup integrity
  list                       List available backups
  cleanup                    Clean up old backups

Options:
  -d, --backup-dir DIR      Backup directory (default: $BACKUP_BASE_DIR)
  -r, --retention DAYS      Retention period in days (default: $RETENTION_DAYS)
  -k, --key-file FILE       Encryption key file (default: $ENCRYPTION_KEY_FILE)
  -s, --s3-bucket BUCKET    S3 bucket for remote backups
  -w, --webhook URL         Notification webhook URL
  -h, --help                Show this help message

Examples:
  $0 backup full tradingagents-cn
  $0 restore /var/backups/tradingagents-cn-full-20240101-120000.tar.gz.enc
  $0 verify /var/backups/tradingagents-cn-full-20240101-120000.tar.gz.enc
  $0 list
  $0 cleanup

Environment Variables:
  BACKUP_BASE_DIR          Base directory for backups
  RETENTION_DAYS           Backup retention period
  ENCRYPTION_KEY_FILE      Path to encryption key file
  S3_BUCKET                S3 bucket for remote storage
  NOTIFICATION_WEBHOOK     Webhook URL for notifications

EOF
}

# Parse command line arguments
main() {
    case "${1:-}" in
        backup)
            check_prerequisites
            perform_backup "${2:-full}" "${3:-tradingagents-cn}"
            ;;
        restore)
            if [[ -z "${2:-}" ]]; then
                log_error "Archive path required for restore"
                usage
                exit 1
            fi
            # Restore functionality would be implemented here
            log_info "Restore functionality not yet implemented"
            ;;
        verify)
            if [[ -z "${2:-}" ]]; then
                log_error "Archive path required for verification"
                usage
                exit 1
            fi
            check_prerequisites
            verify_backup "$2"
            ;;
        list)
            log_info "Available backups:"
            ls -la "$BACKUP_BASE_DIR"/*.tar.gz.enc 2>/dev/null || log_info "No backups found"
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown command: ${1:-}"
            usage
            exit 1
            ;;
    esac
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi