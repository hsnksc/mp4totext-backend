# Transkripsiyon Fiyatlandırma Güncellemesi

## 📊 Değişiklik Özeti

**Tarih**: 2024
**Değişiklik**: Transkripsiyon maliyetleri 10x daha ucuz hale getirildi

### Eski Fiyatlar
- **Transkripsiyon**: 10 kredi/dakika
- **Speaker Recognition**: 5 kredi/dakika (ek maliyet)

### Yeni Fiyatlar
- **Transkripsiyon**: 1 kredi/dakika (90% daha ucuz!)
- **Speaker Recognition**: 0.5 kredi/dakika (90% daha ucuz!)

---

## 🔧 Yapılan Değişiklikler

### 1. Database Güncellemesi
**Dosya**: `update_transcription_pricing.py`

```sql
-- credit_pricing_configs tablosu
UPDATE credit_pricing_configs 
SET cost_per_unit = 1 
WHERE operation_key = 'transcription_base';

UPDATE credit_pricing_configs 
SET cost_per_unit = 1,
    unit_description = 'per 2 dakika',
    description = 'Farklı konuşmacıları ayırt etme (0.5 kredi/dakika)'
WHERE operation_key = 'speaker_recognition';
```

**Not**: SQLite INTEGER kullandığı için 0.5 değerini direkt tutamıyoruz. Çözüm olarak:
- Database'de `cost_per_unit = 1` ve `unit_description = "per 2 dakika"` olarak saklanıyor
- Backend kod hesaplarken `1 / 2 = 0.5 kredi/dakika` olarak kullanıyor

### 2. Backend Güncellemeleri

#### `app/services/credit_service.py`

**Default pricing güncellendi** (Lines 30-42):
```python
_DEFAULT_PRICING = {
    "transcription_base": 1,        # Was 10
    "speaker_recognition": 1,       # Was 5 (represents 0.5 kredi/dk)
    "youtube_download": 10,
    "ai_enhancement": 20,
    # ... diğer fiyatlar değişmedi
}
```

**`calculate_transcription_cost()` metodu güncellendi** (Lines 106-147):
```python
def calculate_transcription_cost(
    self, 
    duration_seconds: float, 
    use_speaker_recognition: bool = False,
    is_youtube: bool = False
) -> int:
    """
    Pricing:
    - Transcription: 1 kredi/dakika
    - Speaker recognition: 0.5 kredi/dakika
    
    Example: 5 dakikalık dosya + speaker:
    (5 × 1) + (5 × 0.5) = 7.5 → rounds to 8 kredi
    """
    minutes = max(1, int(duration_seconds / 60) + (1 if duration_seconds % 60 > 0 else 0))
    
    # Base cost
    cost = self.TRANSCRIPTION_BASE * minutes
    
    # Speaker recognition: 0.5 kredi/dakika
    if use_speaker_recognition:
        speaker_cost = (self.SPEAKER_RECOGNITION * minutes) / 2
        cost += speaker_cost
    
    if is_youtube:
        cost += self.YOUTUBE_DOWNLOAD
    
    # Round up (can't charge fractional credits)
    return int(cost + 0.5)
```

**Önemli**: Speaker recognition maliyeti `/2` ile hesaplanarak 0.5 kredi/dakika efektif maliyeti sağlanıyor.

### 3. Frontend Güncellemeleri

#### `mp4totext-web/src/pages/UploadPage.tsx`

**State'e pricing eklendi** (Lines 37-42):
```typescript
const [basePrices, setBasePrices] = useState({ 
  transcription_per_minute: 1,
  speaker_recognition_per_minute: 1, // DB'de "per 2 dakika" = 0.5 kredi/dk
  ai_enhancement: 20,
  tavily_web_search: 5
});
```

**API'den pricing fetch ediliyor** (Lines 46-61):
```typescript
useEffect(() => {
  const fetchData = async () => {
    const [modelsRes, pricingRes] = await Promise.all([
      api.get('/credits/models/active'),
      api.get('/credits/pricing')
    ]);
    setAiModels(modelsRes.data);
    setBasePrices({
      transcription_per_minute: pricingRes.data.transcription_per_minute || 1,
      speaker_recognition_per_minute: pricingRes.data.speaker_recognition_per_minute || 1,
      ai_enhancement: pricingRes.data.ai_enhancement || 20,
      tavily_web_search: pricingRes.data.tavily_web_search || 5
    });
  };
  fetchData();
}, []);
```

**Maliyet gösterimi dinamik hale getirildi** (Lines 559-574):
```tsx
{/* Transcription cost */}
<span>~{basePrices.transcription_per_minute} kredi/dk</span>

{/* Speaker recognition cost (0.5 kredi/dk) */}
<span>~{basePrices.speaker_recognition_per_minute / 2} kredi/dk</span>

{/* Tavily web search */}
<span>~{basePrices.tavily_web_search} kredi</span>
```

---

## 💰 Maliyet Karşılaştırma Örnekleri

