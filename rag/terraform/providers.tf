provider "aws" {
  region = var.aws_region
}

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0" # required for s3vectors support
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}