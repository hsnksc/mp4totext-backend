# 🚀 Backend Başlatma Talimatları

## Adım 1: Backend'i Ayrı Terminalde Başlat

**Yeni bir PowerShell penceresi aç** ve şu komutu çalıştır:

```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext-backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Bu mesajları göreceksin:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
🌐 Allowed CORS origins: [...]
✅ WebSocket manager initialized
✅ Database initialized successfully
Application startup complete.
```

**⚠️ Bu terminali kapatma - backend çalışırken açık kalmalı!**

---

## Adım 2: Browser Cache'i Temizle

**Chrome/Edge'de:**
1. `Ctrl + Shift + Delete` bas
2. **"Cached images and files"** seç
3. **"All time"** seç
4. **Clear data** tıkla

**VEYA:** Incognito pencere aç (`Ctrl + Shift + N`)

---

## Adım 3: Upload Testi

1. **Browser'da aç:** http://localhost:5173
2. **Login ol** (JWT token alması için)
3. **Upload sayfasına git**
4. **Ses/video dosyası seç** (text dosyası değil!)
5. **Upload butonuna tıkla**

---

## Adım 4: Logları İzle

Backend terminalinde şunları göreceksin:

### ✅ Başarılı upload:
```
INFO: 127.0.0.1:52123 - "POST /api/v1/transcriptions/ HTTP/1.1" 201 Created
🚀 Celery task 1234-5678... started for transcription ID: 42
```

### ✅ Celery yoksa (fallback):
```
⚠️ Celery broker unavailable, running synchronously
INFO: 127.0.0.1:52123 - "POST /api/v1/transcriptions/ HTTP/1.1" 201 Created
```

### ✅ Validation hatası (CORS ile):
```
INFO: 127.0.0.1:52123 - "POST /api/v1/transcriptions/ HTTP/1.1" 422 Unprocessable Entity
```

**Artık hiçbir hata "Access to XMLHttpRequest blocked by CORS" demeyecek!** 🎉

---

## Sorun Giderme

### Backend başlamıyor?
```powershell
# Docker kontrol:
docker ps

# Port kontrol:
netstat -ano | findstr :8000

# Port dolu mu? Kapat:
Stop-Process -Id <PID> -Force
```

### Frontend'te hala CORS hatası?
```powershell
# Diagnostic script çalıştır:
cd C:\Users\hasan\OneDrive\Desktop\mp4totext-backend
.\debug_backend_clean.ps1
```

**Tüm checkler ✅ olmalı!**
