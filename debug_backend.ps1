# 🔍 Backend Hata Debug Scripti

Bu script backend'inizin durumunu kontrol eder ve sorunları tespit eder.

## Kullanım

```powershell
# Script'i çalıştır
.\debug_backend.ps1
```

## Script İçeriği

```powershell
# Backend Debug Script
Write-Host "🔍 MP4toText Backend Diagnostic Tool" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. Docker Container Status
Write-Host "📦 Docker Container Status:" -ForegroundColor Yellow
docker ps --filter "name=mp4totext" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""

# 2. Redis Connection Test
Write-Host "🔴 Redis Connection Test:" -ForegroundColor Yellow
try {
    $redisTest = docker exec mp4totext-redis redis-cli -a dev_redis_123 ping 2>&1
    if ($redisTest -match "PONG") {
        Write-Host "✅ Redis: OK" -ForegroundColor Green
    } else {
        Write-Host "❌ Redis: FAILED - $redisTest" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Redis container not running" -ForegroundColor Red
}
Write-Host ""

# 3. PostgreSQL Connection Test
Write-Host "🐘 PostgreSQL Connection Test:" -ForegroundColor Yellow
try {
    $pgTest = docker exec mp4totext-postgres pg_isready -U dev_user 2>&1
    if ($pgTest -match "accepting connections") {
        Write-Host "✅ PostgreSQL: OK" -ForegroundColor Green
    } else {
        Write-Host "❌ PostgreSQL: FAILED - $pgTest" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ PostgreSQL container not running" -ForegroundColor Red
}
Write-Host ""

# 4. Backend Health Check
Write-Host "🏥 Backend Health Check:" -ForegroundColor Yellow
try {
    $health = curl.exe -s http://localhost:8000/health 2>&1
    if ($health -match "healthy") {
        Write-Host "✅ Backend: HEALTHY" -ForegroundColor Green
        Write-Host $health
    } else {
        Write-Host "❌ Backend: NOT RESPONDING" -ForegroundColor Red
        Write-Host "   Start backend with: .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    }
} catch {
    Write-Host "❌ Backend not running" -ForegroundColor Red
}
Write-Host ""

# 5. CORS Preflight Test (Port 5173)
Write-Host "🌐 CORS Test (Port 5173):" -ForegroundColor Yellow
try {
    $cors5173 = curl.exe -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: POST" 2>&1
    if ($cors5173 -match "access-control-allow-origin: http://localhost:5173") {
        Write-Host "✅ CORS for 5173: OK" -ForegroundColor Green
    } else {
        Write-Host "❌ CORS for 5173: FAILED" -ForegroundColor Red
        Write-Host $cors5173
    }
} catch {
    Write-Host "❌ CORS test failed" -ForegroundColor Red
}
Write-Host ""

# 6. CORS Preflight Test (Port 5174)
Write-Host "🌐 CORS Test (Port 5174):" -ForegroundColor Yellow
try {
    $cors5174 = curl.exe -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ -H "Origin: http://localhost:5174" -H "Access-Control-Request-Method: POST" 2>&1
    if ($cors5174 -match "access-control-allow-origin: http://localhost:5174") {
        Write-Host "✅ CORS for 5174: OK" -ForegroundColor Green
    } else {
        Write-Host "❌ CORS for 5174: FAILED" -ForegroundColor Red
        Write-Host $cors5174
    }
} catch {
    Write-Host "❌ CORS test failed" -ForegroundColor Red
}
Write-Host ""

# 7. Frontend Status Check
Write-Host "⚛️  Frontend Status:" -ForegroundColor Yellow
try {
    $frontend5173 = curl.exe -s http://localhost:5173 2>&1
    if ($frontend5173 -match "<!doctype" -or $frontend5173 -match "<html") {
        Write-Host "✅ Frontend on 5173: RUNNING" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Frontend on 5173: NOT RUNNING" -ForegroundColor Yellow
    }
    
    $frontend5174 = curl.exe -s http://localhost:5174 2>&1
    if ($frontend5174 -match "<!doctype" -or $frontend5174 -match "<html") {
        Write-Host "✅ Frontend on 5174: RUNNING" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Frontend on 5174: NOT RUNNING" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Frontend check failed" -ForegroundColor Red
}
Write-Host ""

# 8. Port Usage Check
Write-Host "🔌 Port Usage:" -ForegroundColor Yellow
Write-Host "Backend (8000):"
netstat -ano | Select-String ":8000" | Select-Object -First 1
Write-Host "Frontend (5173):"
netstat -ano | Select-String ":5173" | Select-Object -First 1
Write-Host "Frontend (5174):"
netstat -ano | Select-String ":5174" | Select-Object -First 1
Write-Host ""

# 9. Virtual Environment Check
Write-Host "🐍 Python Virtual Environment:" -ForegroundColor Yellow
$backendPath = "C:\Users\hasan\OneDrive\Desktop\mp4totext-backend"
if (Test-Path "$backendPath\venv\Scripts\python.exe") {
    Write-Host "✅ venv found at: $backendPath\venv" -ForegroundColor Green
    & "$backendPath\venv\Scripts\python.exe" --version
} else {
    Write-Host "❌ venv not found at: $backendPath\venv" -ForegroundColor Red
}
Write-Host ""

# 10. .env File Check
Write-Host "📄 Environment Configuration:" -ForegroundColor Yellow
if (Test-Path "$backendPath\.env") {
    Write-Host "✅ .env file exists" -ForegroundColor Green
    Write-Host ""
    Write-Host "Key Variables:" -ForegroundColor Cyan
    Get-Content "$backendPath\.env" | Select-String -Pattern "DATABASE_URL|REDIS_URL|CELERY_BROKER_URL|CORS_ORIGINS" | ForEach-Object {
        $line = $_.Line
        # Şifreleri gizle
        $line = $line -replace '(password|secret|key)=[^@\s]+', '$1=***'
        Write-Host "   $line"
    }
} else {
    Write-Host "❌ .env file not found" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "🎯 SUMMARY & NEXT STEPS" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Quick Actions
Write-Host "Quick Actions:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Start Redis:" -ForegroundColor White
Write-Host "  docker start mp4totext-redis" -ForegroundColor Gray
Write-Host ""
Write-Host "Start PostgreSQL:" -ForegroundColor White
Write-Host "  docker start mp4totext-postgres" -ForegroundColor Gray
Write-Host ""
Write-Host "Start Backend:" -ForegroundColor White
Write-Host "  cd C:\Users\hasan\OneDrive\Desktop\mp4totext-backend" -ForegroundColor Gray
Write-Host "  .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "Start Frontend:" -ForegroundColor White
Write-Host "  cd C:\Users\hasan\OneDrive\Desktop\mp4totext-web" -ForegroundColor Gray
Write-Host "  npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "Clear Browser Cache:" -ForegroundColor White
Write-Host "  Press: Ctrl + Shift + Delete" -ForegroundColor Gray
Write-Host "  Or use Incognito/Private window: Ctrl + Shift + N" -ForegroundColor Gray
Write-Host ""
```

