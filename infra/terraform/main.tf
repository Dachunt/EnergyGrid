terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source      = "./modules/networking"
  project     = var.project
  environment = var.environment
  aws_region  = var.aws_region
}

module "ecr" {
  source      = "./modules/ecr"
  project     = var.project
  environment = var.environment
  services    = ["backend", "frontend", "simulator", "nginx", "munin-master"]
}

module "ec2" {
  source            = "./modules/ec2"
  project           = var.project
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  subnet_id         = module.networking.public_subnet_id
  key_name          = var.key_name
  ecr_registry_url  = module.ecr.registry_url
  db_password       = var.db_password
  jwt_secret        = var.jwt_secret
  pingdom_api_token = var.pingdom_api_token
  pingdom_email     = var.pingdom_email
  aws_account_id    = var.aws_account_id
  aws_region        = var.aws_region
}
