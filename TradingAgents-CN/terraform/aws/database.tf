# =============================================================================
# AWS Database Resources - DocumentDB (MongoDB) and ElastiCache (Redis)
# =============================================================================

# =============================================================================
# DocumentDB (MongoDB Compatible) Cluster
# =============================================================================

# Random password for DocumentDB
resource "random_password" "docdb_password" {
  length  = 32
  special = true
}

# DocumentDB subnet group
resource "aws_docdb_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-docdb-subnet-group"
  subnet_ids = module.vpc.database_subnets

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-docdb-subnet-group"
  })
}

# DocumentDB parameter group
resource "aws_docdb_cluster_parameter_group" "main" {
  family = "docdb5.0"
  name   = "${var.project_name}-${var.environment}-docdb-params"

  parameter {
    name  = "tls"
    value = "enabled"
  }

  parameter {
    name  = "ttl_monitor"
    value = "enabled"
  }

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-docdb-params"
  })
}

# DocumentDB cluster
resource "aws_docdb_cluster" "main" {
  cluster_identifier     = "${var.project_name}-${var.environment}-docdb"
  engine                = "docdb"
  engine_version        = "5.0.0"
  
  master_username        = "tradingadmin"
  master_password        = random_password.docdb_password.result
  
  backup_retention_period = var.backup_config.backup_retention_days
  preferred_backup_window = "03:00-04:00"
  
  skip_final_snapshot = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "${var.project_name}-${var.environment}-docdb-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null
  
  db_subnet_group_name           = aws_docdb_subnet_group.main.name
  vpc_security_group_ids         = [aws_security_group.database_sg.id]
  db_cluster_parameter_group_name = aws_docdb_cluster_parameter_group.main.name
  
  storage_encrypted = true
  kms_key_id       = aws_kms_key.database.arn
  
  enabled_cloudwatch_logs_exports = ["audit"]
  
  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-docdb"
  })
}

# DocumentDB cluster instances
resource "aws_docdb_cluster_instance" "main" {
  count              = var.mongodb_config.multi_az ? 2 : 1
  identifier         = "${var.project_name}-${var.environment}-docdb-${count.index + 1}"
  cluster_identifier = aws_docdb_cluster.main.id
  instance_class     = "db.r6g.large"
  
  performance_insights_enabled = var.environment == "production"
  
  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-docdb-instance-${count.index + 1}"
  })
}

# =============================================================================
# ElastiCache (Redis) Cluster
# =============================================================================

# Random password for Redis
resource "random_password" "redis_password" {
  length  = 32
  special = false  # Redis auth doesn't support special chars
}

# ElastiCache subnet group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-redis-subnet-group"
  subnet_ids = module.vpc.database_subnets

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-redis-subnet-group"
  })
}

# ElastiCache parameter group
resource "aws_elasticache_parameter_group" "main" {
  family = "redis7"
  name   = "${var.project_name}-${var.environment}-redis-params"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-redis-params"
  })
}

# ElastiCache replication group
resource "aws_elasticache_replication_group" "main" {
  replication_group_id         = "${var.project_name}-${var.environment}-redis"
  description                  = "Redis cluster for ${var.project_name} ${var.environment}"
  
  node_type                   = var.redis_config.node_type
  port                        = 6379
  parameter_group_name        = aws_elasticache_parameter_group.main.name
  
  num_cache_clusters          = var.redis_config.num_nodes
  automatic_failover_enabled  = var.redis_config.auto_failover && var.redis_config.num_nodes > 1
  multi_az_enabled           = var.redis_config.auto_failover && var.redis_config.num_nodes > 1
  
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.database_sg.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                = random_password.redis_password.result
  kms_key_id                = aws_kms_key.database.arn
  
  snapshot_retention_limit   = var.backup_config.backup_retention_days
  snapshot_window           = "03:00-05:00"
  
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-redis"
  })
}

# CloudWatch log group for Redis
resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/${var.project_name}-${var.environment}-redis/slow-log"
  retention_in_days = 7
  kms_key_id       = aws_kms_key.logs.arn

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-redis-logs"
  })
}

# =============================================================================
# KMS Keys for Encryption
# =============================================================================

# KMS key for database encryption
resource "aws_kms_key" "database" {
  description             = "KMS key for ${var.project_name} ${var.environment} database encryption"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  
  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-database-kms"
    Type = "Database"
  })
}

resource "aws_kms_alias" "database" {
  name          = "alias/${var.project_name}-${var.environment}-database"
  target_key_id = aws_kms_key.database.key_id
}

# KMS key for logs encryption  
resource "aws_kms_key" "logs" {
  description             = "KMS key for ${var.project_name} ${var.environment} logs encryption"
  deletion_window_in_days = var.environment == "production" ? 30 : 7
  
  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-logs-kms"
    Type = "Logs"
  })
}

resource "aws_kms_alias" "logs" {
  name          = "alias/${var.project_name}-${var.environment}-logs"
  target_key_id = aws_kms_key.logs.key_id
}

# =============================================================================
# Secrets Manager for Database Credentials
# =============================================================================

