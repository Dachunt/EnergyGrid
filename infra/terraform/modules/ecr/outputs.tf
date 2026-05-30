output "registry_url" {
  description = "ECR registry base URL (account_id.dkr.ecr.region.amazonaws.com)"
  value       = split("/", values(aws_ecr_repository.services)[0].repository_url)[0]
}

output "repository_urls" {
  description = "Map of service name to full ECR repository URL"
  value       = { for name, repo in aws_ecr_repository.services : name => repo.repository_url }
}

output "repository_names" {
  description = "Map of service name to ECR repository name"
  value       = { for name, repo in aws_ecr_repository.services : name => repo.name }
}
