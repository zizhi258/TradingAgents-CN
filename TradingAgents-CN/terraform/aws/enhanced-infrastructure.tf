# =============================================================================
# Complete Terraform Infrastructure with Security Best Practices
# Enhanced AWS infrastructure for TradingAgents-CN production deployment
# =============================================================================

# =============================================================================
# Provider and Terraform Configuration
# =============================================================================
terraform {
  required_version = ">= 1.6.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.25"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
    vault = {
      source  = "hashicorp/vault"
      version = "~> 3.23"
    }
  }

  backend "s3" {
    bucket         = "tradingagents-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "tradingagents-terraform-locks"
    
    # Additional security
    versioning = true
    
    # Server-side encryption with KMS
    kms_key_id = "arn:aws:kms:us-west-2:ACCOUNT_ID:key/KEY_ID"
  }
}

# =============================================================================
# Data Sources
# =============================================================================
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Get latest AMI for bastion host
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
  
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# =============================================================================
# Local Values
# =============================================================================
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  common_tags = merge(var.default_tags, {
    Environment   = var.environment
    Project       = var.project_name
    ManagedBy     = "terraform"
    Owner         = var.owner
    CostCenter    = var.cost_center
    Application   = "tradingagents-cn"
    DataClass     = "confidential"
    Compliance    = "financial-services"
  })
  
  cluster_name = "${local.name_prefix}-cluster"
  
  # Security groups
  security_group_rules = {
    api = {
      ingress = [
        {
          from_port   = 8000
          to_port     = 8000
          protocol    = "tcp"
          cidr_blocks = [var.vpc_cidr]
          description = "API server port"
        }
      ]
      egress = [
        {
          from_port   = 0
          to_port     = 0
          protocol    = "-1"
          cidr_blocks = ["0.0.0.0/0"]
          description = "All outbound traffic"
        }
      ]
    }
  }
}

# =============================================================================
# Random Resources for Secrets
# =============================================================================
resource "random_password" "rds_password" {
  length  = 32
  special = true
}

resource "random_password" "redis_auth_token" {
  length  = 32
  special = false
}

resource "random_id" "backup_suffix" {
  byte_length = 4
}

# =============================================================================
# KMS Keys for Encryption
# =============================================================================
resource "aws_kms_key" "main" {
  description             = "KMS key for ${local.name_prefix} encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow use of the key for EKS"
        Effect = "Allow"
        Principal = {
          AWS = [
            module.eks.cluster_iam_role_arn,
            module.eks.node_groups.primary.iam_role_arn,
            module.eks.node_groups.workers.iam_role_arn
          ]
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-kms-key"
  })
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name_prefix}-main"
  target_key_id = aws_kms_key.main.key_id
}

# =============================================================================
# Enhanced VPC Configuration
# =============================================================================
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.4"

  name = "${local.name_prefix}-vpc"
  cidr = var.vpc_cidr

  azs              = slice(data.aws_availability_zones.available.names, 0, 3)
  public_subnets   = var.subnet_config.public_subnets
  private_subnets  = var.subnet_config.private_subnets
  database_subnets = var.subnet_config.database_subnets
  intra_subnets    = var.subnet_config.intra_subnets

  # Enhanced networking features
  enable_nat_gateway       = true
  single_nat_gateway       = var.environment == "development"
  enable_vpn_gateway       = var.enable_vpn_gateway
  enable_dns_hostnames     = true
  enable_dns_support       = true
  create_igw              = true
  
  # Security enhancements
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true
  flow_log_cloudwatch_log_group_retention_in_days = 30
  
  # Network ACLs for additional security
  manage_default_network_acl = true
  default_network_acl_ingress = [
    {
      protocol   = "tcp"
      rule_no    = 100
      action     = "allow"
      cidr_block = var.vpc_cidr
      from_port  = 80
      to_port    = 80
    },
    {
      protocol   = "tcp"
      rule_no    = 110
      action     = "allow"
      cidr_block = var.vpc_cidr
      from_port  = 443
      to_port    = 443
    },
    {
      protocol   = "tcp"
      rule_no    = 120
      action     = "allow"
      cidr_block = "0.0.0.0/0"
      from_port  = 1024
      to_port    = 65535
    }
  ]
  
  # Subnet tagging for EKS
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "Type" = "public"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
    "Type" = "private"
  }
  
  database_subnet_tags = {
    "Type" = "database"
  }
  
  intra_subnet_tags = {
    "Type" = "intra"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

# =============================================================================
# Enhanced Security Groups
# =============================================================================
resource "aws_security_group" "bastion" {
  name_prefix = "${local.name_prefix}-bastion-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for bastion host"

  ingress {
    description = "SSH from allowed IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ip_ranges
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-bastion-sg"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${local.name_prefix}-rds-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for RDS instances"

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  ingress {
    description     = "PostgreSQL from bastion"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-sg"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "elasticache" {
  name_prefix = "${local.name_prefix}-elasticache-"
  vpc_id      = module.vpc.vpc_id
  description = "Security group for ElastiCache cluster"

  ingress {
    description     = "Redis from EKS nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-elasticache-sg"
  })
  
  lifecycle {
    create_before_destroy = true
  }
}

# =============================================================================
# RDS PostgreSQL Instance with Enhanced Security
# =============================================================================
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = module.vpc.database_subnets

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })
}

