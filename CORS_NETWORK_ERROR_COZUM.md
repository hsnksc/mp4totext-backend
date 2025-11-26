# 🔧 CORS ve Network Error Çözüm Rehberi

## 📋 Problem Özeti

Frontend (React/Vite) ile backend (FastAPI) arasında CORS hatası:
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/transcriptions/' 
from origin 'http://localhost:5173' has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

Ardından:
```
POST http://localhost:8000/api/v1/transcriptions/ net::ERR_FAILED 500 (Internal Server Error)
```

## 🎯 Gerçek Sorun

**CORS başlıkları doğru yapılandırılmış** ancak backend **500 Internal Server Error** döndürdüğü için tarayıcı CORS hatası gösteriyor. Asıl sorun backend'de!

## ✅ Yapılan Düzeltmeler

### 1. CORS Middleware Yapılandırması (`app/main.py`)

```python
from app.config import get_settings

settings = get_settings()
settings_cors_origins = getattr(settings, "CORS_ORIGINS", []) or []

# Compute CORS origins dynamically so credentials can be used safely.
default_cors_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
}

allow_origin_list = sorted(set(settings_cors_origins) | default_cors_origins)

# Configure CORS (must be registered before routers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origin_list,  # Wildcard yerine spesifik origin listesi
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Neden bu önemli?**
- `allow_credentials=True` kullanırken `allow_origins=["*"]` çalışmaz
- Tarayıcılar güvenlik için spesifik origin listesi bekler
- Hem `localhost` hem `127.0.0.1` için ayrı girişler gerekli

### 2. Celery Hata Yönetimi (`app/api/transcription.py`)

```python
if CELERY_AVAILABLE:
    try:
        task = process_transcription_task.delay(transcription.id)
        logger.info(
            "🚀 Celery task started: %s for transcription %s",
            task.id,
            transcription.id,
        )
    except Exception as celery_error:
        logger.error(
            "Celery dispatch failed for transcription %s: %s",
            transcription.id,
            celery_error,
            exc_info=True,
        )
        if settings.is_development:
            logger.warning(
                "Falling back to synchronous processing for transcription %s",
                transcription.id,
            )
            process_transcription_task.apply(args=(transcription.id,))
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Background processing service unavailable. Please try again later.",
            )
```

**Neden bu önemli?**
- Celery broker (Redis) bağlantı hatası 500 error'a neden oluyor
- Development modunda synchronous fallback ile iş devam eder
- Production'da 503 Service Unavailable döner (daha açıklayıcı)

## 🔍 Tanı Adımları

### 1. CORS Başlıklarını Doğrula

**Preflight Request Test:**
```powershell
curl.exe -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ `
  -H "Origin: http://localhost:5173" `
  -H "Access-Control-Request-Method: POST"
```

**Beklenen Sonuç:**
```
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:5173
access-control-allow-credentials: true
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
```

✅ **Eğer yukarıdaki başlıkları görüyorsanız, CORS doğru yapılandırılmış!**

### 2. Backend Loglarını İncele

Backend terminalinde (uvicorn çalıştığı yerde) şu hataları arayın:

**Celery/Redis Bağlantı Hatası:**
```
ConnectionRefusedError: [Errno 111] Connection refused
kombu.exceptions.OperationalError: Error 111 connecting to localhost:6379
```

**Çözüm:** Redis container'ını başlat
```powershell
docker start mp4totext-redis
```

**Database Bağlantı Hatası:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Çözüm:** PostgreSQL container'ını başlat
```powershell
docker start mp4totext-postgres
```

### 3. Servis Durumlarını Kontrol Et

```powershell
# Docker container'larını kontrol et
docker ps --filter "name=mp4totext" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Backend health check
curl.exe http://localhost:8000/health

# Redis bağlantısını test et
docker exec mp4totext-redis redis-cli -a dev_redis_123 ping
```

## 🚀 Sorun Giderme Checklist

### Backend Tarafı

- [ ] **Redis container çalışıyor mu?**
  ```powershell
  docker ps | Select-String "redis"
  ```

- [ ] **PostgreSQL container çalışıyor mu?**
  ```powershell
  docker ps | Select-String "postgres"
  ```

- [ ] **Backend başlatıldı mı?**
  ```powershell
  curl.exe http://localhost:8000/health
  ```

- [ ] **CORS middleware doğru sırada mı?** (Router'lardan ÖNCE olmalı)
  
- [ ] **.env dosyası doğru mu?**
  - `DATABASE_URL` doğru mu?
  - `REDIS_URL` doğru mu?
  - `CELERY_BROKER_URL` doğru mu?

### Frontend Tarafı

- [ ] **Frontend hangi portta çalışıyor?**
  ```powershell
  curl.exe -s http://localhost:5173 | Select-String "<!doctype"
  ```

- [ ] **API base URL doğru mu?** (`src/config/api.ts`)
  ```typescript
  baseURL: 'http://localhost:8000'
  ```

- [ ] **Tarayıcı cache temizlendi mi?**
  - `Ctrl + Shift + Delete` → "Cached images and files"
  - Veya Incognito/Private window kullan

- [ ] **JWT token geçerli mi?**
  - Login olun ve yeni token alın
  - Token'ın localStorage'da olduğunu kontrol edin

## 🔧 Adım Adım Çözüm

### 1. Docker Container'ları Başlat

```powershell
# Redis başlat
docker start mp4totext-redis

