# =============================================================================
# AWS Infrastructure Module - EKS Cluster and Supporting Resources
# =============================================================================

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# =============================================================================
# VPC and Networking
# =============================================================================

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.4"

  name = "${var.project_name}-${var.environment}-vpc"
  cidr = var.vpc_cidr

  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  public_subnets  = var.subnet_config.public_subnets
  private_subnets = var.subnet_config.private_subnets
  database_subnets = var.subnet_config.database_subnets

  enable_nat_gateway     = true
  single_nat_gateway     = var.environment == "development"
  enable_vpn_gateway     = false
  enable_dns_hostnames   = true
  enable_dns_support     = true

  # Enable flow logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-vpc"
  })
}

# =============================================================================
# Security Groups
# =============================================================================

# EKS Cluster Security Group
resource "aws_security_group" "cluster_sg" {
  name_prefix = "${var.project_name}-${var.environment}-cluster-"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-cluster-sg"
  })
}

# Node Group Security Group
resource "aws_security_group" "node_sg" {
  name_prefix = "${var.project_name}-${var.environment}-node-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "Node to node communication"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    self        = true
  }

  ingress {
    description     = "Cluster to node communication"
    from_port       = 1025
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.cluster_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-node-sg"
  })
}

# Database Security Group
resource "aws_security_group" "database_sg" {
  name_prefix = "${var.project_name}-${var.environment}-db-"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "MongoDB access from nodes"
    from_port       = 27017
    to_port         = 27017
    protocol        = "tcp"
    security_groups = [aws_security_group.node_sg.id]
  }

  ingress {
    description     = "Redis access from nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.node_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(var.default_tags, {
    Name = "${var.project_name}-${var.environment}-database-sg"
  })
}

# =============================================================================
# EKS Cluster
# =============================================================================

locals {
  cluster_name = "${var.project_name}-${var.environment}-cluster"
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.21"

  cluster_name                   = local.cluster_name
  cluster_version                = var.kubernetes_version
  cluster_endpoint_public_access = true
  
  # Disable public endpoint access for production
  cluster_endpoint_public_access_cidrs = var.environment == "production" ? var.allowed_ip_ranges : ["0.0.0.0/0"]
  cluster_endpoint_private_access      = true

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    # Primary node group for general workloads
    primary = {
      name           = "${var.project_name}-${var.environment}-primary"
      instance_types = [var.aws_instance_types.api_server]
      
      min_size     = var.node_pool_config.min_nodes
      max_size     = var.node_pool_config.max_nodes
      desired_size = var.node_pool_config.initial_nodes

      disk_size = var.node_pool_config.disk_size
      disk_type = "gp3"

      labels = {
        role = "primary"
        environment = var.environment
      }

      taints = []

      tags = merge(var.default_tags, {
        Name = "${var.project_name}-${var.environment}-primary-node"
      })
    }

    # Compute-optimized nodes for background processing
    workers = {
      name           = "${var.project_name}-${var.environment}-workers"
      instance_types = [var.aws_instance_types.worker]
      
      min_size     = 1
      max_size     = var.scaling_config.worker_max_replicas
      desired_size = 2

      disk_size = 50
      disk_type = "gp3"

      labels = {
        role = "worker"
        workload = "compute"
        environment = var.environment
      }

      taints = [
        {
          key    = "workload"
          value  = "compute"
          effect = "NO_SCHEDULE"
        }
      ]

      tags = merge(var.default_tags, {
        Name = "${var.project_name}-${var.environment}-worker-node"
      })
    }
  }

  # Fargate profiles for serverless compute
  fargate_profiles = var.environment == "production" ? {
    monitoring = {
      name = "${var.project_name}-${var.environment}-monitoring"
      selectors = [
        {
          namespace = "monitoring"
        },
        {
          namespace = "logging"
        }
      ]
      
      tags = merge(var.default_tags, {
        Name = "${var.project_name}-${var.environment}-monitoring-fargate"
      })
    }
  } : {}

  # IRSA for service accounts
  enable_irsa = true

  # Cluster security group
  cluster_additional_security_group_ids = [aws_security_group.cluster_sg.id]

  # Node security group  
  node_security_group_additional_rules = {
    ingress_cluster_to_node = {
      description                   = "Cluster API to Nodegroup"
      protocol                     = "tcp"
      from_port                    = 443
      to_port                      = 443
      type                         = "ingress"
      source_cluster_security_group = true
    }
  }

  tags = merge(var.default_tags, {
    Name = local.cluster_name
  })
}

# =============================================================================
# EKS Add-ons
# =============================================================================

resource "aws_eks_addon" "vpc_cni" {
  cluster_name = module.eks.cluster_name
  addon_name   = "vpc-cni"
  addon_version = data.aws_eks_addon_version.vpc_cni.version
  resolve_conflicts = "OVERWRITE"

  depends_on = [module.eks]
}

resource "aws_eks_addon" "coredns" {
  cluster_name = module.eks.cluster_name
  addon_name   = "coredns"
  addon_version = data.aws_eks_addon_version.coredns.version
  resolve_conflicts = "OVERWRITE"

  depends_on = [module.eks]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = module.eks.cluster_name
  addon_name   = "kube-proxy"
  addon_version = data.aws_eks_addon_version.kube_proxy.version
  resolve_conflicts = "OVERWRITE"

  depends_on = [module.eks]
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name = module.eks.cluster_name
  addon_name   = "aws-ebs-csi-driver"
  addon_version = data.aws_eks_addon_version.ebs_csi.version
  resolve_conflicts = "OVERWRITE"

  depends_on = [module.eks]
}

# Data sources for addon versions
data "aws_eks_addon_version" "vpc_cni" {
  addon_name         = "vpc-cni"
  kubernetes_version = module.eks.cluster_version
  most_recent        = true
}

data "aws_eks_addon_version" "coredns" {
  addon_name         = "coredns"
  kubernetes_version = module.eks.cluster_version
  most_recent        = true
}

data "aws_eks_addon_version" "kube_proxy" {
  addon_name         = "kube-proxy"
  kubernetes_version = module.eks.cluster_version
  most_recent        = true
}

data "aws_eks_addon_version" "ebs_csi" {
  addon_name         = "aws-ebs-csi-driver"
  kubernetes_version = module.eks.cluster_version
  most_recent        = true
}

# =============================================================================
# Application Load Balancer Controller
# =============================================================================

# IAM role for AWS Load Balancer Controller
module "load_balancer_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.30"

  role_name = "${var.project_name}-${var.environment}-alb-controller"

  attach_load_balancer_controller_policy = true

  oidc_providers = {
    ex = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }

  tags = var.default_tags
}

# Helm release for AWS Load Balancer Controller
resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.6.2"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.load_balancer_controller_irsa.iam_role_arn
  }

  depends_on = [
    module.eks,
    module.load_balancer_controller_irsa
  ]
}