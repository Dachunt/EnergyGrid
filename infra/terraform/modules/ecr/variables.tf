variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "services" {
  type        = list(string)
  description = "List of service names to create ECR repositories for"
}
