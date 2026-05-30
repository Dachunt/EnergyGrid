variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "key_name" {
  type = string
}

variable "ecr_registry_url" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "jwt_secret" {
  type      = string
  sensitive = true
}

variable "pingdom_api_token" {
  type      = string
  sensitive = true
  default   = ""
}

variable "pingdom_email" {
  type    = string
  default = ""
}

variable "aws_account_id" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "allowed_ssh_cidr" {
  type    = string
  default = "0.0.0.0/0"
}