resource "aws_db_parameter_group" "main" {
  family = "postgres15"
  name   = "${local.name_prefix}-db-params"

  parameter {
    name  = "log_statement"
    value = "all"
  }
  
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }
  
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  tags = local.common_tags
}

resource "aws_db_instance" "main" {
  identifier = "${local.name_prefix}-postgres"

  # Engine configuration
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = var.rds_instance_class
  allocated_storage    = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_type         = "gp3"
  storage_encrypted    = true
  kms_key_id          = aws_kms_key.main.arn

  # Database configuration
  db_name  = var.database_name
  username = var.database_username
  password = random_password.rds_password.result
  port     = 5432

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backup and maintenance
  backup_retention_period   = var.environment == "production" ? 30 : 7
  backup_window            = "03:00-04:00"
  maintenance_window       = "sun:04:00-sun:05:00"
  auto_minor_version_upgrade = true
  deletion_protection      = var.environment == "production"
  
  # Monitoring and logging
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.main.arn
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  # Parameter and option groups
  parameter_group_name = aws_db_parameter_group.main.name
  
  # Snapshot configuration
  final_snapshot_identifier = "${local.name_prefix}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  copy_tags_to_snapshot     = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres"
  })
  
  lifecycle {
    ignore_changes = [password]
  }
}

# RDS Monitoring Role
resource "aws_iam_role" "rds_monitoring" {
  name = "${local.name_prefix}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# =============================================================================
# ElastiCache Redis Cluster with Enhanced Security
# =============================================================================
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-cache-subnet"
  subnet_ids = module.vpc.private_subnets

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cache-subnet"
  })
}

resource "aws_elasticache_parameter_group" "main" {
  family = "redis7.x"
  name   = "${local.name_prefix}-cache-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  
  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = local.common_tags
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${local.name_prefix}-redis"
  description               = "Redis cluster for ${local.name_prefix}"
  
  # Engine configuration
  engine               = "redis"
  engine_version       = "7.0"
  node_type           = var.redis_node_type
  port                = 6379
  parameter_group_name = aws_elasticache_parameter_group.main.name
  
  # Cluster configuration
  num_cache_clusters = var.redis_num_nodes
  
  # Security configuration
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.elasticache.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token = random_password.redis_auth_token.result
  kms_key_id = aws_kms_key.main.arn
  
  # Backup configuration
  automatic_failover_enabled = var.redis_num_nodes > 1
  multi_az_enabled          = var.redis_num_nodes > 1
  snapshot_retention_limit  = var.environment == "production" ? 7 : 1
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"
  
  # Monitoring
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format      = "text"
    log_type        = "slow-log"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis"
  })
}

resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/${local.name_prefix}/slow-log"
  retention_in_days = 30
  kms_key_id       = aws_kms_key.main.arn

  tags = local.common_tags
}

# =============================================================================
# S3 Buckets for Application Data
# =============================================================================
resource "aws_s3_bucket" "app_data" {
  bucket = "${local.name_prefix}-app-data-${random_id.backup_suffix.hex}"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-app-data"
  })
}

resource "aws_s3_bucket_versioning" "app_data" {
  bucket = aws_s3_bucket.app_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  rule {
    id     = "app_data_lifecycle"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }
}

