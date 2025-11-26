# 🚀 Modal.com Setup Guide - Serverless GPU Transcription

## ✨ Neden Modal?

### RunPod vs Modal Karşılaştırması:
| Özellik | RunPod | Modal |
|---------|--------|-------|
| **URL Desteği** | ❌ Yok (sadece base64) | ✅ Native URL support |
| **File Size Limit** | ~10MB (base64) | ✅ 5GB+ |
| **Startup Time** | Cold start: 20-30s | ⚡ 5-10s |
| **Pricing** | $0.24/saat GPU | 💰 $0.004/dakika (saniye bazlı) |
| **Auto-scaling** | Manuel configuration | ✅ Otomatik 0→∞ GPU |
| **Free Tier** | Yok | ✅ $30/ay ücretsiz credit |
| **API Complexity** | Async polling gerekli | ✅ Sync/Async kolay |

**Sonuç:** Modal daha hızlı, daha ucuz, ve çok daha kolay! 🎉

---

## 📋 Kurulum Adımları

### 1. Modal Hesap Aç (2 dakika)
```bash
# https://modal.com adresine git
# "Sign up" tıkla (GitHub ile giriş yapabilirsin)
# Otomatik $30 ücretsiz credit alacaksın
```

### 2. Modal CLI Kur
```powershell
# Backend klasöründe:
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
pip install modal
```

### 3. Modal Token Al
```powershell
# Terminal'de çalıştır:
modal token new

# Browser açılacak, GitHub ile giriş yap
# Token otomatik kaydedilecek
```

### 4. Modal Whisper Function Deploy Et
```powershell
# Backend klasöründe:
modal deploy modal_whisper_function.py

# Çıktı örneği:
# ✓ Created deployment mp4totext-whisper
# ✓ Function transcribe deployed
# View at: https://modal.com/apps/mp4totext-whisper
```

### 5. .env Dosyasını Güncelle
```bash
# .env dosyasında:
USE_MODAL='true'  # Modal'ı aktif et
MODAL_API_TOKEN=''  # Boş bırak (CLI token kullanılır)
```

### 6. Backend ve Celery Yeniden Başlat
```powershell
# Terminal 1: Backend
python run.py

# Terminal 2: Celery
.\start_celery.ps1

# Terminal 3: ngrok (MinIO için açık kalmalı)
ngrok http 9000
```

---

## 🧪 Test Et

### Option 1: Web UI (Önerilen)
1. http://localhost:5173 aç
2. >10MB dosya yükle
3. Celery loglarında kontrol et:
```
☁️ Using Modal for transcription
📦 File size: 29.4MB, uploading to MinIO...
✅ File uploaded, using URL for Modal
🚀 Modal transcription started with URL: https://...
✅ Modal transcription completed in 45.2s
```

### Option 2: CLI Test
```powershell
# Backend klasöründe:
modal run modal_whisper_function.py

# Test dosyası ile otomatik test yapar
# Roosevelt's Pearl Harbor speech transcribe edilecek
```

### Option 3: Manuel API Test
```python
import requests

url = "https://modal.com/api/v1/apps/mp4totext-whisper/functions/transcribe/invoke"
headers = {"Authorization": f"Bearer {your_modal_token}"}
payload = {
    "audio_url": "https://your-ngrok-url.ngrok-free.app/mp4totext/file.m4a",
    "model": "large-v3",
    "language": None
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

---

## 💰 Maliyet Hesaplama

### Pricing (Nvidia T4 GPU):
- **$0.004/dakika** = **$0.24/saat** (RunPod ile aynı saatlik ücret!)
- **Fark:** Modal saniye bazlı, RunPod saat bazlı faturalandırma

### Örnek Hesaplamalar:
| Dosya | Süre | RunPod Maliyet | Modal Maliyet | Tasarruf |
|-------|------|----------------|---------------|----------|
| 30 min audio | 45 sn | $0.24 (1 saat) | $0.003 | **%98.75** 🎉 |
| 2 saat audio | 3 min | $0.24 (1 saat) | $0.012 | **%95** |
| 10 dosya/gün | 10 min | $2.40 (10 saat) | $0.04 | **%98.3** |

**Sonuç:** Modal ÇOOOOK daha ucuz çünkü sadece kullandığın saniyeler için ödüyorsun!

### Free Tier:
- **$30 ücretsiz credit/ay**
- **≈ 125 saatlik GPU kullanımı**
- **≈ 15,000 dosya** (her biri 30 saniye transcription)

---

## 🔧 Sorun Giderme

### Modal Token Bulunamıyor
```powershell
# Token'ı kontrol et:
modal token show

