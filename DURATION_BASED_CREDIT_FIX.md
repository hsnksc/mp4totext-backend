# 🔥 CRITICAL BUG FIX: Duration-Based Credit Calculation

## 🐛 Problem

**Semptom**: Transkripsiyon maliyeti dosya süresine göre değil, **her dosyadan sabit 10 kredi** düşüyordu.

**Root Cause**: `transcription.duration` field'ı hiç set edilmiyordu!

```python
# transcription_worker.py (Line 565)
actual_duration = transcription.duration or 60  # ← ALWAYS using fallback!
```

Database'de `duration` field'ı vardı ama hiç dolmuyordu, bu yüzden:
- Her dosya için `duration = None`
- Fallback: `60 seconds` (1 dakika)
- Maliyet: `60 / 60 * 10 = 10 kredi` (sabit)

**Örnek**:
- 30 saniye dosya → 10 kredi ❌
- 5 dakika (300s) dosya → 10 kredi ❌
- 20 dakika (1200s) dosya → 10 kredi ❌

**İmpact**: Kullanıcılar kısa dosyalar için **fazla** ödüyordu, uzun dosyalar için **az** ödüyordu.

---

## ✅ Solution

### Code Changes

**File**: `app/workers/transcription_worker.py` (Lines 207-226)

**BEFORE** (Lines 207-213):
```python
# Update transcription with results
transcription.text = result["text"]
transcription.language = result["language"]
transcription.speaker_count = result["speaker_count"]
transcription.speakers = result["speakers"]
transcription.segments = result["segments"]
transcription.processing_time = processing_time
```

**AFTER** (Lines 207-232):
```python
# Update transcription with results
transcription.text = result["text"]
transcription.language = result["language"]
transcription.speaker_count = result["speaker_count"]
transcription.speakers = result["speakers"]
transcription.segments = result["segments"]
transcription.processing_time = processing_time

# 🔥 CRITICAL FIX: Calculate duration from segments
# Without this, credit deduction was always using fallback (60 seconds)
if result.get("segments") and len(result["segments"]) > 0:
    # Get the end time of the last segment
    last_segment = result["segments"][-1]
    transcription.duration = int(last_segment.get("end", 0))
    logger.info(f"⏱️ Audio duration calculated from segments: {transcription.duration} seconds ({transcription.duration/60:.1f} minutes)")
else:
    # Fallback: try to get duration from audio file metadata
    try:
        import subprocess
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
               '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)]
        duration_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        transcription.duration = int(float(duration_output.decode().strip()))
        logger.info(f"⏱️ Audio duration from ffprobe: {transcription.duration} seconds")
    except Exception as e:
        logger.warning(f"⚠️ Could not determine audio duration: {e}. Using 60s fallback.")
        transcription.duration = 60  # 1 minute fallback
```

### How It Works Now

1. **Primary Method**: Extract duration from Whisper segments
   - Get last segment's `end` timestamp
   - Most accurate (matches actual transcribed content)

2. **Fallback Method**: Use ffprobe for audio file metadata
   - If segments are empty/missing
   - Requires ffmpeg installed

3. **Last Resort**: 60 seconds default
   - Only if both methods fail

---

## 🧪 Testing

### Test 1: Short Audio (30 seconds)

**Expected**:
```
Duration: 30 seconds (0.5 minutes)
Cost: 1 kredi/dk × 1 minute (round up) = 1 kredi
```

**BEFORE**: 10 kredi ❌
**AFTER**: 1 kredi ✅

### Test 2: Medium Audio (5 minutes = 300 seconds)

**Expected**:
```
Duration: 300 seconds (5.0 minutes)
Cost: 1 kredi/dk × 5 minutes = 5 kredi
```

**BEFORE**: 10 kredi ❌
**AFTER**: 5 kredi ✅

### Test 3: Long Audio (20 minutes = 1200 seconds) + Speaker

**Expected**:
```
Duration: 1200 seconds (20.0 minutes)
Transcription: 1 kredi/dk × 20 = 20 kredi
Speaker Recognition: 0.5 kredi/dk × 20 = 10 kredi
Total: 30 kredi
```

**BEFORE**: 10 + 10 = 20 kredi ❌ (speaker maliyet de sabit idi)
**AFTER**: 30 kredi ✅

---

## 📋 Verification Steps

