# =============================================================================
# AWS Outputs - Resource Information for Application Configuration
# =============================================================================

# =============================================================================
# Cluster Information
# =============================================================================

output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint of the EKS cluster"
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "Version of the EKS cluster"
  value       = module.eks.cluster_version
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = module.eks.cluster_certificate_authority_data
}

# =============================================================================
# Network Information
# =============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "public_subnets" {
  description = "List of IDs of public subnets"
  value       = module.vpc.public_subnets
}

output "private_subnets" {
  description = "List of IDs of private subnets"
  value       = module.vpc.private_subnets
}

output "database_subnets" {
  description = "List of IDs of database subnets"
  value       = module.vpc.database_subnets
}

output "nat_gateway_ips" {
  description = "List of public Elastic IPs created for AWS NAT Gateway"
  value       = module.vpc.nat_public_ips
}

# =============================================================================
# Database Information
# =============================================================================

output "docdb_cluster_endpoint" {
  description = "DocumentDB cluster endpoint"
  value       = aws_docdb_cluster.main.endpoint
}

output "docdb_cluster_reader_endpoint" {
  description = "DocumentDB cluster reader endpoint"
  value       = aws_docdb_cluster.main.reader_endpoint
}

output "docdb_cluster_port" {
  description = "DocumentDB cluster port"
  value       = aws_docdb_cluster.main.port
}

output "docdb_cluster_identifier" {
  description = "DocumentDB cluster identifier"
  value       = aws_docdb_cluster.main.cluster_identifier
}

output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "redis_reader_endpoint" {
  description = "Redis reader endpoint"
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.main.port
}

output "redis_cluster_id" {
  description = "Redis cluster identifier"
  value       = aws_elasticache_replication_group.main.replication_group_id
}

# =============================================================================
# Secrets Manager Information
# =============================================================================

output "docdb_secret_arn" {
  description = "ARN of the DocumentDB credentials secret"
  value       = aws_secretsmanager_secret.docdb_credentials.arn
}

output "redis_secret_arn" {
  description = "ARN of the Redis credentials secret"
  value       = aws_secretsmanager_secret.redis_credentials.arn
}

# =============================================================================
# Security Information
# =============================================================================

output "database_security_group_id" {
  description = "ID of the database security group"
  value       = aws_security_group.database_sg.id
}

output "node_security_group_id" {
  description = "ID of the EKS node security group"
  value       = aws_security_group.node_sg.id
}

# =============================================================================
# KMS Information
# =============================================================================

output "database_kms_key_id" {
  description = "KMS key ID for database encryption"
  value       = aws_kms_key.database.key_id
}

output "database_kms_key_arn" {
  description = "KMS key ARN for database encryption"
  value       = aws_kms_key.database.arn
}

output "logs_kms_key_id" {
  description = "KMS key ID for logs encryption"
  value       = aws_kms_key.logs.key_id
}

output "logs_kms_key_arn" {
  description = "KMS key ARN for logs encryption"
  value       = aws_kms_key.logs.arn
}

# =============================================================================
# Load Balancer Information
# =============================================================================

output "load_balancer_controller_role_arn" {
  description = "ARN of the AWS Load Balancer Controller IAM role"
  value       = module.load_balancer_controller_irsa.iam_role_arn
}

# =============================================================================
# Environment Configuration for Applications
# =============================================================================

output "environment_variables" {
  description = "Environment variables for application configuration"
  value = {
    AWS_REGION = data.aws_region.current.name
    
    # Database Configuration
    MONGODB_ENDPOINT = aws_docdb_cluster.main.endpoint
    MONGODB_PORT     = aws_docdb_cluster.main.port
    MONGODB_DATABASE = "tradingagents"
    MONGODB_SECRET_ARN = aws_secretsmanager_secret.docdb_credentials.arn
    
    REDIS_ENDPOINT = aws_elasticache_replication_group.main.primary_endpoint_address
    REDIS_PORT     = aws_elasticache_replication_group.main.port
    REDIS_SECRET_ARN = aws_secretsmanager_secret.redis_credentials.arn
    
    # Kubernetes Configuration
    CLUSTER_NAME = module.eks.cluster_name
    
    # Environment
    ENVIRONMENT = var.environment
    PROJECT_NAME = var.project_name
  }
  sensitive = false
}

# =============================================================================
# Kubeconfig Information
# =============================================================================

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks --region ${data.aws_region.current.name} update-kubeconfig --name ${module.eks.cluster_name}"
}

# =============================================================================
# Node Groups Information
# =============================================================================

output "node_groups" {
  description = "Information about EKS managed node groups"
  value = {
    for k, v in module.eks.eks_managed_node_groups : k => {
      node_group_name = v.node_group_id
      instance_types  = v.instance_types
      capacity_type   = v.capacity_type
      scaling_config  = v.scaling_config
      launch_template = {
        id      = v.launch_template_id
        version = v.launch_template_version
      }
    }
  }
}

# =============================================================================
# Connection Strings (Sensitive)
# =============================================================================

output "mongodb_connection_string" {
  description = "MongoDB connection string (sensitive)"
  value       = "mongodb://${aws_docdb_cluster.main.master_username}:${aws_docdb_cluster.main.master_password}@${aws_docdb_cluster.main.endpoint}:${aws_docdb_cluster.main.port}/tradingagents?tls=true&replicaSet=rs0&readPreference=secondaryPreferred"
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string (sensitive)"
  value       = "redis://:${aws_elasticache_replication_group.main.auth_token}@${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
  sensitive   = true
}