### Örnek 1: Basit Transkripsiyon
**1 dakikalık dosya**
- **ESKİ**: 10 kredi
- **YENİ**: 1 kredi
- **Tasarruf**: 9 kredi (90% daha ucuz)

### Örnek 2: Speaker Recognition ile
**5 dakikalık dosya + speaker recognition**
- **ESKİ**: (5×10) + (5×5) = 75 kredi
- **YENİ**: (5×1) + (5×0.5) = 7.5 → 8 kredi
- **Tasarruf**: 67 kredi (91% daha ucuz)

### Örnek 3: Full Feature
**10 dakikalık dosya + speaker + AI enhancement (gemini-2.5-flash 1.0x)**
- **ESKİ**: (10×10) + (10×5) + 20 = 170 kredi
- **YENİ**: (10×1) + (10×0.5) + 20 = 35 kredi
- **Tasarruf**: 135 kredi (79% daha ucuz)

### Örnek 4: Premium Full Stack
**20 dakika + speaker + lecture notes (gpt-4o-mini 1.5x) + web search**
- **ESKİ**: (20×10) + (20×5) + (30×1.5) + 5 = 350 kredi
- **YENİ**: (20×1) + (20×0.5) + (30×1.5) + 5 = 80 kredi
- **Tasarruf**: 270 kredi (77% daha ucuz)

---

## 🧪 Test Senaryoları

### Backend Test

#### 1. Database Güncellemesini Çalıştır
```powershell
cd mp4totext-backend
python update_transcription_pricing.py
```

**Beklenen Çıktı**:
```
✅ UPDATED: Transcription Base
   OLD: 10 kredi/dakika
   NEW: 1 kredi/dakika

✅ UPDATED: Speaker Recognition
   OLD: 5 kredi/dakika
   NEW: 1 kredi per 2 dakika (efektif: 0.5 kredi/dakika)
```

#### 2. Backend'i Yeniden Başlat
```powershell
# Kill existing processes
.\debug_backend_clean.ps1

# Start backend
.\venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

#### 3. Celery Worker'ı Yeniden Başlat
```powershell
# Stop existing worker (Ctrl+C)
# Start new worker
.\start_celery.bat
```

#### 4. Pricing API Test
```powershell
# Test pricing endpoint
curl http://localhost:8002/api/v1/credits/pricing
```

**Beklenen Response**:
```json
{
  "transcription_per_minute": 1,
  "speaker_recognition_per_minute": 1,
  "youtube_download": 10,
  "ai_enhancement": 20,
  "lecture_notes": 30,
  "custom_prompt": 25,
  "exam_questions": 20,
  "translation": 15,
  "tavily_web_search": 5
}
```

#### 5. Maliyet Hesaplama Test
Python shell ile:
```python
from app.database import SessionLocal
from app.services.credit_service import get_credit_service

db = SessionLocal()
credit_service = get_credit_service(db)

# Test 1: 5 dakikalık dosya (sadece transkripsiyon)
cost1 = credit_service.pricing.calculate_transcription_cost(
    duration_seconds=300,  # 5 dakika
    use_speaker_recognition=False
)
print(f"5 dakika (sadece transkripsiyon): {cost1} kredi")  # Beklenen: 5

# Test 2: 5 dakikalık dosya (speaker ile)
cost2 = credit_service.pricing.calculate_transcription_cost(
    duration_seconds=300,
    use_speaker_recognition=True
)
print(f"5 dakika (speaker ile): {cost2} kredi")  # Beklenen: 8 (7.5 → round up)

# Test 3: 10 dakikalık dosya (speaker ile)
cost3 = credit_service.pricing.calculate_transcription_cost(
    duration_seconds=600,
    use_speaker_recognition=True
)
print(f"10 dakika (speaker ile): {cost3} kredi")  # Beklenen: 15

db.close()
```

### Frontend Test

#### 1. Frontend'i Çalıştır
```powershell
cd mp4totext-web
npm run dev
```

#### 2. UI Test Adımları

**2.1. Upload Page'i Aç**
- http://localhost:5173/upload

**2.2. Fiyatları Kontrol Et**
- "Tahmini Kredi Maliyeti" bölümünü bul
- **Transkripsiyon**: "~1 kredi/dk" görmeli
- **Speaker Recognition** toggle'ı aç → "~0.5 kredi/dk" görmeli
- **AI Enhancement** toggle'ı aç → "~20 kredi" (veya seçili modele göre) görmeli
- **Web Search** toggle'ı aç → "~5 kredi" görmeli

**2.3. Test Dosyası Yükle**
- Kısa bir ses dosyası seç (örn: 1 dakikalık test dosyası)
- Speaker Recognition: **Açık**
- AI Enhancement: **Kapalı**
- "Yükle ve Transkript Et" butonuna tıkla

**2.4. Kredi Düşüşünü Kontrol Et**
- Dashboard'a git: http://localhost:5173/dashboard
- Credit balance'ı not al
- Transaction history'de maliyeti kontrol et:
  - **1 dakikalık dosya + speaker**: ~2 kredi düşmeli (1 + 0.5 = 1.5 → 2)
  - **5 dakikalık dosya + speaker**: ~8 kredi düşmeli (5 + 2.5 = 7.5 → 8)

**2.5. Tam Özellikli Test**
- Yeni dosya yükle (5 dakikalık)
- Speaker Recognition: **Açık**
- AI Enhancement: **Açık** (gemini-2.5-flash seç)
- Web Search: **Açık**
- Beklenen maliyet: 5 + 2.5 + 20 + 5 = 32.5 → **33 kredi**

---

## 🔍 Sorun Giderme

### Problem 1: Frontend'de Eski Fiyatlar Görünüyor (10 kredi/dk)

**Çözüm**:
```powershell
# Vite cache'i temizle
cd mp4totext-web
npm run dev -- --force

