@echo off
echo 🚀 Starting 4 Celery Workers...
echo.
echo ⚠️ WARNING: This will consume 4-40GB RAM depending on Whisper model!
echo Press Ctrl+C to cancel, or wait 5 seconds to continue...
timeout /t 5

echo.
echo Starting workers...

start "Celery Worker 1" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker1@%%h --max-memory-per-child=2000000"

timeout /t 2

start "Celery Worker 2" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker2@%%h --max-memory-per-child=2000000"

timeout /t 2

start "Celery Worker 3" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker3@%%h --max-memory-per-child=2000000"

timeout /t 2

start "Celery Worker 4" cmd /k "cd /d %~dp0 && .\venv\Scripts\python.exe -m celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo --hostname=worker4@%%h --max-memory-per-child=2000000"

echo.
echo ✅ 4 Celery Workers started!
echo.
echo To stop all workers, run: taskkill /F /IM python.exe
echo.
pause
