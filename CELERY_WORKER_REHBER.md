# 🔧 Celery Worker Kullanım Rehberi

## ✅ Auto-Restart Özelliği

### Evet, şu an uygulandı! ✅

**`start_celery.bat`** dosyası şimdi şunları yapıyor:

1. ✅ Worker başlatır
2. ✅ Worker kapanırsa **5 saniye bekler**
3. ✅ **Otomatik yeniden başlatır**
4. ✅ Sonsuz döngü (kapanana kadar devam eder)

### Test:

```powershell
# Terminal açıp bu komutu çalıştır
.\start_celery.bat

# Worker'ı test etmek için başka terminalden kapat
taskkill /F /PID <worker_pid>

# 5 saniye sonra otomatik yeniden başlar! 🎉
```

---

## 👥 Birden Fazla Celery Worker Durumu

### Senaryo 1: Aynı Redis'e Bağlı Çoklu Worker ✅

**Ne olur?**
- ✅ **Task'ler aralarında paylaşılır** (load balancing)
- ✅ **Paralel işlem** (bir worker X dosyasını, diğeri Y dosyasını işler)
- ✅ **Hız artar** (4 worker = 4 dosya aynı anda)
- ✅ **Birisi kapansa diğerleri devam eder**

**Örnek:**

```
┌─────────────┐
│   Redis     │ ◄─── Task Queue (10 task var)
└──────┬──────┘
       │
       ├─────► Worker 1 (Task 1, 5, 9 alır)
       ├─────► Worker 2 (Task 2, 6, 10 alır)
       ├─────► Worker 3 (Task 3, 7 alır)
       └─────► Worker 4 (Task 4, 8 alır)
```

### Kullanım:

```powershell
# Terminal 1
.\start_celery.bat

# Terminal 2 (başka terminal aç)
cd mp4totext-backend
.\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker2@%h

# Terminal 3 (3. worker)
cd mp4totext-backend
.\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker3@%h
```

**Avantajlar:**
- ⚡ **Hız**: 4 dosya aynı anda işlenir
- 🛡️ **Güvenilirlik**: Bir worker crash ederse diğerleri devam eder
- 💪 **Ölçeklenebilirlik**: İhtiyaca göre worker sayısı artar

**Dikkat:**
- ⚠️ **RAM tüketimi**: Her worker ~2-10GB RAM kullanır (Whisper model'e göre)
- ⚠️ **CPU**: Her worker 1 CPU core kullanır
- ⚠️ **Hostname gerekli**: `--hostname=workerX@%h` olmazsa conflict olur

---

### Senaryo 2: Aynı Hostname ile Çoklu Worker ❌

**Ne olur?**
- ❌ **Conflict** (çakışma)
- ❌ **Task'ler kaybolabilir**
- ❌ **Worker'lar birbirini devre dışı bırakır**

**Örnek YANLIŞ kullanım:**

```powershell
# Terminal 1
.\start_celery.bat  # hostname: celery@DESKTOP-ABC

# Terminal 2
.\start_celery.bat  # hostname: celery@DESKTOP-ABC (AYNI!)

# Sonuç: ❌ ÇAKIŞMA!
```

**Çözüm:** Her worker'a farklı hostname ver:

```bash
--hostname=worker1@%h
--hostname=worker2@%h
--hostname=worker3@%h
```

---

### Senaryo 3: Farklı Queue'lara Atanmış Worker'lar 🎯

**Kullanım durumu:** Öncelikli işlemler için ayrı queue

**Örnek:**

```python
# Backend'de task gönderirken:
process_transcription_task.apply_async(
    args=[transcription_id],
    queue='high_priority'  # Özel queue
)
```

```powershell
# Worker 1: Normal queue
celery -A app.workers.transcription_worker worker --queue=default

# Worker 2: High priority queue
celery -A app.workers.transcription_worker worker --queue=high_priority

# Worker 3: Her ikisi de
celery -A app.workers.transcription_worker worker --queue=default,high_priority
```

---

## 🔍 Worker Durumunu Kontrol Etme

### 1. Kaç Worker Çalışıyor?

```powershell
# PowerShell
Get-Process python | Where-Object {
    (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*celery*worker*"
}

# Her satır = 1 worker
```

### 2. Worker İsimleri Neler?

```powershell
cd mp4totext-backend
.\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker inspect active_queues
```

### 3. Aktif Task'ler

```powershell
.\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker inspect active
```

---

## 💡 Önerilen Kullanım

### Geliştirme Ortamı (Local):

```powershell
# 1 worker yeterli (RAM tasarrufu)
.\start_celery.bat
```

### Production (Sunucu):

```powershell
# 4 worker (paralel işlem için)
# Ancak RAM'iniz yeterli olmalı!

# CPU sayısını kontrol et
Get-WmiObject -Class Win32_Processor | Select-Object NumberOfCores

# 4 core varsa → 3-4 worker açabilirsin
# 8 core varsa → 6-8 worker açabilirsin

# Örnek: 4 worker başlatma
start powershell -ArgumentList "-NoExit", "-Command", "cd $PWD; .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker1@%h"

start powershell -ArgumentList "-NoExit", "-Command", "cd $PWD; .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker2@%h"

start powershell -ArgumentList "-NoExit", "-Command", "cd $PWD; .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker3@%h"

start powershell -ArgumentList "-NoExit", "-Command", "cd $PWD; .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker4@%h"
```

---

## ⚠️ Önemli Notlar

### RAM Hesaplama:

| Whisper Model | Worker Başına RAM | 4 Worker Toplam RAM |
|---------------|-------------------|---------------------|
| base          | ~1 GB             | ~4 GB               |
| small         | ~2 GB             | ~8 GB               |
| medium        | ~5 GB             | ~20 GB              |
| large         | ~10 GB            | ~40 GB              |

### Sistem RAM'inizi kontrol edin:

```powershell
Get-WmiObject -Class Win32_ComputerSystem | Select-Object TotalPhysicalMemory
```

**Örnek:**
- 16 GB RAM → **base model ile 4 worker** ✅
- 16 GB RAM → **medium model ile 4 worker** ❌ (RAM yetersiz)
- 32 GB RAM → **medium model ile 4 worker** ✅

---

## 🚀 Hızlı Başlangıç Komutları

### Tek Worker (Recommended):

```powershell
.\start_celery.bat
```

### Çoklu Worker (Production):

```powershell
# start_all_workers.bat dosyası oluştur:
@echo off
start "Worker 1" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker1@%%h"

start "Worker 2" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker2@%%h"

start "Worker 3" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker3@%%h"

start "Worker 4" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker4@%%h"

echo 4 Celery Worker started!
```

### Tüm Worker'ları Durdurma:

```powershell
taskkill /F /IM python.exe
```

---

## 📊 Özet

| Özellik | Tek Worker | Çoklu Worker (Aynı Queue) | Çoklu Worker (Farklı Queue) |
|---------|------------|---------------------------|----------------------------|
| **Hız** | Normal | 2-4x Hızlı | Öncelikli işlemler hızlı |
| **RAM** | 1-10 GB | 4-40 GB | 4-40 GB |
| **Karmaşıklık** | Basit | Orta | Zor |
| **Önerilen** | Geliştirme | Production | Enterprise |

---

**Son Güncelleme:** 22 Ekim 2025  
**Durum:** ✅ Auto-Restart Aktif
