# =============================================================================
# Enhanced Variables for Production Infrastructure
# =============================================================================

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "tradingagents"
  
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*[a-z0-9]$", var.project_name))
    error_message = "Project name must be lowercase alphanumeric with hyphens."
  }
}

variable "environment" {
  description = "Environment name"
  type        = string
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
  default     = "tradingagents-team"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "engineering"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
  
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "AWS region must be in the format xx-xxxx-x."
  }
}

variable "backup_region" {
  description = "AWS region for backups and cross-region replication"
  type        = string
  default     = "us-east-1"
}

# =============================================================================
# Network Configuration
# =============================================================================
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "subnet_config" {
  description = "Subnet configuration for VPC"
  type = object({
    public_subnets   = list(string)
    private_subnets  = list(string)
    database_subnets = list(string)
    intra_subnets    = list(string)
  })
  default = {
    public_subnets   = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
    private_subnets  = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
    database_subnets = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
    intra_subnets    = ["10.0.31.0/24", "10.0.32.0/24", "10.0.33.0/24"]
  }
}

variable "allowed_ip_ranges" {
  description = "IP ranges allowed to access the infrastructure"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Should be restricted in production
}

variable "enable_vpn_gateway" {
  description = "Enable VPN Gateway"
  type        = bool
  default     = false
}

# =============================================================================
# EKS Configuration
# =============================================================================
variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "node_pool_config" {
  description = "EKS node pool configuration"
  type = object({
    min_nodes     = number
    max_nodes     = number
    initial_nodes = number
    disk_size     = number
  })
  default = {
    min_nodes     = 3
    max_nodes     = 10
    initial_nodes = 3
    disk_size     = 100
  }
}

variable "aws_instance_types" {
  description = "AWS instance types for different workloads"
  type = object({
    api_server = string
    worker     = string
    database   = string
  })
  default = {
    api_server = "t3.large"
    worker     = "c5.xlarge"
    database   = "t3.medium"
  }
}

# =============================================================================
# Database Configuration
# =============================================================================
variable "database_name" {
  description = "Name of the database"
  type        = string
  default     = "tradingagents"
  
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.database_name))
    error_message = "Database name must start with a letter and contain only alphanumeric characters and underscores."
  }
}

variable "database_username" {
  description = "Database master username"
  type        = string
  default     = "postgres"
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "rds_allocated_storage" {
  description = "Initial allocated storage for RDS (GB)"
  type        = number
  default     = 100
  
  validation {
    condition     = var.rds_allocated_storage >= 20
    error_message = "RDS allocated storage must be at least 20 GB."
  }
}

variable "rds_max_allocated_storage" {
  description = "Maximum allocated storage for RDS auto-scaling (GB)"
  type        = number
  default     = 1000
  
  validation {
    condition     = var.rds_max_allocated_storage >= var.rds_allocated_storage
    error_message = "RDS max allocated storage must be greater than or equal to allocated storage."
  }
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_nodes" {
  description = "Number of Redis nodes"
  type        = number
  default     = 2
  
  validation {
    condition     = var.redis_num_nodes >= 1 && var.redis_num_nodes <= 6
    error_message = "Redis number of nodes must be between 1 and 6."
  }
}

# =============================================================================
# Security Configuration
# =============================================================================
variable "enable_bastion" {
  description = "Enable bastion host"
  type        = bool
  default     = true
}

variable "ec2_key_pair_name" {
  description = "EC2 key pair name for bastion host"
  type        = string
  default     = ""
}

variable "enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = true
}

variable "enable_guardduty" {
  description = "Enable AWS GuardDuty"
  type        = bool
  default     = true
}

variable "enable_config" {
  description = "Enable AWS Config"
  type        = bool
  default     = true
}

# =============================================================================
# Monitoring and Alerting
# =============================================================================
variable "alert_email_addresses" {
  description = "Email addresses for alerts"
  type        = list(string)
  default     = []
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed monitoring for resources"
  type        = bool
  default     = true
}

variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
  
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cloudwatch_log_retention_days)
    error_message = "CloudWatch log retention must be a valid value."
  }
}

# =============================================================================
# Domain and SSL Configuration
# =============================================================================
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "tradingagents.example.com"
}

variable "create_route53_zone" {
  description = "Create Route 53 hosted zone"
  type        = bool
  default     = false
}

variable "create_ssl_certificate" {
  description = "Create SSL certificate"
  type        = bool
  default     = true
}

# =============================================================================
# Scaling Configuration
# =============================================================================
variable "scaling_config" {
  description = "Auto-scaling configuration"
  type = object({
    api_min_replicas    = number
    api_max_replicas    = number
    web_min_replicas    = number
    web_max_replicas    = number
    worker_min_replicas = number
    worker_max_replicas = number
  })
  default = {
    api_min_replicas    = 3
    api_max_replicas    = 10
    web_min_replicas    = 2
    web_max_replicas    = 6
    worker_min_replicas = 2
    worker_max_replicas = 8
  }
}

# =============================================================================
# Backup Configuration
# =============================================================================
variable "backup_config" {
  description = "Backup configuration"
  type = object({
    database_backup_retention_days = number
    redis_snapshot_retention_days  = number
    s3_lifecycle_glacier_days      = number
    s3_lifecycle_deep_archive_days = number
  })
  default = {
    database_backup_retention_days = 30
    redis_snapshot_retention_days  = 7
    s3_lifecycle_glacier_days      = 90
    s3_lifecycle_deep_archive_days = 365
  }
}

# =============================================================================
# Feature Flags
# =============================================================================
variable "enable_features" {
  description = "Feature enablement flags"
  type = object({
    multi_az                = bool
    enhanced_monitoring     = bool
    performance_insights    = bool
    automated_backups       = bool
    cross_region_backups    = bool
    encryption_at_rest      = bool
    encryption_in_transit   = bool
    vpc_flow_logs          = bool
    cloudtrail_logging     = bool
    config_compliance      = bool
  })
  default = {
    multi_az                = true
    enhanced_monitoring     = true
    performance_insights    = true
    automated_backups       = true
    cross_region_backups    = true
    encryption_at_rest      = true
    encryption_in_transit   = true
    vpc_flow_logs          = true
    cloudtrail_logging     = true
    config_compliance      = true
  }
}

# =============================================================================
# Default Tags
# =============================================================================
variable "default_tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default = {
    Terraform   = "true"
    Environment = "production"
    Project     = "tradingagents-cn"
    Owner       = "tradingagents-team"
    Repository  = "tradingagents-cn"
  }
}