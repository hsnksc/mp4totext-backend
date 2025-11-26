@echo off
cd /d "%~dp0"

REM Add local FFmpeg 7.1 to PATH (TorchCodec compatible)
set PATH=C:\Users\hasan\OneDrive\Desktop\mp4totext\ffmpeg\bin;%PATH%

echo 🚀 Starting Celery Worker with Auto-Restart...
echo 📦 FFmpeg 7.1 added to PATH
echo.

:start
echo [%date% %time%] Celery Worker Starting...
.\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --max-memory-per-child=2000000

echo.
echo [%date% %time%] ⚠️ Celery Worker Stopped!
echo Waiting 5 seconds before auto-restart...
timeout /t 5 /nobreak >nul
echo.

goto start
