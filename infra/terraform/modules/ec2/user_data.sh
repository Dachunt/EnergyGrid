#!/bin/bash
set -euo pipefail
exec > /var/log/user-data.log 2>&1

echo "=== EnergyGrid EC2 Bootstrap Started ==="

# ── System update ──────────────────────────────────────────────
dnf update -y

# ── Add swap (prevents OOM on t2.micro with 1 GB RAM) ──────────
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# ── Docker ─────────────────────────────────────────────────────
dnf install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# ── Docker Compose v2 ──────────────────────────────────────────
COMPOSE_VER="v2.27.0"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL \
  "https://github.com/docker/compose/releases/download/$${COMPOSE_VER}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# ── AWS CLI ────────────────────────────────────────────────────
dnf install -y aws-cli

# ── Create app directory ───────────────────────────────────────
mkdir -p /opt/energygrid
chown ec2-user:ec2-user /opt/energygrid

# ── Write environment file (values injected by Terraform) ──────
cat > /opt/energygrid/.env << 'ENVEOF'
${env_file_content}
ENVEOF
chmod 600 /opt/energygrid/.env
chown ec2-user:ec2-user /opt/energygrid/.env

# ── Write docker-compose.yml ───────────────────────────────────
cat > /opt/energygrid/docker-compose.yml << 'COMPOSEEOF'
${compose_content}
COMPOSEEOF
chown ec2-user:ec2-user /opt/energygrid/docker-compose.yml

# ── Write database init SQL ────────────────────────────────────
mkdir -p /opt/energygrid/database
cat > /opt/energygrid/database/init.sql << 'SQLEOF'
${init_sql_content}
SQLEOF

# ── Create log directories ─────────────────────────────────────
mkdir -p /opt/energygrid/logs/spikes /opt/energygrid/logs/alertas
chown -R ec2-user:ec2-user /opt/energygrid/logs

# ── Start script ───────────────────────────────────────────────
cat > /opt/energygrid/start.sh << 'STARTEOF'
#!/bin/bash
set -euo pipefail
APP_DIR="/opt/energygrid"
source "$${APP_DIR}/.env"

echo "[1/4] Logging in to ECR..."
aws ecr get-login-password --region "$${AWS_REGION}" \
  | docker login --username AWS --password-stdin "$${ECR_REGISTRY}"

echo "[2/4] Pulling images..."
cd "$${APP_DIR}"
docker compose pull

echo "[3/4] Starting services..."
docker compose up -d --remove-orphans

echo "[4/4] Waiting for backend..."
for i in $$(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[OK] Backend healthy!"
    break
  fi
  echo "  Attempt $$i/30 — waiting 5s..."
  sleep 5
done

docker compose ps
PUBLIC_IP=$$(curl -sf http://169.254.169.254/latest/meta-data/public-ipv4 || echo "YOUR_EC2_IP")
echo ""
echo "  Frontend : http://$${PUBLIC_IP}:3000"
echo "  Backend  : http://$${PUBLIC_IP}:8000"
echo "  Munin    : http://$${PUBLIC_IP}:8081"
echo "  Login    : admin / Admin123!"
STARTEOF
chmod +x /opt/energygrid/start.sh
chown ec2-user:ec2-user /opt/energygrid/start.sh

# ── systemd service ────────────────────────────────────────────
cat > /etc/systemd/system/energygrid.service << 'SVCEOF'
[Unit]
Description=EnergyGrid Application Stack
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/energygrid
ExecStart=/opt/energygrid/start.sh
TimeoutStartSec=300
User=ec2-user
Group=ec2-user

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable energygrid.service

echo "=== Bootstrap complete ==="
