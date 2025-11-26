# 🚀 MP4toText - Deployment & Scaling Guide

## 📋 İçindekiler
- [Mimari Özeti](#mimari-özeti)
- [Geliştirme Ortamı](#geliştirme-ortamı)
- [Production Deployment](#production-deployment)
- [Ölçeklendirme Stratejisi](#ölçeklendirme-stratejisi)
- [Monitoring ve Bakım](#monitoring-ve-bakım)
- [Troubleshooting](#troubleshooting)

---

## 🏗️ Mimari Özeti

### Priority-Based Queue Sistemi

```
┌─────────────────────────────────────────────────────────────┐
│                     MP4toText Architecture                   │
└─────────────────────────────────────────────────────────────┘

Web/Mobile Client
      ↓
FastAPI (Backend)
      ↓
Redis (Message Broker)
      ↓
┌────────────────────────────────────────────────────┐
│              Celery Workers (Priority-Based)        │
├────────────────────────────────────────────────────┤
│ CRITICAL Queue (Priority=10)                       │
│  → File Upload, Validation, Storage                │
│  → Real-time Notifications                         │
│  Concurrency: 3 replicas × 6 workers = 18         │
├────────────────────────────────────────────────────┤
│ HIGH Queue (Priority=7)                            │
│  → Whisper Transcription                           │
│  → Speaker Recognition                             │
│  Concurrency: 5 replicas × 12 workers = 60        │
├────────────────────────────────────────────────────┤
│ DEFAULT Queue (Priority=5)                         │
│  → AI Enhancement (Gemini/GPT)                     │
│  → Translation                                     │
│  → Lecture Notes                                   │
│  Concurrency: 4 replicas × 10 workers = 40        │
├────────────────────────────────────────────────────┤
│ LOW Queue (Priority=2)                             │
│  → Cleanup, Maintenance                            │
│  → Batch Operations                                │
│  Concurrency: 1 replica × 4 workers = 4           │
└────────────────────────────────────────────────────┘
      ↓
Storage (MinIO/S3)
Database (PostgreSQL/SQLite)
```

**Toplam Kapasite**: 122 concurrent workers

---

## 💻 Geliştirme Ortamı

### 1. Başlangıç Setup

```bash
# Backend klasörüne git
cd mp4totext-backend

# Environment variables ayarla
cp .env.example .env.development
# .env.development dosyasını düzenle (API keys, etc.)

# Python sanal ortamı
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
.\venv\Scripts\activate  # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 2. Development ile Çalıştırma

#### Seçenek A: Manuel (Terminal'lerde)

```powershell
# Terminal 1: Backend (FastAPI)
cd mp4totext-backend
python run.py

# Terminal 2: Redis
redis-server

# Terminal 3: Celery Worker
cd mp4totext-backend
celery -A app.celery_app worker -Q high,default,critical -l info --autoscale=4,2

# Terminal 4: Flower (Monitoring)
cd mp4totext-backend
celery -A app.celery_app flower
# Flower UI: http://localhost:5555
```

#### Seçenek B: Docker Compose (Önerilen)

```bash
# Tüm servisleri başlat
docker-compose -f docker-compose.dev.yml up -d

# Logları takip et
docker-compose -f docker-compose.dev.yml logs -f

# Servisleri durdur
docker-compose -f docker-compose.dev.yml down
```

### 3. Mobile App ile Test

```bash
# Mobile klasörüne git
cd ../mp4totext-mobile

# Başlat
npm install --legacy-peer-deps
npm start

# Android emulator için backend URL:
# API_BASE_URL = 'http://10.0.2.2:8002/api/v1'

# Fiziksel cihaz için:
# API_BASE_URL = 'http://YOUR_LOCAL_IP:8002/api/v1'
```

---

## 🚀 Production Deployment

### Adım 1: Environment Hazırlığı

```bash
# Production environment dosyasını düzenle
cp .env.example .env.production

# Gerekli değişkenleri ayarla:
# - SECRET_KEY (güvenli random string)
# - REDIS_PASSWORD (güçlü şifre)
# - DATABASE_URL (PostgreSQL connection)
# - STORAGE_* (S3/MinIO credentials)
# - API keys (Gemini, OpenAI, etc.)
# - FLOWER_PASSWORD
```

**Güvenlik Kontrol Listesi**:
- [ ] SECRET_KEY değiştirildi mi?
- [ ] REDIS_PASSWORD güçlü mü?
- [ ] Database şifresi güvenli mi?
- [ ] API keys production keys mi?
- [ ] CORS_ORIGINS production URLs ile mi?
- [ ] Storage SSL aktif mi (STORAGE_SECURE=True)?
- [ ] Flower password güçlü mü?

### Adım 2: Database Migration

```bash
# PostgreSQL veritabanı oluştur
createdb mp4totext_production

# Migration'ları çalıştır
alembic upgrade head

# Veya manuel:
python add_credits_system.py
python add_ai_model_pricing.py
# ... diğer migration scriptleri
```

### Adım 3: Docker ile Production Deploy

```bash
# Production docker-compose ile başlat
docker-compose -f docker-compose.prod.yml up -d

# Scale specific workers if needed
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker_high=10

# Health check
docker-compose -f docker-compose.prod.yml ps
```

### Adım 4: Monitoring Setup

```bash
# Flower UI'a eriş
http://your-server-ip:5555
# User: admin (değiştir)
# Pass: FLOWER_PASSWORD (.env.production'dan)

# Health check endpoint
curl http://your-server-ip:8002/health

# Worker status
docker-compose -f docker-compose.prod.yml exec celery_worker_high celery -A app.celery_app inspect active
```

---

## 📈 Ölçeklendirme Stratejisi

### 1000 Concurrent User Hedefi

#### Hesaplamalar:

```
Kullanıcı Profili:
- 1000 kullanıcı
- Her kullanıcı 10 dakikada 1 upload (ortalama)
- Upload → Transcription → AI Enhancement pipeline

Queue Dağılımı:
- %50 transcription (500 concurrent)
- %30 AI enhancement (300 concurrent)
- %20 upload/critical (200 concurrent)

Worker İhtiyacı:
- Transcription: Ortalama 10 dakika/task
  → 500 task / 10 dakika = 50 worker minimum
  → Production: 60 worker (5 replica × 12)

- AI Enhancement: Ortalama 2 dakika/task
  → 300 task / 2 dakika = 150 worker/dakika
  → 30-40 worker yeterli
  → Production: 40 worker (4 replica × 10)

- Upload: Ortalama 30 saniye/task
  → 200 task / 0.5 dakika = 400 worker/dakika
  → 10-20 worker yeterli
  → Production: 18 worker (3 replica × 6)
```

#### Ölçeklendirme Komutları:

```bash
# Transcription workers'ı artır (en yoğun queue)
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker_high=10

# AI enhancement workers'ı artır
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker_default=6

# Tüm worker sayılarını göster
docker-compose -f docker-compose.prod.yml ps
```

### Resource Gereksinimleri (1000 User)

#### Minimum Server Specs:
- **CPU**: 32 cores (64 with hyperthreading)
- **RAM**: 64GB
- **Storage**: 500GB SSD (+ S3/MinIO for files)
- **Network**: 1 Gbps

#### Önerilen Dağılım:
```
3× Server (High Priority - Transcription)
- 16 core CPU
- 32GB RAM
- GPU optional (faster-whisper with CUDA)

2× Server (Default Priority - AI Enhancement)
- 8 core CPU
- 16GB RAM

1× Server (Critical + Low Priority)
- 8 core CPU
- 16GB RAM

1× Redis Server
- 4 core CPU
- 8GB RAM
- Persistent storage

1× Database Server (PostgreSQL)
- 8 core CPU
- 32GB RAM
- SSD storage
```

---

## 📊 Monitoring ve Bakım

### Flower Dashboard

```bash
# Flower'a eriş
http://your-server:5555

# Metrics:
- Active tasks per queue
- Worker status
- Task execution times
- Failure rates
```

### Health Checks

```python
# app/utils/monitoring.py'den health check
from app.utils.monitoring import health_check

status = health_check()
# Returns:
# {
#   'status': 'healthy',
#   'uptime_seconds': 3600,
#   'success_rate': 95.2,
#   'tasks': {'completed': 1500, 'failed': 80, ...},
#   'queues': {...}
# }
```

### Log Monitoring

```bash
# Worker logs
docker-compose -f docker-compose.prod.yml logs -f celery_worker_high

# Backend logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Redis logs
docker-compose -f docker-compose.prod.yml logs -f redis
```

### Periodic Tasks (Maintenance)

```python
# app/workers/tasks/low_priority.py
# Otomatik çalışan maintenance tasks:

# Günlük:
- cleanup_temp_files_task()
- cleanup_old_transcriptions_task(days_old=90)

# Haftalık:
- optimize_database_task()
- generate_usage_report_task()
```

---

## 🔧 Troubleshooting

### Problem 1: Workers crash oluyor

```bash
# Worker loglarını kontrol et
docker-compose -f docker-compose.prod.yml logs celery_worker_high

# Memory kullanımı kontrol
docker stats

# Çözüm: worker_max_tasks_per_child değerini düşür
# config/production.py'de:
worker_max_tasks_per_child = 500  # Varsayılan: 1000
```

### Problem 2: Redis connection errors

```bash
# Redis bağlantısını test et
redis-cli -h redis-host -p 6379 -a PASSWORD ping

# Connection pool ayarları
# config/base.py'de:
broker_connection_max_retries = 30
broker_heartbeat = 30
```

### Problem 3: Task'lar queue'da bekliyor

```bash
# Queue durumunu kontrol et
celery -A app.celery_app inspect active_queues

# Worker sayısını artır
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker_high=10

# Veya autoscale ayarlarını optimize et
# config/production.py:
worker_autoscale = (20, 8)  # Max 20, min 8
```

### Problem 4: Slow performance

```bash
# Task execution metrics kontrol
# Flower UI: Tasks > Running

# Prefetch multiplier'ı artır (daha fazla task pre-load)
# config/production.py:
worker_prefetch_multiplier = 8  # Varsayılan: 4

# Database query optimization
# Database indexes kontrol et
```

---

## 📝 Load Testing

### Test Script Çalıştırma

```bash
# Load test script'ini çalıştır
cd tests
python load_test.py

# Customize:
# - TEST_USERS_COUNT = 1000
# - CONCURRENT_UPLOADS = 50
# - API_BASE_URL = "http://localhost:8002/api/v1"
```

### Test Sonuçları Analizi

```
Expected Results (1000 users):
- Login Success Rate: > 95%
- Upload Success Rate: > 90%
- Transcription Completion: > 85%
- Average Upload Time: < 5s
- Throughput: > 10 uploads/second
```

---

## 🌐 Cloud Deployment Options

### AWS Deployment

```yaml
# ECS Task Definition için:
- Fargate containers
- ElastiCache Redis (cluster mode)
- RDS PostgreSQL
- S3 for file storage
- Application Load Balancer
- CloudWatch for monitoring

Estimated Cost (1000 users):
- ECS Fargate: $800-1200/month
- ElastiCache: $200-400/month
- RDS: $300-500/month
- S3: $50-100/month
Total: ~$1500-2000/month
```

### DigitalOcean Deployment

```yaml
# App Platform:
- 3× Professional-L droplets (16GB RAM)
- Managed Redis (4GB)
- Managed PostgreSQL (4GB)
- Spaces for storage

Estimated Cost:
- Droplets: $144 × 3 = $432/month
- Redis: $60/month
- PostgreSQL: $60/month
- Spaces: $20/month
Total: ~$570/month
```

### Docker Swarm (Self-hosted)

```bash
# Swarm init
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml mp4totext

# Scale services
docker service scale mp4totext_celery_worker_high=10
```

---

## 📞 Support ve Güncellemeler

- **Documentation**: Bu dosya
- **Monitoring**: Flower UI (http://server:5555)
- **Health Check**: http://server:8002/health
- **Logs**: `docker-compose logs -f`

**Önemli Notlar**:
1. Production'a geçmeden önce staging ortamında test edin
2. Backup stratejisi kurun (database + storage)
3. SSL sertifikası yapılandırın (Let's Encrypt)
4. Rate limiting ekleyin (DDoS koruması)
5. Log rotation yapılandırın
6. Alert sistemi kurun (email/slack)

---

**Son Güncelleme**: 2024
**Versiyon**: 1.0
**Lisans**: Proprietary
