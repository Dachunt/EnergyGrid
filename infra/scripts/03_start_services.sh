#!/usr/bin/env bash
# Run this script ON THE EC2 INSTANCE after SSH-ing in.
# It logs into ECR, pulls all images, and starts the stack.
# Usage: bash /opt/energygrid/start.sh
set -euo pipefail

APP_DIR="/opt/energygrid"
ENV_FILE="${APP_DIR}/.env"

echo "=== EnergyGrid — Start Services on EC2 ==="

# ── Load environment ───────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] .env file not found at $ENV_FILE"
  exit 1
fi
set -a; source "$ENV_FILE"; set +a

AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REGISTRY="${ECR_REGISTRY}"

# ── ECR login ──────────────────────────────────────────────────
echo "[1/4] Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY"

# ── Pull latest images ─────────────────────────────────────────
echo "[2/4] Pulling images from ECR..."
cd "$APP_DIR"
docker compose pull

# ── Start stack ────────────────────────────────────────────────
echo "[3/4] Starting services..."
docker compose up -d --remove-orphans

# ── Health check ───────────────────────────────────────────────
echo "[4/4] Waiting for backend health check..."
for i in {1..30}; do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[OK] Backend is healthy!"
    break
  fi
  echo "  Attempt $i/30 — waiting 5s..."
  sleep 5
done

echo ""
echo "=== Stack started ==="
docker compose ps

PUBLIC_IP=$(curl -sf http://169.254.169.254/latest/meta-data/public-ipv4 || echo "<EC2_PUBLIC_IP>")
echo ""
echo "  Frontend  : http://${PUBLIC_IP}:3000"
echo "  Backend   : http://${PUBLIC_IP}:8000"
echo "  Munin     : http://${PUBLIC_IP}:8081"
echo ""
echo "Default login → user: admin  password: Admin123!"
