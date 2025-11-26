# 🔍 MP4toText Service Health Check
# Tüm servislerin çalışıp çalışmadığını kontrol eder

Write-Host "🔍 MP4toText Service Health Check" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Backend kontrolü (Port 8002)
Write-Host "1️⃣ Backend (FastAPI - Port 8002):" -NoNewline
$backend = Get-NetTCPConnection -LocalPort 8002 -State Listen -ErrorAction SilentlyContinue
if ($backend) {
    Write-Host " ✅ RUNNING" -ForegroundColor Green
} else {
    Write-Host " ❌ NOT RUNNING" -ForegroundColor Red
}

# Frontend kontrolü (Port 5173)
Write-Host "2️⃣ Frontend (Vite - Port 5173):" -NoNewline
$frontend = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($frontend) {
    Write-Host " ✅ RUNNING" -ForegroundColor Green
} else {
    Write-Host " ❌ NOT RUNNING" -ForegroundColor Red
}

# Redis kontrolü (Port 6379)
Write-Host "3️⃣ Redis (Port 6379):" -NoNewline
$redis = Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue
if ($redis) {
    Write-Host " ✅ RUNNING" -ForegroundColor Green
} else {
    Write-Host " ❌ NOT RUNNING" -ForegroundColor Red
}

# Celery Worker kontrolü
Write-Host "4️⃣ Celery Worker:" -NoNewline
$celery = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*celery*worker*"
}
if ($celery) {
    Write-Host " ✅ RUNNING (PID: $($celery.Id))" -ForegroundColor Green
} else {
    Write-Host " ❌ NOT RUNNING" -ForegroundColor Red
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan

# Özet
$allRunning = $backend -and $frontend -and $redis -and $celery
if ($allRunning) {
    Write-Host "🎉 All services are running!" -ForegroundColor Green
} else {
    Write-Host "⚠️ Some services are not running. Please check above." -ForegroundColor Yellow
}
