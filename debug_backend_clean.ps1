# MP4toText Backend Diagnostic Tool
# Run this script to check all backend services and configurations

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  MP4toText Backend Diagnostic Tool" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Docker Container Status
Write-Host "1. Docker Container Status:" -ForegroundColor Yellow
docker ps --filter "name=mp4totext" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""

# 2. Redis Connection Test
Write-Host "2. Redis Connection Test:" -ForegroundColor Yellow
try {
    $redisTest = docker exec mp4totext-redis redis-cli -a dev_redis_123 ping 2>&1
    if ($redisTest -match "PONG") {
        Write-Host "   [OK] Redis is responding" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] Redis error: $redisTest" -ForegroundColor Red
    }
} catch {
    Write-Host "   [FAIL] Redis container not running" -ForegroundColor Red
}
Write-Host ""

# 3. PostgreSQL Connection Test
Write-Host "3. PostgreSQL Connection Test:" -ForegroundColor Yellow
try {
    $pgTest = docker exec mp4totext-postgres pg_isready -U dev_user 2>&1
    if ($pgTest -match "accepting connections") {
        Write-Host "   [OK] PostgreSQL is accepting connections" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] PostgreSQL error: $pgTest" -ForegroundColor Red
    }
} catch {
    Write-Host "   [FAIL] PostgreSQL container not running" -ForegroundColor Red
}
Write-Host ""

# 4. Backend Health Check
Write-Host "4. Backend Health Check:" -ForegroundColor Yellow
try {
    $health = curl.exe -s http://localhost:8000/health 2>&1
    if ($health -match "healthy") {
        Write-Host "   [OK] Backend is healthy" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] Backend is not responding" -ForegroundColor Red
        Write-Host "   Run: .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Gray
    }
} catch {
    Write-Host "   [FAIL] Backend not running" -ForegroundColor Red
}
Write-Host ""

# 5. CORS Test for Port 5173
Write-Host "5. CORS Test (Port 5173):" -ForegroundColor Yellow
try {
    $cors5173 = curl.exe -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: POST" 2>&1
    if ($cors5173 -match "access-control-allow-origin: http://localhost:5173") {
        Write-Host "   [OK] CORS for port 5173 is configured" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] CORS for port 5173 failed" -ForegroundColor Red
    }
} catch {
    Write-Host "   [FAIL] CORS test failed" -ForegroundColor Red
}
Write-Host ""

# 6. CORS Test for Port 5174
Write-Host "6. CORS Test (Port 5174):" -ForegroundColor Yellow
try {
    $cors5174 = curl.exe -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ -H "Origin: http://localhost:5174" -H "Access-Control-Request-Method: POST" 2>&1
    if ($cors5174 -match "access-control-allow-origin: http://localhost:5174") {
        Write-Host "   [OK] CORS for port 5174 is configured" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] CORS for port 5174 failed" -ForegroundColor Red
    }
} catch {
    Write-Host "   [FAIL] CORS test failed" -ForegroundColor Red
}
Write-Host ""

# 7. Frontend Status
Write-Host "7. Frontend Status:" -ForegroundColor Yellow
$frontend5173 = curl.exe -s http://localhost:5173 2>&1
if ($frontend5173 -match "<!doctype" -or $frontend5173 -match "<html") {
    Write-Host "   [OK] Frontend on port 5173 is running" -ForegroundColor Green
} else {
    Write-Host "   [INFO] Frontend on port 5173 is not running" -ForegroundColor Yellow
}

$frontend5174 = curl.exe -s http://localhost:5174 2>&1
if ($frontend5174 -match "<!doctype" -or $frontend5174 -match "<html") {
    Write-Host "   [OK] Frontend on port 5174 is running" -ForegroundColor Green
} else {
    Write-Host "   [INFO] Frontend on port 5174 is not running" -ForegroundColor Yellow
}
Write-Host ""

# 8. Port Usage
Write-Host "8. Port Usage:" -ForegroundColor Yellow
Write-Host "   Backend (8000):"
$port8000 = netstat -ano | Select-String ":8000.*LISTENING"
if ($port8000) {
    Write-Host "   [OK] Port 8000 is in use" -ForegroundColor Green
} else {
    Write-Host "   [INFO] Port 8000 is free" -ForegroundColor Yellow
}

Write-Host "   Frontend (5173):"
$port5173 = netstat -ano | Select-String ":5173.*LISTENING"
if ($port5173) {
    Write-Host "   [OK] Port 5173 is in use" -ForegroundColor Green
} else {
    Write-Host "   [INFO] Port 5173 is free" -ForegroundColor Yellow
}
Write-Host ""

# 9. Virtual Environment Check
Write-Host "9. Python Virtual Environment:" -ForegroundColor Yellow
$backendPath = "C:\Users\hasan\OneDrive\Desktop\mp4totext-backend"
if (Test-Path "$backendPath\venv\Scripts\python.exe") {
    Write-Host "   [OK] venv found" -ForegroundColor Green
    $pythonVersion = & "$backendPath\venv\Scripts\python.exe" --version 2>&1
    Write-Host "   $pythonVersion" -ForegroundColor Gray
} else {
    Write-Host "   [FAIL] venv not found at: $backendPath\venv" -ForegroundColor Red
}
Write-Host ""

# 10. Environment File Check
Write-Host "10. Environment Configuration:" -ForegroundColor Yellow
if (Test-Path "$backendPath\.env") {
    Write-Host "   [OK] .env file exists" -ForegroundColor Green
    Write-Host "   Key variables:" -ForegroundColor Gray
    Get-Content "$backendPath\.env" | Select-String -Pattern "^(DATABASE_URL|REDIS_URL|CELERY_BROKER_URL|CORS_ORIGINS)=" | ForEach-Object {
        $line = $_.Line
        $line = $line -replace '(password|secret|key)=[^@\s]+', '$1=***'
        Write-Host "     $line" -ForegroundColor DarkGray
    }
} else {
    Write-Host "   [FAIL] .env file not found" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  SUMMARY & QUICK ACTIONS" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
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
Write-Host "  Ctrl + Shift + Delete (or use Incognito: Ctrl + Shift + N)" -ForegroundColor Gray
Write-Host ""
