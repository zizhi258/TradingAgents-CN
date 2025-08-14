# =============================================================================
# Input Variables - Infrastructure Configuration
# =============================================================================

# General Configuration
variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "tradingagents-cn"
}

variable "application_version" {
  description = "Application version"
  type        = string
  default     = "1.0.0"
}

variable "default_tags" {
  description = "Default tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "TradingAgents-CN"
    Environment = "production"
    ManagedBy   = "Terraform"
    Application = "market-analysis"
  }
}

# =============================================================================
# Cloud Provider Configuration
# =============================================================================

variable "cloud_provider" {
  description = "Primary cloud provider (aws, azure, gcp)"
  type        = string
  default     = "aws"
  validation {
    condition     = contains(["aws", "azure", "gcp"], var.cloud_provider)
    error_message = "Cloud provider must be one of: aws, azure, gcp."
  }
}

# AWS Configuration
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "aws_availability_zones" {
  description = "AWS availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

variable "aws_instance_types" {
  description = "Instance types for different workloads"
  type = object({
    web_app    = string
    api_server = string
    database   = string
    worker     = string
  })
  default = {
    web_app    = "t3.medium"
    api_server = "t3.large"
    database   = "r6i.large"
    worker     = "c6i.large"
  }
}

# Azure Configuration
variable "azure_location" {
  description = "Azure region for resources"
  type        = string
  default     = "West US 2"
}

# Google Cloud Configuration
variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
  default     = ""
}

variable "gcp_region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-west1"
}

# =============================================================================
# Kubernetes Configuration
# =============================================================================

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "node_pool_config" {
  description = "Node pool configuration"
  type = object({
    min_nodes     = number
    max_nodes     = number
    initial_nodes = number
    machine_type  = string
    disk_size     = number
  })
  default = {
    min_nodes     = 2
    max_nodes     = 10
    initial_nodes = 3
    machine_type  = "e2-standard-4"
    disk_size     = 100
  }
}

variable "kubernetes_config_path" {
  description = "Path to kubernetes config file"
  type        = string
  default     = "~/.kube/config"
}

# =============================================================================
# Database Configuration
# =============================================================================

variable "mongodb_config" {
  description = "MongoDB configuration"
  type = object({
    version        = string
    instance_class = string
    storage_size   = number
    backup_retention = number
    multi_az       = bool
  })
  default = {
    version        = "6.0"
    instance_class = "db.r6i.large"
    storage_size   = 100
    backup_retention = 7
    multi_az       = true
  }
}

variable "redis_config" {
  description = "Redis configuration"
  type = object({
    version      = string
    node_type    = string
    num_nodes    = number
    auto_failover = bool
  })
  default = {
    version      = "7.0"
    node_type    = "cache.r7g.large"
    num_nodes    = 2
    auto_failover = true
  }
}

# =============================================================================
# Network Configuration
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_config" {
  description = "Subnet configuration"
  type = object({
    public_subnets  = list(string)
    private_subnets = list(string)
    database_subnets = list(string)
  })
  default = {
    public_subnets  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
    private_subnets = ["10.0.10.0/24", "10.0.20.0/24", "10.0.30.0/24"]
    database_subnets = ["10.0.100.0/24", "10.0.200.0/24", "10.0.300.0/24"]
  }
}

# =============================================================================
# Security Configuration
# =============================================================================

variable "enable_waf" {
  description = "Enable Web Application Firewall"
  type        = bool
  default     = true
}

variable "ssl_certificate_arn" {
  description = "SSL certificate ARN for HTTPS"
  type        = string
  default     = ""
}

variable "allowed_ip_ranges" {
  description = "IP ranges allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict in production
}

# =============================================================================
# Application Configuration
# =============================================================================

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "tradingagents-cn.com"
}

variable "container_images" {
  description = "Container images configuration"
  type = object({
    web_image = string
    api_image = string
  })
  default = {
    web_image = "ghcr.io/yourusername/tradingagents-cn-web:latest"
    api_image = "ghcr.io/yourusername/tradingagents-cn-api:latest"
  }
}

variable "scaling_config" {
  description = "Auto-scaling configuration"
  type = object({
    web_min_replicas = number
    web_max_replicas = number
    api_min_replicas = number
    api_max_replicas = number
    worker_min_replicas = number
    worker_max_replicas = number
  })
  default = {
    web_min_replicas = 2
    web_max_replicas = 10
    api_min_replicas = 2
    api_max_replicas = 20
    worker_min_replicas = 1
    worker_max_replicas = 5
  }
}

# =============================================================================
# Monitoring Configuration
# =============================================================================

variable "monitoring_config" {
  description = "Monitoring and alerting configuration"
  type = object({
    enable_prometheus = bool
    enable_grafana   = bool
    retention_days   = number
    alert_email      = string
  })
  default = {
    enable_prometheus = true
    enable_grafana   = true
    retention_days   = 30
    alert_email      = "alerts@tradingagents-cn.com"
  }
}

# =============================================================================
# Backup Configuration
# =============================================================================

variable "backup_config" {
  description = "Backup configuration"
  type = object({
    enable_daily_backups = bool
    backup_retention_days = number
    enable_point_in_time_recovery = bool
  })
  default = {
    enable_daily_backups = true
    backup_retention_days = 30
    enable_point_in_time_recovery = true
  }
}