# =============================================================================
# Terraform Provider Configuration - Multi-Cloud Support
# Supports AWS, Azure, and Google Cloud Platform deployments
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.5"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  # Backend configuration - use remote state
  backend "s3" {
    # Configure via backend.hcl or environment variables
    # bucket = "tradingagents-terraform-state"
    # key    = "infrastructure/terraform.tfstate"
    # region = "us-west-2"
  }
}

# =============================================================================
# Provider Configurations
# =============================================================================

# AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = var.default_tags
  }
}

# Azure Provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Google Cloud Provider
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Kubernetes Provider
provider "kubernetes" {
  config_path = var.kubernetes_config_path
}

# Helm Provider
provider "helm" {
  kubernetes {
    config_path = var.kubernetes_config_path
  }
}