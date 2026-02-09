# Compliance Platform MVP - Phase 0 Terraform Root

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Backend configured via -backend-config in CI/CD or local setup
    # Example:
    # bucket         = "compliance-platform-terraform-state"
    # key            = "phase-0/terraform.tfstate"
    # region         = "ca-central-1"
    # encrypt        = true
    # dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CompliancePlatform"
      Phase       = "Phase0"
      Environment = var.environment
      Terraform   = "true"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ca-central-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
  default     = "031195399879"
}

# Outputs
output "aws_region" {
  value = var.aws_region
}

output "environment" {
  value = var.environment
}