# Veya browser cache'i temizle (Ctrl+Shift+R)
```

### Problem 2: Backend Pricing API Eski Değerleri Dönüyor

**Kontrol**:
```powershell
cd mp4totext-backend
python -c "
from app.database import SessionLocal
from app.models.credit_pricing import CreditPricingConfig

db = SessionLocal()
configs = db.query(CreditPricingConfig).filter_by(is_active=True).all()
for c in configs:
    print(f'{c.operation_key}: {c.cost_per_unit} {c.unit_description}')
db.close()
"
```

**Beklenen**:
```
transcription_base: 1 dakika başı
speaker_recognition: 1 per 2 dakika
```

**Eğer yanlışsa**, `update_transcription_pricing.py`'yi tekrar çalıştır.

### Problem 3: Celery Worker Eski Fiyatları Kullanıyor

**Çözüm**: Worker restart gerekli
```powershell
# Windows'ta tüm Python process'leri kill et
taskkill /F /IM python.exe

# Celery'yi tekrar başlat
cd mp4totext-backend
.\venv\Scripts\activate
.\start_celery.bat
```

### Problem 4: Speaker Recognition Maliyeti 1 kredi/dk Gösteriyor (0.5 değil)

**Kontrol**: Frontend code'da `/2` eklendi mi?
```tsx
<span>~{basePrices.speaker_recognition_per_minute / 2} kredi/dk</span>
```

Backend'de de kontrol:
```python
# credit_service.py calculate_transcription_cost metodunda
speaker_cost = (self.SPEAKER_RECOGNITION * minutes) / 2
```

---

## 📝 Notlar

### SQLite ve Decimal Değerler
SQLite INTEGER kullandığı için 0.5 değerini direkt saklayamıyoruz. Workaround:
- Database'de: `cost_per_unit=1`, `unit_description="per 2 dakika"`
- Backend'de: Hesaplarken `/2` ile 0.5 efektif maliyet
- Frontend'de: Gösterirken `/2` ile 0.5 gösterim

### Yuvarlama Stratejisi
- Python backend: `int(cost + 0.5)` - Standard rounding (7.5 → 8, 7.4 → 7)
- Kullanıcıya her zaman yukarı yuvarlama yapıyoruz (fractional credit yok)

### Credit Deduction Timing
- Kredi düşümü **transkripsiyon başlamadan önce** yapılıyor
- Eğer işlem fail olursa, kredi **geri iade ediliyor**
- Worker'daki credit deduction kodu: `transcription_worker.py` lines 556-576

---

## ✅ Checklist

Backend:
- [x] Database pricing güncellendi (`update_transcription_pricing.py`)
- [x] `credit_service.py` default pricing güncellendi
- [x] `calculate_transcription_cost()` metodu 0.5 kredi/dk hesaplaması eklenді
- [x] Backend restart edildi

Frontend:
- [x] `basePrices` state'i genişletildi (transcription_per_minute, speaker_recognition_per_minute eklendi)
- [x] Pricing API fetch güncellendi
- [x] UI'da hardcoded değerler dinamik hale getirildi
- [x] Speaker recognition maliyeti `/2` ile gösterildi

Test:
- [ ] Pricing API response'u test edildi (1, 1, 20, 5, ...)
- [ ] 5 dakikalık dosya + speaker = ~8 kredi düşüşü test edildi
- [ ] Frontend UI'da doğru fiyatlar gösteriliyor
- [ ] Credit transaction history doğru kayıt tutuyor

---

## 🚀 Deployment

Production'a çıkmadan önce:

1. **Database Migration**: Production DB'ye `update_transcription_pricing.py` çalıştır
2. **Backend Deployment**: Yeni kod deploy et, restart et
3. **Frontend Deployment**: Build ve deploy
4. **Kullanıcı Bildirimi**: "Fiyatlar 10x daha ucuz!" duyurusu yap
5. **Monitor**: İlk gün credit transaction'ları izle

---

## 📞 İletişim

Sorular için: Backend team / Credit system owner