# Backend Debug Script
Write-Host "MP4toText Backend Diagnostic Tool" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

```
🔍 MP4toText Backend Diagnostic Tool
=====================================

📦 Docker Container Status:
NAMES                STATUS               PORTS
mp4totext-redis      Up 34 hours          0.0.0.0:6379->6379/tcp
mp4totext-postgres   Up 34 hours          0.0.0.0:5432->5432/tcp

🔴 Redis Connection Test:
✅ Redis: OK

🐘 PostgreSQL Connection Test:
✅ PostgreSQL: OK

🏥 Backend Health Check:
✅ Backend: HEALTHY
{"status":"healthy","timestamp":"2025-10-21T08:56:40.803256"}

🌐 CORS Test (Port 5173):
✅ CORS for 5173: OK

🌐 CORS Test (Port 5174):
✅ CORS for 5174: OK

⚛️  Frontend Status:
✅ Frontend on 5173: RUNNING

🔌 Port Usage:
Backend (8000): TCP    0.0.0.0:8000    LISTENING    12345

🐍 Python Virtual Environment:
✅ venv found at: C:\Users\hasan\OneDrive\Desktop\mp4totext-backend\venv
Python 3.11.5

📄 Environment Configuration:
✅ .env file exists
Key Variables:
   DATABASE_URL=postgresql://dev_user:password=***@localhost:5432/mp4totext_dev
   REDIS_URL=redis://:password=***@localhost:6379/0
   CELERY_BROKER_URL=redis://:password=***@localhost:6379/1
```