# Backup bucket
resource "aws_s3_bucket" "backups" {
  bucket = "${local.name_prefix}-backups-${random_id.backup_suffix.hex}"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backups"
  })
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# Bastion Host for Secure Access
# =============================================================================
resource "aws_instance" "bastion" {
  count = var.enable_bastion ? 1 : 0
  
  ami                     = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  key_name               = var.ec2_key_pair_name
  vpc_security_group_ids = [aws_security_group.bastion.id]
  subnet_id              = module.vpc.public_subnets[0]
  
  # Enhanced security
  monitoring = true
  
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }
  
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    kms_key_id           = aws_kms_key.main.arn
    delete_on_termination = true
  }
  
  user_data = base64encode(templatefile("${path.module}/user-data/bastion.sh", {
    cloudwatch_agent_config = base64encode(file("${path.module}/config/cloudwatch-agent.json"))
  }))
  
  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-bastion"
    Type = "bastion"
  })
  
  lifecycle {
    ignore_changes = [ami]
  }
}

# =============================================================================
# CloudWatch Alarms and Monitoring
# =============================================================================
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/tradingagents/${var.environment}"
  retention_in_days = 30
  kms_key_id       = aws_kms_key.main.arn

  tags = local.common_tags
}

# RDS CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name_prefix}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = local.common_tags
}

# ElastiCache CPU Utilization Alarm
resource "aws_cloudwatch_metric_alarm" "elasticache_cpu" {
  alarm_name          = "${local.name_prefix}-elasticache-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors ElastiCache CPU utilization"

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.main.primary_endpoint_address
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = local.common_tags
}

# =============================================================================
# SNS Topic for Alerts
# =============================================================================
resource "aws_sns_topic" "alerts" {
  name              = "${local.name_prefix}-alerts"
  kms_master_key_id = aws_kms_key.main.arn

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count = length(var.alert_email_addresses)
  
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email_addresses[count.index]
}

# =============================================================================
# Secrets Manager for Database Credentials
# =============================================================================
resource "aws_secretsmanager_secret" "rds_credentials" {
  name        = "${local.name_prefix}-rds-credentials"
  description = "RDS credentials for ${local.name_prefix}"
  
  kms_key_id = aws_kms_key.main.arn
  
  replica {
    region     = var.backup_region
    kms_key_id = aws_kms_key.main.arn
  }

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "rds_credentials" {
  secret_id = aws_secretsmanager_secret.rds_credentials.id
  
  secret_string = jsonencode({
    username = var.database_username
    password = random_password.rds_password.result
    engine   = "postgres"
    host     = aws_db_instance.main.endpoint
    port     = 5432
    dbname   = var.database_name
  })
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "redis_credentials" {
  name        = "${local.name_prefix}-redis-credentials"
  description = "Redis credentials for ${local.name_prefix}"
  
  kms_key_id = aws_kms_key.main.arn

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "redis_credentials" {
  secret_id = aws_secretsmanager_secret.redis_credentials.id
  
  secret_string = jsonencode({
    auth_token = random_password.redis_auth_token.result
    host       = aws_elasticache_replication_group.main.primary_endpoint_address
    port       = 6379
  })
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# =============================================================================
# WAF for Application Load Balancer
# =============================================================================
resource "aws_wafv2_web_acl" "main" {
  name  = "${local.name_prefix}-web-acl"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-CommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-KnownBadInputsMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "RateLimitRule"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-RateLimitMetric"
      sampled_requests_enabled   = true
    }
  }

  tags = local.common_tags

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-WebACLMetric"
    sampled_requests_enabled   = true
  }
}

# =============================================================================
# Route 53 Configuration
# =============================================================================
resource "aws_route53_zone" "main" {
  count = var.create_route53_zone ? 1 : 0
  
  name          = var.domain_name
  comment       = "Hosted zone for ${local.name_prefix}"
  force_destroy = false

  tags = merge(local.common_tags, {
    Name = var.domain_name
  })
}

# =============================================================================
# Certificate Manager SSL/TLS Certificates
# =============================================================================
resource "aws_acm_certificate" "main" {
  count = var.create_ssl_certificate ? 1 : 0
  
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = var.domain_name
  })
}

resource "aws_route53_record" "cert_validation" {
  count = var.create_ssl_certificate && var.create_route53_zone ? 1 : 0
  
  for_each = {
    for dvo in aws_acm_certificate.main[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.main[0].zone_id
}

resource "aws_acm_certificate_validation" "main" {
  count = var.create_ssl_certificate && var.create_route53_zone ? 1 : 0
  
  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation[0] : record.fqdn]

  timeouts {
    create = "5m"
  }
}