# Token yoksa tekrar oluştur:
modal token new
```

### Function Deploy Hata Veriyor
```powershell
# Bağımlılıkları kontrol et:
pip install openai-whisper torch

# Deploy loglarını incele:
modal deploy modal_whisper_function.py --debug
```

### ngrok URL Erişilemiyor
```powershell
# ngrok çalışıyor mu?
curl https://your-ngrok-url.ngrok-free.app/minio/health/live

# MinIO çalışıyor mu?
curl http://localhost:9000/minio/health/live

# ngrok yeniden başlat:
ngrok http 9000
# .env'de yeni URL'yi güncelle
```

### Transcription Timeout
```bash
# .env'de timeout'u artır:
MODAL_TIMEOUT='1200'  # 20 minutes

# Veya daha küçük model kullan:
# Backend'de: large-v3 → large-v2 → medium
```

---

## 📊 Modal Dashboard

### Monitoring:
1. https://modal.com/apps adresine git
2. `mp4totext-whisper` app'ini aç
3. **Logs:** Gerçek zamanlı function logları
4. **Metrics:** GPU usage, execution time, errors
5. **Billing:** Credit kullanımı ve maliyet analizi

### Logs Örneği:
```
2025-11-09 21:15:42 🎵 Downloading audio from: https://...
2025-11-09 21:15:47 🤖 Loading Whisper model: large-v3
2025-11-09 21:15:52 🎬 Transcribing audio...
2025-11-09 21:16:28 ✅ Transcription complete: 4,823 chars
```

---

## 🎯 Alternatif Modeller

Modal deployment'da model değiştirebilirsin:

```python
# modal_whisper_function.py içinde:

@app.function(
    gpu="T4",  # Değiştir: T4, A10G, A100
    ...
)
```

### GPU Seçenekleri:
| GPU | VRAM | Hız | Maliyet/saat |
|-----|------|-----|--------------|
| T4 (free tier) | 16GB | 1x | $0.24 |
| A10G | 24GB | 3x | $1.10 |
| A100 (40GB) | 40GB | 8x | $4.00 |

**Öneri:** T4 yeterli! Large-v3 model rahat çalışır.

---

## 📝 Özet Workflow

```powershell
# İLK SETUP (tek seferlik):
1. modal token new                           # Token al
2. modal deploy modal_whisper_function.py    # Deploy et
3. .env'de USE_MODAL='true' yap
4. Backend + Celery restart

# HER KULANIMDA:
1. ngrok http 9000                           # MinIO public yap
2. .env'de STORAGE_ENDPOINT güncelle         # ngrok URL
3. Backend + Celery restart
4. Dosya yükle ve test et! 🚀

# MONITORING:
https://modal.com/apps → Logs, Metrics, Billing
```

---

## 🎉 Başarı Kriterleri

Test başarılı ise göreceksin:

```bash
# Celery logs:
☁️ Using Modal for transcription
📦 File size: 29.4MB, uploading to MinIO...
✅ Uploaded to MinIO: xxxx.m4a
🚀 Modal transcription started with URL: https://...
✅ Modal transcription completed in 45.2s
📝 Transcription length: 4823 chars
🔢 Segments: 147
🌍 Language: tr

# Web UI:
Status: COMPLETED ✅
Duration: 45 seconds
Transcript: [full text]
```

**Tebrikler!** 🎊 Modal entegrasyonu tamamlandı! Artık büyük dosyalar için en hızlı ve en ucuz çözümü kullanıyorsun.

---

## 💡 Pro Tips

1. **Model Seçimi:** 
   - Test: `base` (fast, cheap)
   - Production: `large-v3` (best quality)

2. **Cost Optimization:**
   - Batch uploads: Birden fazla dosyayı sırayla gönder
   - Modal auto-scales:걱정 할 필요 없음, otomatik optimize ediyor

3. **Debugging:**
   - Modal logs gerçek zamanlı: `modal app logs mp4totext-whisper`
   - Local test: `modal run modal_whisper_function.py`

4. **ngrok Free Tier:**
   - URL her restart'ta değişir
   - Paid ($8/ay): Static URL, sınırsız
   - Alternatif: Cloudflare Tunnel (ücretsiz, static)

**Hazırsın! 🚀**
