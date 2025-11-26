# 🎯 MP4toText - Scalable Architecture Quick Start

## ✅ Tamamlanan Yapılandırma

### 📁 Yeni Dosya Yapısı

```
mp4totext-backend/
├── app/
│   ├── config/                      # ✨ YENİ - Environment-based config
│   │   ├── __init__.py
│   │   ├── base.py                 # Base configuration
│   │   ├── development.py          # Dev: 2 workers
│   │   ├── staging.py              # Staging: 4-6 workers
│   │   └── production.py           # Prod: 8-12 workers
│   │
│   ├── workers/
│   │   ├── tasks/                  # ✨ YENİ - Priority-based tasks
│   │   │   ├── critical.py        # Upload, file ops (priority=10)
│   │   │   ├── high_priority.py   # Transcription (priority=7)
│   │   │   ├── default_priority.py # AI enhancement (priority=5)
│   │   │   └── low_priority.py    # Cleanup (priority=2)
│   │   └── transcription_worker.py # Mevcut worker
│   │
│   └── utils/                      # ✨ YENİ - Monitoring
│       ├── __init__.py
│       └── monitoring.py           # Task metrics, health checks
│
├── tests/
│   └── load_test.py               # ✨ YENİ - 1000 user load test
│
├── docker-compose.dev.yml         # Mevcut (dev environment)
├── docker-compose.prod.yml        # ✨ YENİ - Production with scaling
├── .env.development              # ✨ YENİ - Dev environment vars
├── .env.production               # ✨ YENİ - Prod environment vars
└── DEPLOYMENT_GUIDE.md           # ✨ YENİ - Kapsamlı deployment rehberi
```

---

## 🚀 Hızlı Başlangıç

### 1. Development Mode

```bash
# Backend klasöründe
cd mp4totext-backend

# Environment variables (API keys ekle)
cp .env.development .env

# Manuel başlatma
python run.py                                    # Terminal 1: Backend
redis-server                                      # Terminal 2: Redis
celery -A app.celery_app worker -l info         # Terminal 3: Worker
celery -A app.celery_app flower                 # Terminal 4: Monitoring

# VEYA Docker ile (Önerilen)
docker-compose -f docker-compose.dev.yml up -d

# Flower Monitoring UI
http://localhost:5555
```

### 2. Production Mode (1000 Kullanıcı için)

```bash
# Production environment ayarla
cp .env.example .env.production
# .env.production dosyasını düzenle (güvenlik ayarları)

# Docker ile başlat
docker-compose -f docker-compose.prod.yml up -d

# Worker kapasitesi:
# - 3 replica × 6 = 18 critical workers (upload)
# - 5 replica × 12 = 60 high workers (transcription)
# - 4 replica × 10 = 40 default workers (AI enhancement)
# - 1 replica × 4 = 4 low workers (cleanup)
# TOPLAM: 122 concurrent workers

# Scale up if needed
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker_high=10
```

---

## 📊 Priority-Based Queue Sistemi

### Queue Yapısı

| Queue | Priority | İşlemler | Worker Sayısı (Prod) |
|-------|----------|----------|----------------------|
| **critical** | 10 | Upload, File validation, Real-time ops | 18 (3×6) |
| **high** | 7 | Whisper transcription, Speaker recognition | 60 (5×12) |
| **default** | 5 | AI enhancement, Translation, Lecture notes | 40 (4×10) |
| **low** | 2 | Cleanup, Maintenance, Batch operations | 4 (1×4) |

### Otomatik Task Routing

```python
# Task'lar otomatik olarak doğru queue'ya yönlendirilir:

# app/config/base.py'de tanımlı:
'task_routes': {
    'app.workers.tasks.upload.*': {'queue': 'critical'},
    'app.workers.process_transcription': {'queue': 'high'},
    'app.workers.tasks.ai_enhancement.*': {'queue': 'default'},
    'app.workers.tasks.cleanup.*': {'queue': 'low'},
}
```

---

## 📈 Monitoring ve Health Checks

### Flower Dashboard

```bash
# Flower UI'a eriş
http://localhost:5555

# Görebilecekleriniz:
- Active/completed/failed tasks
- Worker durumu (online/offline)
- Queue uzunlukları
- Task execution times
- Retry statistikleri
```

### Programmatic Health Check

```python
from app.utils.monitoring import health_check, get_current_metrics

# Health status
status = health_check()
# {
#   'status': 'healthy',
#   'uptime_seconds': 3600,
#   'success_rate': 95.5,
#   'tasks': {...},
#   'queues': {...}
# }

# Current metrics
metrics = get_current_metrics()
# {
#   'tasks_completed': 1500,
#   'tasks_failed': 80,
#   'active_tasks': 25,
#   ...
# }
```

---

## 🧪 Load Testing

### 1000 Kullanıcı Simülasyonu

