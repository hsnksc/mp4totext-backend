# MP4toText - Image Generation Setup Guide

## 🎨 Transcript-to-Image Feature

Bu özellik, Modal.com'un T4 GPU'larını kullanarak transkriptlerden profesyonel görseller oluşturur.

---

## 📋 Kurulum Adımları

### 1️⃣ Modal.com Hesabı Oluştur

```bash
# Modal.com'a git
https://modal.com

# Hesap oluştur (GitHub ile giriş yapabilirsin)
```

### 2️⃣ Modal CLI Kurulumu

```bash
# Backend klasöründe
cd mp4totext-backend

# Modal kütüphanesini yükle
pip install modal

# Modal hesabınıza giriş yapın
modal token new
```

**Bu komut şunları yapacak:**
- Tarayıcıda Modal login sayfası açılacak
- Giriş yaptıktan sonra terminal'de token bilgileri gösterilecek
- Token'lar otomatik kaydedilecek

### 3️⃣ Environment Variables

`.env` dosyanıza ekleyin:

```bash
# Modal.com Credentials (modal token new çıktısından)
MODAL_TOKEN_ID=your_token_id_here
MODAL_TOKEN_SECRET=your_token_secret_here
```

### 4️⃣ Database Migration

```bash
# Backend klasöründe
cd mp4totext-backend

# Virtual environment aktif et
.\.venv\Scripts\Activate.ps1

# Migration çalıştır
python add_generated_images.py
```

**Çıktı:**
```
================================================================================
ADDING GENERATED IMAGES TABLE
================================================================================
📝 Creating generated_images table...
✅ generated_images table created successfully

📋 Table Structure:
------------------------------------------------------------
  id                   integer
  transcription_id     integer
  user_id              integer
  prompt               text
  style                character varying
  seed                 integer
  image_url            character varying
  filename             character varying
  file_size            integer
  is_active            boolean
  created_at           timestamp with time zone
------------------------------------------------------------

✅ Migration completed successfully!
```

### 5️⃣ Backend Yeniden Başlat

```bash
# Terminal 1: Backend
cd mp4totext-backend
python run.py

# Terminal 2: Celery Worker (background image generation için)
cd mp4totext-backend
.\start_celery.ps1
```

### 6️⃣ Frontend Yeniden Başlat

```bash
cd mp4totext-web
npm run dev
```

---

## 🎨 Kullanım

### Web UI'dan:

1. **Transkripsiyon tamamlandıktan sonra**
2. **"🎨 Görsel Oluştur" butonuna tıkla**
3. **Stil seç:**
   - 💼 **Professional**: İş/toplantı görselleri
   - 🎨 **Artistic**: Sanatsal illüstrasyon
   - 📊 **Technical**: Teknik diyagram
   - 🎯 **Minimalist**: Basit ve şık
   - 🎬 **Cinematic**: Sinematik ışıklandırma

4. **Görsel sayısı seç:** 1-4 arası
5. **İsteğe bağlı özel prompt ekle**
6. **"Oluştur" butonuna tıkla**

**Süre:** 1-2 dakika (1 görsel için)

### API'dan:

```bash
# Image Generation
curl -X POST http://localhost:8002/api/v1/images/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "transcription_id": 123,
    "num_images": 1,
    "style": "professional"
  }'

# List Generated Images
curl http://localhost:8002/api/v1/images/transcription/123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 💰 Maliyet Analizi

### Modal T4 GPU Fiyatlandırması:

- **Saat başı:** $0.59
- **Görsel başı (tahmini):** ~$0.01
- **Süre:** ~60 saniye/görsel

**Örnek Hesaplama:**
```
100 transkript × 1 görsel × $0.01 = $1.00/ay
```

**Çok ucuz! ✅**

### Neden T4 GPU?

| GPU | Saat Başı | Görsel Başı | Süre | Önerilen |
|-----|-----------|-------------|------|----------|
| **T4** | $0.59 | $0.01 | 60s | ✅ **EN İYİ** |
| A10G | $1.10 | $0.02 | 40s | Hızlı ama pahalı |
| H100 | $3.95 | $0.07 | 10s | Gereksiz pahalı |

---

## 🔧 Sorun Giderme

### 1. "Modal credentials not configured"

**Çözüm:**
```bash
# Token'ları tekrar oluştur
modal token new

# .env'ye ekle
MODAL_TOKEN_ID=...
MODAL_TOKEN_SECRET=...

# Backend yeniden başlat
```

### 2. "Modal library not installed"

**Çözüm:**
```bash
cd mp4totext-backend
pip install modal
```

### 3. "Table 'generated_images' does not exist"

**Çözüm:**
```bash
cd mp4totext-backend
python add_generated_images.py
```

### 4. Görseller oluşturulmuyor

**Kontrol:**
1. Modal credentials doğru mu? → `python -c "import os; print(os.getenv('MODAL_TOKEN_ID'))"`
2. Backend çalışıyor mu? → `http://localhost:8002/docs`
3. Celery worker çalışıyor mu? → `.\check_celery.ps1`

---

## 📊 Özellikler

### ✅ Tamamlanan:

- [x] Modal T4 GPU entegrasyonu
- [x] 5 farklı görsel stili
- [x] AI-powered prompt generation
- [x] Custom prompt desteği
- [x] MinIO storage entegrasyonu
- [x] Database kayıt sistemi
- [x] Web UI ile görsel galeri
- [x] Background task support (Celery)
- [x] Image download/view

### 🚀 Gelecek Geliştirmeler:

- [ ] Batch image generation
- [ ] Image editing (inpainting, variations)
- [ ] Style transfer
- [ ] Text-to-image fine-tuning
- [ ] Credits system integration

---

## 🎯 Test

```bash
# Backend test
cd mp4totext-backend
pytest tests/test_image_generation.py

# API health check
curl http://localhost:8002/api/v1/images/styles
```

---

## 📚 Kaynaklar

- **Modal Docs:** https://modal.com/docs
- **Stable Diffusion:** https://stability.ai/stable-diffusion
- **API Endpoints:** http://localhost:8002/docs#/images

---

## 💡 İpuçları

1. **En iyi sonuçlar için:**
   - Transkript ne kadar detaylı olursa görseller o kadar iyi olur
   - Custom prompt kullanarak tam istediğiniz görseli oluşturabilirsiniz
   - Professional style iş kullanımları için idealdir

2. **Maliyet optimizasyonu:**
   - Tek görsel ile başlayın
   - Beğenirseniz daha fazla varyasyon oluşturun
   - Background generation kullanarak senkron beklemeyin

3. **Prompt örnekleri:**
   - "Modern conference room with business presentation, blue corporate colors"
   - "Abstract visualization of data analytics, minimalist infographic style"
   - "Professional team meeting in office, natural lighting, realistic"

---

## ✅ Kurulum Tamamlandı!

Artık transkriptlerinizden profesyonel görseller oluşturabilirsiniz! 🎨

**Destek için:** hasan@mp4totext.com
