@echo off
echo 🚀 MP4toText Backend Başlatılıyor...
echo.

REM Virtual environment'ı aktifleştir
call venv\Scripts\activate

REM Servislerin çalıştığını kontrol et
echo 📦 Docker servisleri kontrol ediliyor...
docker-compose ps

echo.
echo 🔧 Environment variables yükleniyor...

REM FastAPI sunucusunu başlat
echo.
echo 🌐 FastAPI sunucusu başlatılıyor (http://localhost:8000)...
echo 📚 API Docs: http://localhost:8000/docs
echo.
start /B uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

REM Birkaç saniye bekle
timeout /t 3 /nobreak > nul

REM Celery worker'ı başlat (ayrı pencerede)
echo.
echo ⚙️  Celery worker başlatılıyor...
start "Celery Worker" cmd /k "venv\Scripts\activate && celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo"

echo.
echo ✅ Backend başlatıldı!
echo.
pause
