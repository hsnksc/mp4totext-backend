# Backend Diagnostic Script
Write-Host "`n=== BACKEND DIAGNOSTIC ===" -ForegroundColor Cyan

# 1. Check Python processes
Write-Host "`n[1] Python processes:" -ForegroundColor Yellow
$pythonProcs = Get-Process -Name "python*" -ErrorAction SilentlyContinue
if ($pythonProcs) {
    $pythonProcs | Format-Table Id, ProcessName, StartTime -AutoSize
} else {
    Write-Host "NO PYTHON PROCESSES RUNNING!" -ForegroundColor Red
}

# 2. Check port 8000
Write-Host "`n[2] Port 8000 status:" -ForegroundColor Yellow
$port = netstat -ano | Select-String ":8000"
if ($port) {
    Write-Host "Port 8000 IN USE:" -ForegroundColor Green
    Write-Host $port
} else {
    Write-Host "PORT 8000 IS FREE - NOTHING IS LISTENING!" -ForegroundColor Red
}

# 3. Backend health check
Write-Host "`n[3] Backend health check:" -ForegroundColor Yellow
try {
    $response = curl.exe -s -m 3 http://localhost:8000/health
    Write-Host "Response: $response" -ForegroundColor Green
} catch {
    Write-Host "BACKEND NOT RESPONDING!" -ForegroundColor Red
}

# 4. CORS test
Write-Host "`n[4] CORS test (port 5173):" -ForegroundColor Yellow
$corsHeaders = curl.exe -s -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ -H "Origin: http://localhost:5173" 2>&1 | Select-String "access-control"
if ($corsHeaders) {
    Write-Host "CORS headers found:" -ForegroundColor Green
    $corsHeaders
} else {
    Write-Host "NO CORS HEADERS (backend not running or not responding)" -ForegroundColor Red
}

# 5. Docker containers
Write-Host "`n[5] Docker containers:" -ForegroundColor Yellow
docker ps --filter "name=mp4totext" --format "{{.Names}}: {{.Status}}"

# 6. Redis
Write-Host "`n[6] Redis:" -ForegroundColor Yellow
$redis = docker exec mp4totext-redis redis-cli -a dev_redis_123 ping 2>&1
Write-Host "Redis: $redis"

# 7. PostgreSQL
Write-Host "`n[7] PostgreSQL:" -ForegroundColor Yellow
$pg = docker exec mp4totext-postgres pg_isready -U dev_user 2>&1
Write-Host "PostgreSQL: $pg"

# Summary
Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
if (-not $pythonProcs) {
    Write-Host "CRITICAL: Backend is NOT running!" -ForegroundColor Red
    Write-Host "`nTo start backend:" -ForegroundColor Yellow
    Write-Host "  cd C:\Users\hasan\OneDrive\Desktop\mp4totext-backend" -ForegroundColor White
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug" -ForegroundColor White
} elseif (-not $port) {
    Write-Host "WARNING: Python running but port 8000 not listening!" -ForegroundColor Yellow
} elseif (-not $response) {
    Write-Host "WARNING: Process exists but backend not responding!" -ForegroundColor Yellow
} else {
    Write-Host "Backend appears to be running correctly!" -ForegroundColor Green
}

Write-Host "`n"
