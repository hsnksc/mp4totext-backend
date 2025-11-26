# 🎙️ Speaker Diarization Kurulum Rehberi

MP4toText projesine **pyannote.audio 3.1** ile speaker diarization (konuşmacı tanıma) özelliği eklenmiştir.

## 🚀 Özellikler

- ✅ **Whisper transcription** - Tüm diller desteklenir (tr, en, de, fr, es, vs.)
- ✅ **pyannote.audio 3.1** - Son teknoloji konuşmacı tanıma (state-of-the-art)
- ✅ **Otomatik speaker alignment** - Transkripsiyon segmentleri ile konuşmacıları otomatik eşleştirir
- ✅ **Multi-language support** - Tüm Whisper destekli diller için çalışır
- ✅ **Modal.com GPU** - T4 GPU ile hızlı işlem (15-16GB RAM)
- ✅ **Model caching** - Container 5 dakika açık kalır, sonraki istekler daha hızlı

## 📋 Gereksinimler

### 1. HuggingFace Hesabı ve Token

pyannote.audio modeli HuggingFace'den yüklenir ve **access token** gerektirir.

#### Adımlar:

1. **HuggingFace hesabı açın**
   - https://huggingface.co/join adresine gidin
   - Ücretsiz hesap oluşturun

2. **Access token oluşturun**
   - Settings → Access Tokens → New Token
   - Token tipini seçin: **Read** (okuma yetkisi yeterli)
   - Token'ı kopyalayın: `hf_xxxxxxxxxxxxxxxxxxxxxxxx`

3. **pyannote model'e erişim izni alın**
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - **"Accept terms"** butonuna tıklayın (model kullanım şartlarını kabul edin)
   - Bu adım **zorunludur**, aksi halde model yüklenemez

### 2. Modal CLI Kurulumu

```bash
# Modal CLI'yi yükleyin
pip install modal

# Modal hesabınızı bağlayın
modal token new
```

### 3. HuggingFace Token'ı Modal'a Ekleyin

```bash
# Secret oluşturun
modal secret create huggingface-secret HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx
```

**NOT**: `hf_xxxxxxxxxxxxxxxxxxxxxxxx` kısmını kendi token'ınız ile değiştirin.

### 4. Modal App'i Deploy Edin

```bash
# Backend klasörüne gidin
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend

# Modal app'i deploy edin
modal deploy modal_whisper_function.py
```

**Başarılı deploy çıktısı:**
```
✓ Initialized. View run at https://modal.com/apps/...
✓ Created objects.
├── 🔨 Created mount /...
├── 🔨 Created volume whisper-diarization-models
└── 🔨 Created WhisperDiarizationModel => https://modal.com/...
✓ App deployed! 🎉
```

## 🧪 Test

```bash
# Modal app'i test edin
modal run modal_whisper_function.py
```

## 📊 Kullanım

### API Endpoint

```python
POST /api/v1/transcriptions
{
  "file": <audio_file>,
  "enable_diarization": true,
  "min_speakers": 2,  # Opsiyonel
  "max_speakers": 5,  # Opsiyonel
  "language": "tr"    # Opsiyonel (null = otomatik)
}
```

### Response Format

```json
{
  "id": 123,
  "text": "Merhaba ben Ahmet. Merhaba Ahmet, ben Ayşe.",
  "transcript_with_speakers": "SPEAKER_00: Merhaba ben Ahmet.\n\nSPEAKER_01: Merhaba Ahmet, ben Ayşe.",
  "speaker_count": 2,
  "speakers_json": [
    {"speaker": "SPEAKER_00", "start": 0.0, "end": 2.5},
    {"speaker": "SPEAKER_01", "start": 2.5, "end": 5.8}
  ],
  "language": "tr"
}
```

## 🔧 Database Migration

Speaker diarization alanları zaten eklenmiş durumda:

```python
# Transcription model
enable_diarization: bool = False
min_speakers: int = None
max_speakers: int = None
speakers_json: JSON = None
transcript_with_speakers: Text = None
```

Migration gerekmez, yeni kolonlar otomatik eklenir.

## ⚙️ Ayarlar

### Modal Container Specs

```python
gpu="T4"              # Nvidia T4 GPU (ücretsiz tier)
memory=16384          # 16GB RAM (pyannote için gerekli)
timeout=900           # 15 dakika max işlem süresi
container_idle_timeout=300  # 5 dakika warm container
```

### Performans

- **İlk istek**: Model yükleme + transcription (~2-3 dakika)
- **Sonraki istekler (5 dk içinde)**: Sadece transcription (~1 dakika)
- **Diarization overhead**: +30-60 saniye (audio uzunluğuna göre)

## 🐛 Troubleshooting

### HuggingFace Token Hatası

```
⚠️ Failed to load diarization pipeline: Invalid token
```

**Çözüm**:
1. Token'ın doğru kopyalandığından emin olun
2. pyannote model sayfasında "Accept terms" yaptığınızdan emin olun
3. Token'ı tekrar oluşturun ve Modal'a ekleyin

### Model Yüklenemiyor

```
⚠️ No HUGGINGFACE_TOKEN found, speaker diarization disabled
```

**Çözüm**:
```bash
# Secret'ın doğru eklendiğini kontrol edin
modal secret list

# Yeniden ekleyin
modal secret create huggingface-secret HUGGINGFACE_TOKEN=hf_xxxxx --force
```

### GPU Yetersiz

```
OutOfMemoryError: CUDA out of memory
```

**Çözüm**: Modal'da memory ayarı 16GB yapılmış durumda. Eğer sorun devam ederse:
- Daha kısa audio dosyaları kullanın
- `max_speakers` parametresini küçültün

## 📝 Notlar

- **Diarization opsiyoneldir**: `enable_diarization=False` (default) ise sadece transkripsiyon yapılır
- **Tüm diller desteklenir**: Whisper'ın desteklediği tüm dillerde çalışır
- **Speaker labels**: SPEAKER_00, SPEAKER_01, SPEAKER_02, ... formatında gelir
- **Min/max speakers**: Opsiyonel kısıtlamalar, None ise otomatik tespit edilir

## 🎯 Best Practices

1. **Küçük dosyalarla test edin** (1-2 dakikalık audio)
2. **Min/max speakers belirtin** (eğer biliyorsanız, daha hızlı sonuç verir)
3. **Language parameter kullanın** (auto-detect yerine dil belirtin, daha hızlı)
4. **Container warm tutun** (ardışık istekler 5 dk içinde yapın)

## 📚 Referanslar

- [pyannote.audio 3.1 Documentation](https://github.com/pyannote/pyannote-audio)
- [Modal.com Documentation](https://modal.com/docs)
- [Whisper Model Documentation](https://github.com/openai/whisper)
- [HuggingFace Access Tokens](https://huggingface.co/docs/hub/security-tokens)

## ✅ Checklist

- [ ] HuggingFace hesabı açıldı
- [ ] Access token oluşturuldu
- [ ] pyannote model'e erişim izni alındı (Accept terms)
- [ ] Modal CLI kuruldu (`pip install modal`)
- [ ] Modal token oluşturuldu (`modal token new`)
- [ ] HuggingFace secret Modal'a eklendi
- [ ] Modal app deploy edildi (`modal deploy modal_whisper_function.py`)
- [ ] Test başarılı (`modal run modal_whisper_function.py`)

## 🎉 Tamamlandı!

Speaker diarization artık kullanıma hazır. API endpoint'inizi `enable_diarization=true` parametresi ile çağırın.
