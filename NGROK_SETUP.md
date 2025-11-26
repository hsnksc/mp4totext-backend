# ⚠️ ngrok Kurulum ve Kullanım Rehberi

## 🎯 Amaç
RunPod sunucularının localhost:9000'deki MinIO'ya erişebilmesi için public URL oluşturmak.

## 📥 Kurulum Adımları

### 1. ngrok İndir ve Kur
```powershell
# Seçenek A: Doğrudan indirme (Önerilen)
# 1. https://ngrok.com/download adresine git
# 2. "Windows (64-bit)" tıkla
# 3. ZIP'i Downloads klasörüne indir
# 4. ZIP'i sağ tıkla → "Extract All" → C:\ngrok\ klasörüne çıkar

# Seçenek B: winget (zaten yüklü olabilir)
winget install --id=Ngrok.Ngrok -e
```

### 2. ngrok Hesap Aç ve Token Al
```powershell
# 1. https://dashboard.ngrok.com/signup ile ücretsiz hesap aç
# 2. https://dashboard.ngrok.com/get-started/your-authtoken
# 3. Token'ı kopyala (örnek: 2aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5)
```

### 3. ngrok'u Yapılandır
```powershell
# Token'ı ngrok'a ekle (sadece ilk seferinde)
C:\ngrok\ngrok.exe config add-authtoken YOUR_TOKEN_HERE

# Örnek:
C:\ngrok\ngrok.exe config add-authtoken 2aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5
```

### 4. MinIO'nun Çalıştığını Kontrol Et
```powershell
curl http://localhost:9000/minio/health/live

# ✅ Çalışıyorsa: 200 OK
# ❌ Çalışmıyorsa: MinIO'yu başlat
```

## 🚀 Kullanım

### Adım 1: ngrok Tunnel Başlat
```powershell
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\start_ngrok_minio.ps1

# veya doğrudan:
C:\ngrok\ngrok.exe http 9000
```

**Çıktı örneği:**
```
Session Status                online
Account                       your_email@example.com (Plan: Free)
Forwarding                    https://1a2b-3c4d-5e6f.ngrok-free.app -> http://localhost:9000
```

### Adım 2: Public URL'yi Kopyala
```
https://1a2b-3c4d-5e6f.ngrok-free.app
```
⚠️ **ÖNEMLİ:** Bu URL her ngrok başlatışında DEĞİŞİR (free tier)

### Adım 3: .env Dosyasını Güncelle
```bash
# .env dosyasına ekle:
STORAGE_ENDPOINT=1a2b-3c4d-5e6f.ngrok-free.app  # https:// OLMADAN
STORAGE_SECURE=true  # ngrok HTTPS kullanır
```

### Adım 4: Backend ve Celery Yeniden Başlat
```powershell
# Terminal 1: Backend
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
python run.py

# Terminal 2: Celery
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\start_celery.ps1

# Terminal 3: ngrok (açık kalmalı!)
.\start_ngrok_minio.ps1
```

### Adım 5: Test Et
1. Web UI'dan >10MB dosya yükle
2. Celery loglarında kontrol et:
```
✅ Uploaded to MinIO: xxxx.m4a
🚀 RunPod transcription started with URL: https://1a2b-3c4d-5e6f.ngrok-free.app/mp4totext/xxxx.m4a
```

## 🔧 Sorun Giderme

### ngrok Bulunamıyor
```powershell
# PATH'e ekle:
$env:Path += ";C:\ngrok"

# veya tam yol kullan:
C:\ngrok\ngrok.exe http 9000
```

### MinIO Erişilemiyor
```powershell
# MinIO çalışıyor mu?
curl http://localhost:9000/minio/health/live

# Docker ile başlat:
docker start minio

# veya manuel başlat
```

### ngrok Tunnel Kapanıyor
- ⚠️ Free tier: 8 saatlik session limiti
- ⚠️ URL her başlatmada değişir
- 💡 Çözüm: Paid plan ($8/ay) - static URL

### RunPod Hala Erişemiyor
```powershell
# ngrok URL'yi test et (browser'dan):
https://YOUR-NGROK-URL.ngrok-free.app/minio/health/live

# ✅ MinIO login sayfası görünmeli
# ❌ 404: ngrok doğru çalışmıyor
# ❌ timeout: MinIO çalışmıyor
```

## 📊 Maliyet ve Limitler

### Free Tier
- ✅ 1 online tunnel
- ✅ Unlimited requests
- ❌ Random URLs (her başlatmada değişir)
- ❌ 8 saat session limiti
- ⚠️ ngrok banner (bazen sorun yaratabilir)

### Paid ($8/month)
- ✅ 3+ tunnels
- ✅ Static domains (your-name.ngrok.io)
- ✅ No session limit
- ✅ No banner
- ✅ IP whitelisting

## 🎯 Alternatifler (ngrok Yerine)

### 1. Cloudflare Tunnel (Ücretsiz, Kalıcı)
```powershell
# Daha iyi alternatif - static URL
cloudflared tunnel --url http://localhost:9000
```

### 2. Azure Storage / AWS S3 (Production)
```python
# settings.py
STORAGE_ENDPOINT = "mp4totext.blob.core.windows.net"
STORAGE_SECURE = True
```

### 3. Replicate Storage (Production)
- Replicate'in built-in storage'ını kullan
- File size limiti yok
- Otomatik cleanup

## 📝 Özet Workflow

```powershell
# 1. ngrok indir ve token ekle (ilk seferinde)
C:\ngrok\ngrok.exe config add-authtoken YOUR_TOKEN

# 2. Her kullanımda:
# Terminal 1: ngrok başlat
C:\ngrok\ngrok.exe http 9000

# Terminal 2: URL'yi kopyala ve .env'e ekle
STORAGE_ENDPOINT=xxxx.ngrok-free.app
STORAGE_SECURE=true

# Terminal 3: Backend yeniden başlat
python run.py

# Terminal 4: Celery yeniden başlat
.\start_celery.ps1

# 5. Test: >10MB dosya yükle
```

**⚠️ ÖNEMLİ:** ngrok terminali açık kalmalı! Kapanırsa RunPod erişemez.