```bash
# Test script'i çalıştır
cd tests
python load_test.py

# Test parametreleri (load_test.py'de):
TEST_USERS_COUNT = 1000          # 1000 kullanıcı
CONCURRENT_UPLOADS = 50          # 50'şer batch'ler halinde
TEST_AUDIO_FILE = "test_audio.mp3"  # Test dosyası

# Sonuçlar:
- Login success rate
- Upload success rate
- Transcription completion rate
- Average upload time
- Throughput (uploads/second)
```

### Beklenen Performans (1000 User)

```
✅ Hedef Metrikler:
- Login Success: > 95%
- Upload Success: > 90%
- Transcription Completion: > 85%
- Upload Time: < 5 saniye
- Throughput: > 10 upload/saniye
```

---

## 🔧 Configuration Özeti

### Development (Local)

```python
# app/config/development.py
worker_concurrency = 2           # Hafif
worker_pool = 'solo'             # Debugging kolay
worker_autoscale = None          # Fixed concurrency
```

### Staging (Test)

```python
# app/config/staging.py
worker_concurrency = 4
worker_pool = 'prefork'          # Multi-process
worker_autoscale = (6, 2)        # Dynamic: 2-6 workers
```

### Production (1000+ Users)

```python
# app/config/production.py
worker_concurrency = 8
worker_pool = 'prefork'
worker_autoscale = (12, 4)       # Dynamic: 4-12 workers
worker_prefetch_multiplier = 4   # High throughput
worker_max_tasks_per_child = 1000  # Restart after 1000 tasks
```

---

## 📝 Kullanım Örnekleri

### Backend'den Task Trigger Etme

```python
# Critical priority task (upload)
from app.workers.tasks.critical import validate_file_task
result = validate_file_task.delay(file_id, file_path)

# High priority task (transcription)
from app.workers.tasks.high_priority import process_transcription
result = process_transcription.delay(transcription_id, user_id)

# Default priority task (AI enhancement)
from app.workers.tasks.default_priority import enhance_text_task
result = enhance_text_task.delay(transcription_id, text, 'gemini', 'gemini-2.0-flash-lite')

# Low priority task (cleanup)
from app.workers.tasks.low_priority import cleanup_temp_files_task
result = cleanup_temp_files_task.delay()
```

### Task Status Kontrolü

```python
# Task result'ı al
task_id = result.id
result_data = result.get(timeout=60)

# Task durumu kontrol et
if result.ready():
    print("Task completed")
elif result.failed():
    print("Task failed")
else:
    print("Task still processing")
```

---

## 🔐 Güvenlik Kontrol Listesi

Production'a geçmeden önce:

- [ ] `.env.production` dosyasında SECRET_KEY değiştirildi
- [ ] REDIS_PASSWORD güçlü şifre ile ayarlandı
- [ ] Database şifresi güvenli
- [ ] API keys production credentials ile değiştirildi
- [ ] CORS_ORIGINS production URLs ile güncellendi
- [ ] STORAGE_SECURE=True (SSL aktif)
- [ ] FLOWER_PASSWORD güçlü şifre
- [ ] Firewall kuralları yapılandırıldı
- [ ] SSL sertifikası kuruldu
- [ ] Log rotation yapılandırıldı
- [ ] Backup stratejisi oluşturuldu

---

## 📚 Dokümantasyon

- **Detaylı Deployment**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **API Documentation**: `/docs` endpoint (FastAPI Swagger)
- **Monitoring**: Flower UI (http://server:5555)
- **Health Check**: `/health` endpoint

---

## 🆘 Hızlı Troubleshooting

### Workers çalışmıyor
```bash
# Worker loglarını kontrol et
docker-compose -f docker-compose.prod.yml logs -f celery_worker_high

# Redis bağlantısını test et
redis-cli -h localhost -p 6379 ping
```

### Task'lar queue'da bekliyor
```bash
# Queue durumunu kontrol
celery -A app.celery_app inspect active_queues

# Worker sayısını artır
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker_high=10
```

### Memory kullanımı yüksek
```bash
# Resource kullanımı
docker stats

# Çözüm: config/production.py'de
worker_max_tasks_per_child = 500  # Daha sık restart
```

---

## 🎓 Sonraki Adımlar

1. **Development Test**: Local'de test edin
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

2. **Load Test**: 1000 kullanıcı simülasyonu
   ```bash
   cd tests && python load_test.py
   ```

3. **Staging Deploy**: Test ortamında deneyin
   ```bash
   ENVIRONMENT=staging docker-compose -f docker-compose.prod.yml up
   ```

4. **Production Deploy**: Canlıya alın
   ```bash
   # .env.production'ı düzenle
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Monitor**: Flower UI ve health checks ile takip edin
   ```bash
   # Flower: http://server:5555
   # Health: http://server:8002/health
   ```

---

**✅ Sistem Hazır!**

1000+ kullanıcı için ölçeklenebilir, production-ready mimari oluşturuldu.

**Kapasite**:
- 🚀 122 concurrent workers
- ⚡ Priority-based routing
- 📊 Real-time monitoring
- 🔄 Auto-scaling ready
- 🛡️ Production-grade security

**İletişim**: Sorularınız için DEPLOYMENT_GUIDE.md'ye bakın.
