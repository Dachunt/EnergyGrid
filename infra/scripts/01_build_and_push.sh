#!/usr/bin/env bash
# Build all Docker images locally and push them to AWS ECR.
# Run this from the project root: bash infra/scripts/01_build_and_push.sh
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
PROJECT="${PROJECT:-energygrid}"

if [[ -z "$AWS_ACCOUNT_ID" ]]; then
  echo "[ERROR] Set the AWS_ACCOUNT_ID environment variable before running."
  echo "  export AWS_ACCOUNT_ID=\$(aws sts get-caller-identity --query Account --output text)"
  exit 1
fi

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
TAG="${IMAGE_TAG:-latest}"

echo "=== EnergyGrid — Build & Push to ECR ==="
echo "  Registry : $ECR_REGISTRY"
echo "  Region   : $AWS_REGION"
echo "  Tag      : $TAG"
echo ""

# ── ECR login ──────────────────────────────────────────────────
echo "[1/6] Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

# ── Build & push function ───────────────────────────────────────
build_and_push() {
  local service="$1"
  local context="$2"
  local repo="${ECR_REGISTRY}/${PROJECT}-${service}:${TAG}"

  echo ""
  echo "[BUILD] $service → $repo"
  docker build --platform linux/amd64 -t "$repo" "$context"
  docker push "$repo"
  echo "[OK]    $service pushed."
}

# ── Services ───────────────────────────────────────────────────
build_and_push "backend"      "./backend"
build_and_push "frontend"     "./frontend"
build_and_push "simulator"    "./simulator"
build_and_push "nginx"        "./docker/nginx"
build_and_push "munin-master" "./docker/munin-master"

echo ""
echo "=== All images pushed successfully ==="
echo ""
echo "Next step → run: bash infra/scripts/02_deploy.sh"
