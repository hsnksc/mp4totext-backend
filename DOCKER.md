# 🐳 MP4toText Backend - Docker Deployment Guide

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Production Deployment](#production-deployment)
- [Development Setup](#development-setup)
- [Container Architecture](#container-architecture)
- [Service Management](#service-management)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

### Required Software

- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+

### System Requirements

- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB available disk space
- **CPU**: 2 cores minimum, 4 cores recommended

### Installation

#### Windows
```powershell
# Install Docker Desktop
winget install Docker.DockerDesktop
```

#### Linux
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin
```

#### macOS
```bash
# Install Docker Desktop
brew install --cask docker
```

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/mp4totext-backend.git
cd mp4totext-backend
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env and fill required values
# Required: SECRET_KEY, JWT_SECRET, GEMINI_API_KEY, PYANNOTE_AUTH_TOKEN
notepad .env  # Windows
nano .env     # Linux/macOS
```

### 3. Start Services

#### Using Makefile (Recommended)
```bash
# Development with hot reload + monitoring tools
make quickstart

# Or step by step
make dev-build
make dev-up
make dev-urls
```

#### Using Docker Compose Directly
```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production
docker-compose up -d
```

### 4. Verify Deployment
```bash
# Check container health
docker-compose ps

# View logs
docker-compose logs -f backend

# Open API docs
http://localhost:8000/docs
```

---

## ⚙️ Environment Configuration

### Required Environment Variables

Create `.env` file from `.env.example`:

```env
# Application
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET=<generate-with-openssl-rand-hex-32>

# Database
POSTGRES_PASSWORD=<strong-password>

# Redis
REDIS_PASSWORD=<strong-password>

# Storage
STORAGE_ACCESS_KEY=<minio-access-key>
STORAGE_SECRET_KEY=<minio-secret-key>

# AI Services
GEMINI_API_KEY=<get-from-google-ai-studio>
PYANNOTE_AUTH_TOKEN=<get-from-huggingface>
```

### Generate Secrets
```bash
# Generate SECRET_KEY and JWT_SECRET
openssl rand -hex 32

# Or use Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### Get API Keys

1. **Gemini AI**: https://makersuite.google.com/app/apikey
2. **Pyannote (HuggingFace)**: https://huggingface.co/settings/tokens

---

## 🏭 Production Deployment

### Build Images
```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend
```

### Start Production Services
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Container health
docker-compose ps
```

### Database Migration
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Check migration status
docker-compose exec backend alembic current
```

---

## 💻 Development Setup

### Start Development Environment
```bash
# Using Makefile
make dev-up

# Or using docker-compose
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Development Features

- **Hot Reload**: Code changes automatically restart services
- **Debug Ports**: Exposed for debugger attachment
- **Monitoring Tools**:
  - Flower (Celery): http://localhost:5555
  - pgAdmin: http://localhost:5050
  - Redis Commander: http://localhost:8081
  - MinIO Console: http://localhost:9001

### Access Development Tools

```bash
# Open all tools
make flower      # Celery monitoring
make pgadmin     # Database GUI
make redis-ui    # Redis GUI
make minio-ui    # Object storage GUI
make docs        # API documentation
```

---

## 🏗️ Container Architecture

### Multi-Stage Build

```
┌─────────────────────────────────────────────┐
│ Stage 1: builder                            │
│ - Compile dependencies                      │
│ - Create virtual environment               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Stage 2: runtime (Production)              │
│ - Minimal base image                       │
│ - Non-root user                            │
│ - Health checks                            │
└─────────────────────────────────────────────┘
                    ↓
    ┌───────────────┴────────────────┐
    ↓               ↓                 ↓
┌─────────┐  ┌──────────────┐  ┌───────────┐
│   API   │  │ Celery Worker│  │   Beat    │
│ Stage 3 │  │   Stage 4    │  │  Stage 5  │
└─────────┘  └──────────────┘  └───────────┘
```

### Services Overview

| Service | Port | Description |
|---------|------|-------------|
| **backend** | 8000 | FastAPI application |
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Cache & message broker |
| **minio** | 9000/9001 | Object storage |
| **celery-worker** | - | Background task processor |
| **celery-beat** | - | Periodic task scheduler |
| **flower** | 5555 | Celery monitoring (dev) |
| **pgadmin** | 5050 | PostgreSQL GUI (dev) |
| **redis-commander** | 8081 | Redis GUI (dev) |

---

## 📊 Service Management

### Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend

# Execute command in container
docker-compose exec backend bash

# Scale workers
docker-compose up -d --scale celery-worker=4
```

### Database Operations

```bash
# Run migrations
make db-migrate

# Rollback migration
make db-rollback

# Open database shell
make db-shell

# Backup database
make db-backup
```

### Testing

```bash
# Run all tests
make test

# Run unit tests
make test-unit

# Run integration tests
make test-integration

# Generate coverage report
make coverage
```

---

## 📈 Monitoring

### Container Health

```bash
# Check health status
make health

# Show resource usage
make stats

# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

### Application Metrics

- **API Health**: http://localhost:8000/health
- **API Status**: http://localhost:8000/api/v1/status
- **Flower (Celery)**: http://localhost:5555 (dev only)

### Log Files

Logs are stored in `./logs` directory:
- `app.log` - Application logs
- `celery.log` - Celery worker logs
- `error.log` - Error logs

---

## 🔍 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Check container status
docker-compose ps

# Rebuild image
docker-compose build --no-cache backend
docker-compose up -d
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready

# Connect to database
docker-compose exec postgres psql -U postgres -d mp4totext
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test connection
docker-compose exec redis redis-cli -a <REDIS_PASSWORD> ping
```

### MinIO Connection Issues

```bash
# Check MinIO is running
docker-compose ps minio

# Check MinIO logs
docker-compose logs minio

# Access MinIO console
http://localhost:9001
```

### Port Already in Use

```bash
# Check which process is using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/macOS

# Kill process or change port in docker-compose.yml
ports:
  - "8001:8000"  # Change host port
```

### Out of Memory

```bash
# Check Docker resource limits
docker stats

# Increase Docker Desktop memory limit
# Settings → Resources → Memory → Increase

# Or limit container memory
docker-compose.yml:
  services:
    backend:
      mem_limit: 2g
```

### Permission Denied

```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Or run with sudo (not recommended)
sudo docker-compose up -d
```

---

## 🧹 Cleanup

### Stop All Services
```bash
make down
```

### Remove All Data (⚠️ Destructive)
```bash
# Remove volumes (data will be lost!)
make clean-volumes

# Remove everything
make clean
```

### Prune Unused Resources
```bash
# Safe cleanup of unused resources
make prune
```

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Project Repository**: https://github.com/yourusername/mp4totext-backend
- **Issue Tracker**: https://github.com/yourusername/mp4totext-backend/issues
- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose Documentation**: https://docs.docker.com/compose/

---

## 🆘 Support

If you encounter any issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review container logs: `docker-compose logs`
3. Open an issue on GitHub
4. Contact the development team

---

**Built with ❤️ by MP4toText Team**
