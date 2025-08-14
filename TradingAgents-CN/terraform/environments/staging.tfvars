# =============================================================================
# Staging Environment Configuration
# AWS Deployment for TradingAgents-CN Market Analysis Platform
# =============================================================================

# General Configuration
environment      = "staging"
project_name     = "tradingagents-cn"
application_version = "1.0.0-staging"
cloud_provider   = "aws"

# Tags applied to all resources
default_tags = {
  Project     = "TradingAgents-CN"
  Environment = "staging"
  ManagedBy   = "Terraform"
  Application = "market-analysis"
  Owner       = "DevOps-Team"
  CostCenter  = "engineering"
  AutoShutdown = "true"  # Enable automatic shutdown for cost savings
}

# =============================================================================
# AWS Configuration
# =============================================================================

aws_region = "us-west-2"
aws_availability_zones = ["us-west-2a", "us-west-2b"]  # Fewer AZs for staging

# Cost-optimized instance types for staging
aws_instance_types = {
  web_app    = "t3.medium"     # 2 vCPU, 4 GB RAM
  api_server = "t3.large"      # 2 vCPU, 8 GB RAM  
  database   = "r6i.large"     # 2 vCPU, 16 GB RAM
  worker     = "t3.medium"     # 2 vCPU, 4 GB RAM
}

# =============================================================================
# Network Configuration
# =============================================================================

vpc_cidr = "10.1.0.0/16"

subnet_config = {
  public_subnets   = ["10.1.1.0/24", "10.1.2.0/24"]
  private_subnets  = ["10.1.10.0/24", "10.1.20.0/24"]
  database_subnets = ["10.1.100.0/24", "10.1.200.0/24"]
}

# =============================================================================
# Kubernetes Configuration
# =============================================================================

kubernetes_version = "1.28"

node_pool_config = {
  min_nodes     = 1      # Minimal for staging
  max_nodes     = 6      # Limited scaling
  initial_nodes = 2      # Start small
  machine_type  = "t3.large"
  disk_size     = 50     # Smaller disks for staging
}

# =============================================================================
# Database Configuration
# =============================================================================

mongodb_config = {
  version          = "5.0.0"
  instance_class   = "db.r6g.large"   # 2 vCPU, 16 GB RAM
  storage_size     = 100               # GB - smaller for staging
  backup_retention = 7                 # days - shorter retention
  multi_az         = false             # Single AZ for cost savings
}

redis_config = {
  version       = "7.0"
  node_type     = "cache.r7g.large"   # 2 vCPU, 13.07 GB RAM
  num_nodes     = 1                    # Single node for staging
  auto_failover = false                # Disabled for single node
}

# =============================================================================
# Application Scaling Configuration
# =============================================================================

scaling_config = {
  web_min_replicas    = 1    # Minimal redundancy
  web_max_replicas    = 4    # Limited scaling
  api_min_replicas    = 2    # Basic load handling
  api_max_replicas    = 8    # Moderate scaling
  worker_min_replicas = 1    # Single worker
  worker_max_replicas = 3    # Limited worker scaling
}

# =============================================================================
# Security Configuration
# =============================================================================

enable_waf = false  # Disabled for staging to reduce costs

# More permissive access for staging (development teams)
allowed_ip_ranges = [
  "0.0.0.0/0"  # Open access for testing - secure this based on your needs
]

# Self-signed or development certificate for staging
ssl_certificate_arn = ""  # Empty for development certificate

# =============================================================================
# Application Configuration
# =============================================================================

domain_name = "staging.tradingagents-cn.com"

container_images = {
  web_image = "ghcr.io/yourusername/tradingagents-cn-web:staging"
  api_image = "ghcr.io/yourusername/tradingagents-cn-api:staging"
}

# =============================================================================
# Monitoring Configuration
# =============================================================================

monitoring_config = {
  enable_prometheus = true
  enable_grafana   = true
  retention_days   = 14     # Shorter retention for staging
  alert_email      = "staging-alerts@tradingagents-cn.com"
}

# =============================================================================
# Backup Configuration
# =============================================================================

backup_config = {
  enable_daily_backups           = true
  backup_retention_days          = 14    # Shorter retention
  enable_point_in_time_recovery  = false # Disabled for cost savings
}