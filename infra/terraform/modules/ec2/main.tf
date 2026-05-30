# IAM role allowing EC2 to pull images from ECR
resource "aws_iam_role" "ec2" {
  name = "${var.project}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = {
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project}-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2.name
}

# Security group
resource "aws_security_group" "ec2" {
  name        = "${var.project}-${var.environment}-ec2-sg"
  description = "EnergyGrid EC2 security group"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  ingress {
    description = "Frontend"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Backend API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Munin dashboard"
    from_port   = 8081
    to_port     = 8081
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project}-${var.environment}-ec2-sg"
    Project     = var.project
    Environment = var.environment
  }
}

# Latest Amazon Linux 2023 AMI
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  env_file_content = <<-ENV
    POSTGRES_USER=energygrid
    POSTGRES_PASSWORD=${var.db_password}
    POSTGRES_DB=energygrid
    POSTGRES_HOST=energygrid-db
    POSTGRES_PORT=5432
    POSTGRES_HOST_PORT=15432
    BACKEND_PORT=8000
    FRONTEND_PORT=3000
    SIMULATOR_INTERVAL_MS=2000
    JWT_SECRET=${var.jwt_secret}
    JWT_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=1440
    PINGDOM_API_TOKEN=${var.pingdom_api_token}
    PINGDOM_EMAIL=${var.pingdom_email}
    MUNIN_MASTER_URL=http://munin-master:8080
    REDIS_URL=redis://energygrid-redis:6379
    ECR_REGISTRY=${var.ecr_registry_url}
    AWS_REGION=${var.aws_region}
  ENV

  compose_content = <<-COMPOSE
    networks:
      energygrid-net:
        driver: bridge

    volumes:
      energygrid-db-data:
      energygrid-logs:
      munin-rrd:
      munin-html:

    services:
      energygrid-db:
        image: postgres:15-alpine
        container_name: ENERGYGRID-DB
        restart: unless-stopped
        environment:
          POSTGRES_USER: $${POSTGRES_USER}
          POSTGRES_PASSWORD: $${POSTGRES_PASSWORD}
          POSTGRES_DB: $${POSTGRES_DB}
        ports:
          - "$${POSTGRES_HOST_PORT}:5432"
        volumes:
          - energygrid-db-data:/var/lib/postgresql/data
          - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
        command:
          - "postgres"
          - "-c"
          - "shared_preload_libraries=pg_stat_statements"
          - "-c"
          - "pg_stat_statements.max=10000"
          - "-c"
          - "pg_stat_statements.track=all"
        networks:
          - energygrid-net
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
          interval: 10s
          timeout: 5s
          retries: 5
        deploy:
          resources:
            limits:
              memory: 256M

      energygrid-redis:
        image: redis:7-alpine
        container_name: ENERGYGRID-REDIS
        restart: unless-stopped
        expose:
          - "6379"
        networks:
          - energygrid-net
        healthcheck:
          test: ["CMD", "redis-cli", "ping"]
          interval: 5s
          timeout: 3s
          retries: 5
        deploy:
          resources:
            limits:
              memory: 64M

      energygrid-backend:
        image: $${ECR_REGISTRY}/energygrid-backend:latest
        restart: on-failure:5
        environment:
          POSTGRES_USER: $${POSTGRES_USER}
          POSTGRES_PASSWORD: $${POSTGRES_PASSWORD}
          POSTGRES_DB: $${POSTGRES_DB}
          POSTGRES_HOST: energygrid-db
          POSTGRES_PORT: $${POSTGRES_PORT}
          SIMULATOR_URL: http://energygrid-simulator:8001
          MUNIN_MASTER_URL: http://munin-master:8080
          PINGDOM_API_TOKEN: $${PINGDOM_API_TOKEN}
          PINGDOM_EMAIL: $${PINGDOM_EMAIL}
          REDIS_URL: redis://energygrid-redis:6379
          JWT_SECRET: $${JWT_SECRET}
          JWT_ALGORITHM: $${JWT_ALGORITHM}
          ACCESS_TOKEN_EXPIRE_MINUTES: $${ACCESS_TOKEN_EXPIRE_MINUTES}
        expose:
          - "8000"
          - "4949"
        volumes:
          - energygrid-logs:/app/logs
          - ./logs/spikes:/app/logs/spikes
          - ./logs/alertas:/app/logs/alertas
        networks:
          - energygrid-net
        depends_on:
          energygrid-db:
            condition: service_healthy
          energygrid-redis:
            condition: service_started
        deploy:
          resources:
            limits:
              memory: 200M

      energygrid-nginx:
        image: $${ECR_REGISTRY}/energygrid-nginx:latest
        container_name: ENERGYGRID-NGINX
        restart: unless-stopped
        ports:
          - "$${BACKEND_PORT}:8000"
        networks:
          - energygrid-net
        depends_on:
          - energygrid-backend
        deploy:
          resources:
            limits:
              memory: 32M

      energygrid-frontend:
        image: $${ECR_REGISTRY}/energygrid-frontend:latest
        container_name: ENERGYGRID-FRONTEND
        restart: unless-stopped
        ports:
          - "$${FRONTEND_PORT}:80"
        networks:
          - energygrid-net
        depends_on:
          - energygrid-backend
        deploy:
          resources:
            limits:
              memory: 32M

      energygrid-simulator:
        image: $${ECR_REGISTRY}/energygrid-simulator:latest
        container_name: ENERGYGRID-SIMULATOR
        restart: unless-stopped
        environment:
          BACKEND_URL: http://energygrid-backend:8000
          INTERVAL_MS: $${SIMULATOR_INTERVAL_MS}
        expose:
          - "8001"
        networks:
          - energygrid-net
        depends_on:
          - energygrid-backend
        deploy:
          resources:
            limits:
              memory: 64M

      munin-master:
        image: $${ECR_REGISTRY}/energygrid-munin-master:latest
        container_name: ENERGYGRID-MUNIN-MASTER
        restart: unless-stopped
        ports:
          - "8081:8080"
        volumes:
          - munin-rrd:/var/lib/munin
          - munin-html:/var/www/munin
        networks:
          - energygrid-net
        depends_on:
          - energygrid-backend
        deploy:
          resources:
            limits:
              memory: 128M
  COMPOSE
}

resource "aws_instance" "main" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t2.micro"
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name
  key_name               = var.key_name

  root_block_device {
    volume_size = 30
    volume_type = "gp2"
    encrypted   = true
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    env_file_content = local.env_file_content
    compose_content  = local.compose_content
    init_sql_content = file("${path.root}/../../database/init.sql")
  })

  tags = {
    Name        = "${var.project}-${var.environment}-ec2"
    Project     = var.project
    Environment = var.environment
  }
}

resource "aws_eip" "main" {
  instance = aws_instance.main.id
  domain   = "vpc"

  tags = {
    Name        = "${var.project}-${var.environment}-eip"
    Project     = var.project
    Environment = var.environment
  }
}
