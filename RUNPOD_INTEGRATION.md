# RunPod Serverless Entegrasyonu

## 🚀 Genel Bakış

MP4toText backend'ine RunPod Serverless desteği eklendi. Admin kullanıcılar artık transkripsiyon işlemlerini:
- **Local** (Faster-Whisper) - Kendi sunucunuzda
- **RunPod** (Cloud) - RunPod serverless endpoint'inde

arasında seçerek yapabilir.

## 📋 Yapılan Değişiklikler

### 1. Settings Konfigürasyonu (`app/settings.py`)
```python
# RunPod Serverless ayarları eklendi
USE_RUNPOD: bool = Field(default=False, env="USE_RUNPOD")
RUNPOD_API_KEY: Optional[str] = Field(default=None, env="RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID: Optional[str] = Field(default=None, env="RUNPOD_ENDPOINT_ID")
RUNPOD_TIMEOUT: int = Field(default=300, env="RUNPOD_TIMEOUT")
```

### 2. RunPod Service (`app/services/runpod_service.py`)
Yeni servis dosyası oluşturuldu:
- ✅ Audio dosyası base64 encoding
- ✅ Asenkron job submission (`/run` endpoint)
- ✅ Job status polling (exponential backoff)
- ✅ Whisper transcription result parsing
- ✅ Health check endpoint
- ✅ Error handling ve timeout yönetimi

### 3. Transcription Worker Güncelleme (`app/workers/transcription_worker.py`)
Worker'da RunPod/Local seçimi eklendi:
```python
if settings.USE_RUNPOD:
    # RunPod Serverless kullan
    result = runpod_service.transcribe_audio(...)
else:
    # Local Faster-Whisper kullan
    result = processor.process_file(...)
```

### 4. Admin API Endpoints (`app/api/admin.py`)
Yeni admin panel endpoint'leri:

#### GET `/api/v1/admin/transcription-provider`
Mevcut transkripsiyon provider bilgisini döner:
```json
{
  "provider": "local",  // veya "runpod"
  "use_runpod": false,
  "runpod_configured": true,
  "runpod_healthy": true
}
```

#### POST `/api/v1/admin/transcription-provider`
Provider ayarlarını günceller:
```json
{
  "use_runpod": true,
  "runpod_api_key": "rpa_...",
  "runpod_endpoint_id": "q3arg0kg6iadou",
  "runpod_timeout": 300
}
```

#### GET `/api/v1/admin/runpod/health`
RunPod endpoint sağlık kontrolü:
```json
{
  "enabled": true,
  "configured": true,
  "status": "healthy",
  "data": {
    "jobs": {...},
    "workers": {...}
  }
}
```

### 5. Environment Variables (`.env`)
```bash
# RunPod Serverless Configuration
USE_RUNPOD=false
RUNPOD_API_KEY=rpa_W359E4SWUIQ16V608TYF2L8ZFE5NE45C5GOJ88HBtzrjap
RUNPOD_ENDPOINT_ID=q3arg0kg6iadou
RUNPOD_TIMEOUT=300
```

## 🔧 Kullanım

### Admin Olarak Provider Değiştirme

1. **Admin token ile login olun**
2. **Mevcut ayarları kontrol edin:**
```bash
GET /api/v1/admin/transcription-provider
Authorization: Bearer <admin_token>
```

3. **RunPod'a geçiş yapın:**
```bash
POST /api/v1/admin/transcription-provider
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "use_runpod": true,
  "runpod_api_key": "rpa_W359E4SWUIQ16V608TYF2L8ZFE5NE45C5GOJ88HBtzrjap",
  "runpod_endpoint_id": "q3arg0kg6iadou",
  "runpod_timeout": 300
}
```

4. **Backend ve Celery worker'ları yeniden başlatın:**
```bash
# Backend
python run.py

# Celery workers
.\start_celery.ps1
```

### RunPod Endpoint Health Check
```bash
GET /api/v1/admin/runpod/health
Authorization: Bearer <admin_token>
```

Response:
```json
{
  "enabled": true,
  "configured": true,
  "status": "healthy",
  "data": {
    "jobs": {
      "completed": 150,
      "failed": 2,
      "inProgress": 3,
      "inQueue": 5,
      "retried": 1
    },
    "workers": {
      "idle": 2,
      "running": 5
    }
  }
}
```

## 📊 RunPod vs Local Karşılaştırma

| Özellik | Local (Faster-Whisper) | RunPod Serverless |
|---------|------------------------|-------------------|
| **Hız** | Orta (CPU/GPU'ya bağlı) | Çok Hızlı (GPU cluster) |
| **Maliyet** | Sunucu maliyeti | Pay-per-use |
| **Ölçeklenebilirlik** | Sınırlı (donanıma bağlı) | Otomatik (unlimited) |
| **Kurulum** | Karmaşık (dependencies) | Kolay (API key) |
| **Speaker Recognition** | ✅ Desteklenir | ❌ Henüz yok |
| **Offline Çalışma** | ✅ Evet | ❌ İnternet gerekli |

## 🔐 Güvenlik

- ✅ Admin endpoint'leri `require_admin` dependency ile korunuyor
- ✅ RunPod API key `.env` dosyasında güvenli tutuluyor
- ✅ Timeout ayarları ile sonsuz bekleme önleniyor
- ✅ Health check ile endpoint durumu izleniyor

## 🐛 Sorun Giderme

### RunPod bağlantı hatası
```python
# Error: RunPod connection test failed
```
**Çözüm:**
1. API key'in doğru olduğundan emin olun
2. Endpoint ID'nin doğru olduğundan emin olun
3. `/api/v1/admin/runpod/health` ile endpoint durumunu kontrol edin

### Timeout hatası
```python
# Error: RunPod job timed out after 300 seconds
```
**Çözüm:**
- `RUNPOD_TIMEOUT` değerini artırın (örn: 600 saniye)
- Büyük dosyalar için daha uzun timeout gerekebilir

### Speaker recognition çalışmıyor (RunPod)
**Not:** RunPod şu anda sadece transkripsiyon yapıyor, speaker recognition local'de çalışır.
**Çözüm:** Speaker recognition gerekiyorsa local mode kullanın.

## 📝 TODO / İyileştirmeler

- [ ] RunPod endpoint'ine speaker recognition desteği ekle
- [ ] Streaming output support (real-time transcription)
- [ ] Batch processing (multiple files)
- [ ] Cost tracking (RunPod usage monitoring)
- [ ] Frontend admin panel UI
- [ ] Auto-fallback (RunPod fail → Local)

## 📚 Referanslar

- [RunPod Serverless Docs](https://docs.runpod.io/serverless/endpoints/send-requests)
- [RunPod Python SDK](https://github.com/runpod/runpod-python)
- [Faster-Whisper Documentation](https://github.com/guillaumekln/faster-whisper)