# PostgreSQL başlat
docker start mp4totext-postgres

# Kontrol et
docker ps --filter "name=mp4totext"
```

### 2. Backend'i Başlat

```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext-backend

# Virtual environment'ı aktive et ve backend'i başlat
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Beklenen Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Database initialized successfully
✅ Database connection successful
```

### 3. Frontend'i Başlat

```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext-web

npm run dev
```

**Çıktıda hangi portu kullandığını not edin:**
```
➜  Local:   http://localhost:5173/
```

### 4. Tarayıcı Cache'ini Temizle

**Seçenek 1: Cache Temizleme**
1. `Ctrl + Shift + Delete`
2. "Cached images and files" işaretle
3. "Clear data"

**Seçenek 2: Incognito/Private Window**
1. `Ctrl + Shift + N` (Chrome/Edge)
2. `http://localhost:5173` (veya 5174) aç

### 5. Test Et

1. Frontend'de login olun (yeni JWT token alın)
2. Upload sayfasına gidin
3. Bir audio/video dosyası seçin
4. Upload butonuna tıklayın

## 📊 Hata Kodları ve Anlamları

| Kod | Anlam | Çözüm |
|-----|-------|-------|
| **CORS Error** | Tarayıcı CORS başlığı görmüyor | Backend loglarına bak, asıl hata 500/503 |
| **500 Internal Server Error** | Backend'de beklenmedik hata | Backend terminalindeki stack trace'i incele |
| **503 Service Unavailable** | Celery broker bağlanamıyor | Redis container'ını başlat |
| **401 Unauthorized** | Token geçersiz/yok | Yeniden login ol |
| **422 Unprocessable Entity** | Request body hatalı | File ID veya format kontrol et |

## 🐛 Yaygın Hatalar ve Çözümleri

### Hata 1: "No 'Access-Control-Allow-Origin' header"

**Sebep:** Backend 500 error döndüğü için CORS başlıkları gönderilmiyor

**Çözüm:** Backend loglarındaki gerçek hatayı bul ve çöz

### Hata 2: "ConnectionRefusedError: [Errno 111]"

**Sebep:** Redis container çalışmıyor

**Çözüm:**
```powershell
docker start mp4totext-redis
```

### Hata 3: "No module named 'uvicorn'"

**Sebep:** Yanlış Python environment veya eksik paket

**Çözüm:**
```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext-backend
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Hata 4: "Port 5173 is in use"

**Sebep:** Başka bir frontend instance çalışıyor

**Çözüm:**
```powershell
# Tüm node process'lerini durdur
Get-Process -Name "node" | Stop-Process -Force

# Frontend'i yeniden başlat
npm run dev
```

### Hata 5: "Could not validate credentials"

**Sebep:** JWT token süresi dolmuş veya geçersiz

**Çözüm:**
1. Frontend'de logout yap
2. Yeniden login ol
3. Yeni token ile tekrar dene

## 🔐 .env Dosyası Örnek Yapılandırma

```env
# Backend (.env)
SECRET_KEY=your-super-secret-key-change-in-production
JWT_SECRET=your-jwt-secret-key-change-in-production

DATABASE_URL=postgresql://dev_user:dev_password_123@localhost:5432/mp4totext_dev

REDIS_URL=redis://:dev_redis_123@localhost:6379/0
CELERY_BROKER_URL=redis://:dev_redis_123@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:dev_redis_123@localhost:6379/2

CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174

GEMINI_API_KEY=your-gemini-api-key-here
```

## 📞 Hala Çalışmıyor mu?

Aşağıdaki bilgileri toplayın ve log olarak kaydedin:

### 1. Backend Terminal Output
```powershell
# Backend başlatırken tüm çıktıyı kaydet
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1
```

### 2. Frontend Console Errors
- Tarayıcıda F12 → Console → Hataları kopyala

### 3. Network Tab
- Tarayıcıda F12 → Network
- Upload dene
- Başarısız olan request'e sağ tık → "Copy as cURL"

### 4. Docker Status
```powershell
docker ps --all --filter "name=mp4totext" > docker_status.txt
```

### 5. CORS Preflight Test
```powershell
curl.exe -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ `
  -H "Origin: http://localhost:5173" `
  -H "Access-Control-Request-Method: POST" > cors_test.txt 2>&1
```

## 🎓 Öğrenilen Dersler

1. **CORS hatası her zaman CORS problemi değildir**
   - Genellikle backend'deki 500/503 hatasının bir sonucudur
   - Önce backend loglarına bakın

2. **`allow_credentials=True` ile `allow_origins=["*"]` çalışmaz**
   - Tarayıcılar güvenlik için spesifik origin listesi gerektirir
   - Hem `localhost` hem `127.0.0.1` için ayrı girişler ekleyin

3. **Celery broker bağlantı hatası 500 error'a neden olur**
   - Development modunda synchronous fallback kullanın
   - Production'da 503 Service Unavailable dönün

4. **Tarayıcı cache CORS başlıklarını saklar**
   - Her CORS değişikliğinden sonra cache temizleyin
   - Veya Incognito/Private window kullanın

## 📚 Ek Kaynaklar

- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Understanding CORS](https://web.dev/cross-origin-resource-sharing/)
- [FastAPI Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)

---

**Son Güncelleme:** 21 Ekim 2025
**Durum:** ✅ CORS yapılandırması tamamlandı, Celery fallback eklendi
