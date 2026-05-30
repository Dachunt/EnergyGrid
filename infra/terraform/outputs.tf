output "ec2_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = module.ec2.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS of the EC2 instance"
  value       = module.ec2.public_dns
}

output "ecr_registry_url" {
  description = "ECR registry URL for pushing/pulling images"
  value       = module.ecr.registry_url
}

output "ecr_repository_urls" {
  description = "Full ECR repository URLs per service"
  value       = module.ecr.repository_urls
}

output "frontend_url" {
  description = "URL to access the React frontend"
  value       = "http://${module.ec2.public_ip}:3000"
}

output "backend_url" {
  description = "URL to access the FastAPI backend"
  value       = "http://${module.ec2.public_ip}:8000"
}

output "munin_url" {
  description = "URL to access Munin monitoring dashboard"
  value       = "http://${module.ec2.public_ip}:8081"
}

output "ssh_command" {
  description = "SSH command to connect to the EC2 instance"
  value       = "ssh -i ~/.ssh/${var.key_name}.pem ec2-user@${module.ec2.public_ip}"
}
