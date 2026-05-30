variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name used as prefix for all resources"
  type        = string
  default     = "energygrid"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "key_name" {
  description = "Name of the EC2 SSH key pair (must exist in your AWS account)"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID (used for ECR registry URL)"
  type        = string
}

variable "db_password" {
  description = "PostgreSQL database password"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT secret key for authentication tokens"
  type        = string
  sensitive   = true
}

variable "pingdom_api_token" {
  description = "Pingdom API token for uptime monitoring (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "pingdom_email" {
  description = "Pingdom account email (optional)"
  type        = string
  default     = ""
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the EC2 instance"
  type        = string
  default     = "0.0.0.0/0"
}