# DocumentDB credentials
resource "aws_secretsmanager_secret" "docdb_credentials" {
  name                    = "${var.project_name}/${var.environment}/docdb/credentials"
  description             = "DocumentDB credentials for ${var.project_name} ${var.environment}"
  recovery_window_in_days = var.environment == "production" ? 30 : 0
  kms_key_id             = aws_kms_key.database.arn

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-docdb-credentials"
  })
}

resource "aws_secretsmanager_secret_version" "docdb_credentials" {
  secret_id = aws_secretsmanager_secret.docdb_credentials.id
  secret_string = jsonencode({
    username = aws_docdb_cluster.main.master_username
    password = aws_docdb_cluster.main.master_password
    endpoint = aws_docdb_cluster.main.endpoint
    port     = aws_docdb_cluster.main.port
    database = "tradingagents"
    url      = "mongodb://${aws_docdb_cluster.main.master_username}:${aws_docdb_cluster.main.master_password}@${aws_docdb_cluster.main.endpoint}:${aws_docdb_cluster.main.port}/tradingagents?tls=true&replicaSet=rs0&readPreference=secondaryPreferred"
  })
}

# Redis credentials
resource "aws_secretsmanager_secret" "redis_credentials" {
  name                    = "${var.project_name}/${var.environment}/redis/credentials"
  description             = "Redis credentials for ${var.project_name} ${var.environment}"
  recovery_window_in_days = var.environment == "production" ? 30 : 0
  kms_key_id             = aws_kms_key.database.arn

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-redis-credentials"
  })
}

resource "aws_secretsmanager_secret_version" "redis_credentials" {
  secret_id = aws_secretsmanager_secret.redis_credentials.id
  secret_string = jsonencode({
    auth_token = aws_elasticache_replication_group.main.auth_token
    endpoint   = aws_elasticache_replication_group.main.primary_endpoint_address
    port       = aws_elasticache_replication_group.main.port
    url        = "redis://:${aws_elasticache_replication_group.main.auth_token}@${aws_elasticache_replication_group.main.primary_endpoint_address}:${aws_elasticache_replication_group.main.port}"
  })
}

# =============================================================================
# Database Backup Configuration
# =============================================================================

# Lambda function for additional backup tasks
resource "aws_lambda_function" "db_backup" {
  count = var.backup_config.enable_daily_backups ? 1 : 0
  
  filename      = "db_backup_lambda.zip"
  function_name = "${var.project_name}-${var.environment}-db-backup"
  role          = aws_iam_role.lambda_backup[0].arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 300

  source_code_hash = data.archive_file.lambda_backup[0].output_base64sha256

  environment {
    variables = {
      DOCDB_CLUSTER_ID = aws_docdb_cluster.main.cluster_identifier
      REDIS_GROUP_ID   = aws_elasticache_replication_group.main.replication_group_id
      ENVIRONMENT      = var.environment
    }
  }

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-db-backup-lambda"
  })
}

# Lambda function code
data "archive_file" "lambda_backup" {
  count = var.backup_config.enable_daily_backups ? 1 : 0
  
  type        = "zip"
  output_path = "db_backup_lambda.zip"
  
  source {
    content = templatefile("${path.module}/lambda/db_backup.py", {
      docdb_cluster_id = aws_docdb_cluster.main.cluster_identifier
      redis_group_id   = aws_elasticache_replication_group.main.replication_group_id
    })
    filename = "index.py"
  }
}

# IAM role for Lambda backup function
resource "aws_iam_role" "lambda_backup" {
  count = var.backup_config.enable_daily_backups ? 1 : 0
  
  name = "${var.project_name}-${var.environment}-lambda-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.default_tags
}

# IAM policy for Lambda backup function
resource "aws_iam_role_policy_attachment" "lambda_backup_basic" {
  count = var.backup_config.enable_daily_backups ? 1 : 0
  
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_backup[0].name
}

resource "aws_iam_role_policy" "lambda_backup_custom" {
  count = var.backup_config.enable_daily_backups ? 1 : 0
  
  name = "${var.project_name}-${var.environment}-lambda-backup-policy"
  role = aws_iam_role.lambda_backup[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rds:CreateDBClusterSnapshot",
          "rds:DescribeDBClusterSnapshots",
          "elasticache:CreateSnapshot",
          "elasticache:DescribeSnapshots",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch event rule for daily backup
resource "aws_cloudwatch_event_rule" "daily_backup" {
  count = var.backup_config.enable_daily_backups ? 1 : 0
  
  name                = "${var.project_name}-${var.environment}-daily-backup"
  description         = "Trigger daily database backup"
  schedule_expression = "cron(0 2 * * ? *)"  # Daily at 2 AM UTC

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-daily-backup-schedule"
  })
}

resource "aws_cloudwatch_event_target" "lambda_backup" {
  count = var.backup_config.enable_daily_backups ? 1 : 0
  
  rule      = aws_cloudwatch_event_rule.daily_backup[0].name
  target_id = "TriggerLambdaBackup"
  arn       = aws_lambda_function.db_backup[0].arn
}

resource "aws_lambda_permission" "allow_cloudwatch_backup" {
  count = var.backup_config.enable_daily_backups ? 1 : 0
  
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.db_backup[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_backup[0].arn
}