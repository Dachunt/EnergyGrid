#!/usr/bin/env bash
# Destroy all AWS infrastructure created by Terraform.
# WARNING: This is irreversible. All data will be lost.
set -euo pipefail

TF_DIR="infra/terraform"

echo "=== EnergyGrid — Terraform Teardown ==="
echo ""
echo "WARNING: This will PERMANENTLY destroy all AWS resources:"
echo "  - EC2 instance (and its Elastic IP)"
echo "  - ECR repositories (and all images)"
echo "  - VPC, subnets, security groups"
echo ""
read -rp "Type 'destroy' to confirm: " CONFIRM
if [[ "$CONFIRM" != "destroy" ]]; then
  echo "Aborted."
  exit 0
fi

cd "$TF_DIR"
terraform destroy -auto-approve

echo ""
echo "=== All resources destroyed. ==="