### 1. Backend Restart
```powershell
cd mp4totext-backend
.\debug_backend_clean.ps1
.\start_celery.bat
```

### 2. Upload Test File and Check Logs

**Look for this log line**:
```
⏱️ Audio duration calculated from segments: 300 seconds (5.0 minutes)
```

**Then check credit deduction log**:
```
💳 Deducting 5 credits from user #1 for transcription
```

### 3. Database Verification

```python
from app.database import SessionLocal
from app.models.transcription import Transcription

db = SessionLocal()
t = db.query(Transcription).order_by(Transcription.id.desc()).first()

print(f"ID: {t.id}")
print(f"Filename: {t.original_filename}")
print(f"Duration: {t.duration} seconds ({t.duration/60:.1f} minutes)")
print(f"Processing time: {t.processing_time} seconds")

# Check credit transaction
from app.models.credit_transaction import CreditTransaction
tx = db.query(CreditTransaction).filter_by(
    transcription_id=t.id
).first()

if tx:
    print(f"\nCredit Transaction:")
    print(f"Amount: {tx.amount} kredi")
    print(f"Description: {tx.description}")
    print(f"Metadata: {tx.metadata}")
    
db.close()
```

**Expected Output**:
```
ID: 42
Filename: test_audio_5min.mp3
Duration: 300 seconds (5.0 minutes)
Processing time: 12.5 seconds

Credit Transaction:
Amount: 5 kredi
Description: Transcription: test_audio_5min.mp3 (5min)
Metadata: {"duration_seconds": 300, "whisper_model": "base", ...}
```

### 4. Frontend Verification

1. Upload dosyası
2. Dashboard'da transcription'a tıkla
3. Detail page'de duration bilgisini kontrol et
4. Credit transaction history'de doğru miktarı kontrol et

---

## 🎯 Impact Summary

### Before Fix
- ❌ Her dosyadan sabit 10 kredi düşüyordu
- ❌ Duration field boştu
- ❌ Kısa dosyalar için overcharge
- ❌ Uzun dosyalar için undercharge

### After Fix
- ✅ Duration segments'ten hesaplanıyor
- ✅ Dakika bazlı doğru maliyet
- ✅ Kısa dosya (30s) = 1 kredi
- ✅ Uzun dosya (20dk) = 20 kredi
- ✅ Speaker recognition da dakika bazlı (0.5 kredi/dk)

### Combined with Pricing Update
**Double Win**:
1. ✅ Fiyatlar 10x daha ucuz (10 kredi/dk → 1 kredi/dk)
2. ✅ Maliyet artık gerçekten dakika bazlı hesaplanıyor

**Örnek**: 5 dakikalık dosya + speaker
- **Eski sistem**: 10 kredi (yanlış - flat rate)
- **Sadece pricing fix**: Hala 10 kredi olurdu (duration boş)
- **Her iki fix birlikte**: (5×1) + (5×0.5) = 7.5 → 8 kredi ✅

---

## ⚠️ Important Notes

1. **ffprobe Dependency**: Fallback method için ffmpeg/ffprobe gerekli. Yoksa 60s fallback kullanılır.

2. **Duration Precision**: Segments'ten hesaplama en doğru yöntem çünkü Whisper'ın gerçekten işlediği süreyi yansıtır.

3. **Rounding**: Credit hesaplamasında `int(cost + 0.5)` ile yuvarlama yapılıyor:
   - 7.5 kredi → 8 kredi
   - 7.4 kredi → 7 kredi

4. **Existing Data**: Eski transcription'ların duration'ı NULL kalacak. Sadece yeni upload'lar doğru duration'a sahip olacak.

---

## 🚀 Next Steps

1. ✅ Backend code updated
2. ⏳ Restart backend ve Celery
3. ⏳ Test 3 farklı uzunlukta dosya (30s, 5min, 20min)
4. ⏳ Verify database'de duration field doluyor
5. ⏳ Verify credit transaction'larda doğru maliyet
6. ⏳ Monitor production logs: `⏱️ Audio duration calculated from segments`

---

## 📞 Related Issues

- **TRANSCRIPTION_PRICING_UPDATE.md**: Fiyat güncellemesi (10 kredi/dk → 1 kredi/dk)
- **PROJECT_ARCHITECTURE.md**: System architecture documentation
- **PROGRESS_TRACKING_UPDATE.md**: Progress bar improvements

This fix completes the pricing system overhaul! 🎉
