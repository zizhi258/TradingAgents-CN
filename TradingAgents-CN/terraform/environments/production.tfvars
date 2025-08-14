# =============================================================================
# Production Environment Configuration
# AWS Deployment for TradingAgents-CN Market Analysis Platform
# =============================================================================

# General Configuration
environment      = "production"
project_name     = "tradingagents-cn"
application_version = "1.0.0"
cloud_provider   = "aws"

# Tags applied to all resources
default_tags = {
  Project     = "TradingAgents-CN"
  Environment = "production"
  ManagedBy   = "Terraform"
  Application = "market-analysis"
  Owner       = "DevOps-Team"
  CostCenter  = "engineering"
}

# =============================================================================
# AWS Configuration
# =============================================================================

aws_region = "us-west-2"
aws_availability_zones = ["us-west-2a", "us-west-2b", "us-west-2c"]

# Instance types optimized for production workloads
aws_instance_types = {
  web_app    = "t3.large"      # 2 vCPU, 8 GB RAM
  api_server = "c6i.xlarge"    # 4 vCPU, 8 GB RAM  
  database   = "r6i.xlarge"    # 4 vCPU, 32 GB RAM
  worker     = "c6i.large"     # 2 vCPU, 4 GB RAM
}

# =============================================================================
# Network Configuration
# =============================================================================

vpc_cidr = "10.0.0.0/16"

subnet_config = {
  public_subnets   = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnets  = ["10.0.10.0/24", "10.0.20.0/24", "10.0.30.0/24"]
  database_subnets = ["10.0.100.0/24", "10.0.200.0/24", "10.0.300.0/24"]
}

# =============================================================================
# Kubernetes Configuration
# =============================================================================

kubernetes_version = "1.28"

node_pool_config = {
  min_nodes     = 3      # Minimum for high availability
  max_nodes     = 20     # Scale up for high traffic
  initial_nodes = 5      # Start with adequate capacity
  machine_type  = "c6i.xlarge"
  disk_size     = 100    # GB for container images and logs
}

# =============================================================================
# Database Configuration
# =============================================================================

mongodb_config = {
  version          = "5.0.0"
  instance_class   = "db.r6g.xlarge"  # 4 vCPU, 32 GB RAM
  storage_size     = 500               # GB
  backup_retention = 30                # days
  multi_az         = true              # High availability
}

redis_config = {
  version       = "7.0"
  node_type     = "cache.r7g.large"   # 2 vCPU, 13.07 GB RAM
  num_nodes     = 3                    # Multi-AZ with replica
  auto_failover = true                 # Automatic failover
}

# =============================================================================
# Application Scaling Configuration
# =============================================================================

scaling_config = {
  web_min_replicas    = 3    # Minimum for redundancy
  web_max_replicas    = 15   # Scale for user traffic
  api_min_replicas    = 5    # Handle API load
  api_max_replicas    = 30   # Scale for market analysis
  worker_min_replicas = 2    # Background processing
  worker_max_replicas = 10   # Scale for heavy workloads
}

# =============================================================================
# Security Configuration
# =============================================================================

enable_waf = true

# Production should restrict access - replace with actual IP ranges
allowed_ip_ranges = [
  "10.0.0.0/8",      # Internal networks
  "172.16.0.0/12",   # Internal networks
  "192.168.0.0/16"   # Internal networks
  # Add specific public IP ranges for admin access
]

# SSL certificate ARN - replace with actual certificate
ssl_certificate_arn = "arn:aws:acm:us-west-2:123456789012:certificate/your-certificate-id"

# =============================================================================
# Application Configuration
# =============================================================================

domain_name = "tradingagents-cn.com"

container_images = {
  web_image = "ghcr.io/yourusername/tradingagents-cn-web:v1.0.0"
  api_image = "ghcr.io/yourusername/tradingagents-cn-api:v1.0.0"
}

# =============================================================================
# Monitoring Configuration
# =============================================================================

monitoring_config = {
  enable_prometheus = true
  enable_grafana   = true
  retention_days   = 90     # Extended retention for production
  alert_email      = "alerts@tradingagents-cn.com"
}

# =============================================================================
# Backup Configuration
# =============================================================================

backup_config = {
  enable_daily_backups           = true
  backup_retention_days          = 90    # Extended retention
  enable_point_in_time_recovery  = true  # Critical for production
}