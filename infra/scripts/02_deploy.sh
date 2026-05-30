#!/usr/bin/env bash
# Deploy EnergyGrid infrastructure with Terraform.
# Run from project root: bash infra/scripts/02_deploy.sh
set -euo pipefail

TF_DIR="infra/terraform"
TFVARS_FILE="${TF_DIR}/terraform.tfvars"

echo "=== EnergyGrid — Terraform Deploy ==="

# ── Pre-flight checks ──────────────────────────────────────────
if ! command -v terraform &>/dev/null; then
  echo "[ERROR] Terraform not installed. Download from https://developer.hashicorp.com/terraform/downloads"
  exit 1
fi

if ! command -v aws &>/dev/null; then
  echo "[ERROR] AWS CLI not installed."
  exit 1
fi

if [[ ! -f "$TFVARS_FILE" ]]; then
  echo "[ERROR] terraform.tfvars not found."
  echo "  Copy the example: cp ${TF_DIR}/terraform.tfvars.example ${TFVARS_FILE}"
  echo "  Then fill in your values."
  exit 1
fi

# ── Verify AWS credentials ─────────────────────────────────────
echo "[*] Verifying AWS credentials..."
aws sts get-caller-identity --output table

# ── Terraform init & apply ─────────────────────────────────────
cd "$TF_DIR"

echo ""
echo "[1/3] terraform init"
terraform init

echo ""
echo "[2/3] terraform plan"
terraform plan -out=tfplan

echo ""
read -rp "Apply the plan? (yes/no): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Aborted."
  exit 0
fi

echo ""
echo "[3/3] terraform apply"
terraform apply tfplan

echo ""
echo "=== Infrastructure deployed! ==="
echo ""
terraform output

echo ""
echo "Next steps:"
echo "  1. Note the ec2_public_ip from the outputs above."
echo "  2. Run images build: bash infra/scripts/01_build_and_push.sh"
echo "  3. SSH into EC2 and start services: bash infra/scripts/03_start_services.sh"
