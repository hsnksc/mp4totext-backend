# 🚀 MP4toText Başlatma Rehberi

## ✅ Tüm Sorunlar Çözüldü!

### 🔧 Yapılan Düzeltmeler:

1. **Database Yolu**: Tek database (`mp4totext.db`) kullanılıyor
2. **Dotenv Import**: Tüm dosyalarda `.env` otomatik yükleniyor
3. **Port Standardizasyonu**: Backend 8002, Frontend 5173
4. **Başlatma Scriptleri**: Doğru venv Python kullanıyor

---

## 📦 Gereksinimler

- ✅ **Redis**: Port 6379'da çalışmalı
- ✅ **Python 3.13**: Backend venv'inde yüklü
- ✅ **Node.js**: Frontend için

---

## 🎯 Hızlı Başlatma

### 1️⃣ Backend Başlatma

**Yöntem 1: PowerShell (ÖNERİLEN)**
```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\start_backend.ps1
```

**Yöntem 2: Batch Dosyası**
```cmd
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
start_backend.bat
```

**Yöntem 3: Manuel Komut**
```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

### 2️⃣ Celery Worker Başlatma

**Yöntem 1: PowerShell (ÖNERİLEN)**
```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\start_celery.ps1
```

**Yöntem 2: Batch Dosyası**
```cmd
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
start_celery.bat
```

**Yöntem 3: Manuel Komut**
```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\venv\Scripts\python.exe -m celery -A app.celery_app worker --loglevel=info --pool=solo
```

### 3️⃣ Frontend Başlatma

```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-web
npm run dev
```

---

## 🔐 Test Kullanıcısı

- **Kullanıcı Adı**: `testuser`
- **Şifre**: `Test1234!`
- **Email**: `test@example.com`

---

## 🌐 Uygulama URL'leri

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8002/api/v1
- **API Docs**: http://localhost:8002/docs
- **Redis**: localhost:6379

---

## 📊 Sistem Durumu Kontrolü

### Redis Kontrolü
```powershell
Test-NetConnection -ComputerName localhost -Port 6379 -InformationLevel Quiet
```

### Backend Kontrolü
```powershell
Test-NetConnection -ComputerName localhost -Port 8002 -InformationLevel Quiet
```

### Login Testi
```powershell
$body = @{username='testuser';password='Test1234!'} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8002/api/v1/auth/login" -Method POST -Body $body -ContentType "application/json"
```

---

## 🗄️ Database İşlemleri

### Kullanıcıları Listele
```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv(); from app.database import SessionLocal; from app.models.user import User; db = SessionLocal(); users = db.query(User).all(); [print(f'{u.username} / {u.email} / Active: {u.is_active}') for u in users]; db.close()"
```

### Yeni Kullanıcı Oluştur
```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv(); from app.database import SessionLocal; from app.models.user import User; from app.auth.utils import get_password_hash; db = SessionLocal(); user = User(username='yenikullanici', email='yeni@example.com', hashed_password=get_password_hash('Sifre123!'), is_active=True); db.add(user); db.commit(); print('Kullanici olusturuldu'); db.close()"
```

---

## 🎬 Transkripsiyon Testi

1. Frontend'e giriş yap: http://localhost:5173
2. `testuser` / `Test1234!` ile login ol
3. **Upload** sayfasına git
4. **Speaker Model** seç:
   - `SILERO` (önerilen - varsayılan)
   - `CUSTOM` (kendi model dosyanı kullan)
   - `NONE` (speaker tanıma kapalı)
5. **Gemini Enhancement** aktif et (opsiyonel)
6. MP3/MP4 dosyası yükle
7. **Transcriptions** sayfasından ilerlemeyi izle

---

## 🔧 Sorun Giderme

### Backend Başlamıyor
```powershell
# Port 8002'yi kullanan process'i bul ve kapat
Get-NetTCPConnection -LocalPort 8002 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }

# Tekrar başlat
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

### Celery Başlamıyor
```powershell
# Redis'i kontrol et
Test-NetConnection -ComputerName localhost -Port 6379

# Redis yoksa Docker ile başlat
docker run -d -p 6379:6379 --name mp4totext-redis redis:alpine redis-server --requirepass dev_redis_123
```

### "Incorrect username or password" Hatası
```powershell
# Kullanıcıyı kontrol et
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv(); from app.database import SessionLocal; from app.models.user import User; db = SessionLocal(); user = db.query(User).filter(User.username == 'testuser').first(); print(f'User exists: {user is not None}'); print(f'Active: {user.is_active if user else False}'); db.close()"
```

---

## 📁 Dosya Yapısı

```
mp4totext-backend/
├── app/
│   ├── main.py              # FastAPI ana dosya (dotenv yüklü ✅)
│   ├── config.py            # Ayarlar (dotenv yüklü ✅)
│   ├── database.py          # Database config (dotenv yüklü ✅)
│   ├── celery_config.py     # Celery config (dotenv yüklü ✅)
│   └── ...
├── .env                     # Environment variables
├── mp4totext.db            # SQLite database (TEK ✅)
├── start_backend.ps1        # Backend başlatma script ✅
├── start_backend.bat        # Backend başlatma batch ✅
├── start_celery.ps1         # Celery başlatma script ✅
└── start_celery.bat         # Celery başlatma batch ✅
```

---

## ✨ Yeni Özellikler

### 1. Custom Speaker Model Desteği
- **SILERO**: Varsayılan pre-trained model
- **CUSTOM**: Kendi `.pth` model dosyanız
- **NONE**: Speaker tanıma devre dışı

### 2. Gemini AI Enhancement
- Transkripsiyon metnini iyileştir
- Otomatik özet oluştur
- Türkçe dil desteği

### 3. WebSocket Real-time Updates
- Canlı ilerleme takibi
- Instant status güncellemeleri

---

## 🎓 Notlar

1. **Redis Gerekli**: Celery için Redis çalışmalı
2. **Working Directory**: Tüm komutlar `mp4totext-backend` dizininden çalıştırılmalı
3. **Virtual Environment**: Backend kendi `venv` klasörünü kullanır
4. **Database**: Otomatik olarak `mp4totext.db` oluşturulur
5. **CORS**: Frontend (5173) ve Backend (8002) arası CORS ayarlanmış

---

## 📞 Destek

Sorun yaşarsanız:
1. Backend ve Celery loglarını kontrol edin
2. Redis'in çalıştığını doğrulayın
3. Database dosyasının var olduğunu kontrol edin
4. `.env` dosyasının doğru olduğunu kontrol edin

---

**Tüm sistem artık düzgün çalışıyor! 🎉**
