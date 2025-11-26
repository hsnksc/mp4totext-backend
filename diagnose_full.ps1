# 🔍 FULL DIAGNOSTIC SCRIPT - Backend Problem Tespiti
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "🔍 MP4TOTEXT BACKEND FULL DIAGNOSTIC" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. BACKEND PROCESS KONTROLÜ
Write-Host "1️⃣ BACKEND PROCESS KONTROLÜ:" -ForegroundColor Yellow
$pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*mp4totext*" -or $_.CommandLine -like "*uvicorn*"
}
if ($pythonProcesses) {
    Write-Host "✅ Python process(es) bulundu:" -ForegroundColor Green
    $pythonProcesses | Format-Table Id, ProcessName, Path, StartTime -AutoSize
} else {
    Write-Host "❌ BACKEND ÇALIŞMIYOR! Hiç Python/Uvicorn process yok." -ForegroundColor Red
}

# 2. PORT 8000 KONTROLÜ
Write-Host "`n2️⃣ PORT 8000 KONTROLÜ:" -ForegroundColor Yellow
$port8000 = netstat -ano | Select-String ":8000"
if ($port8000) {
    Write-Host "✅ Port 8000'de bir process dinliyor:" -ForegroundColor Green
    Write-Host $port8000 -ForegroundColor White
    
    # PID'yi çıkar
    $portLine = $port8000.ToString()
    if ($portLine -match '\s+(\d+)\s*$') {
        $pid = $matches[1]
        Write-Host "`n📌 Process ID: $pid" -ForegroundColor Cyan
        try {
            $process = Get-Process -Id $pid -ErrorAction Stop
            Write-Host "📌 Process Name: $($process.ProcessName)" -ForegroundColor Cyan
            Write-Host "📌 Process Path: $($process.Path)" -ForegroundColor Cyan
        } catch {
            Write-Host "⚠️ Process bilgisi alınamadı" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "❌ Port 8000'de HİÇBİR ŞEYLER DİNLEMİYOR!" -ForegroundColor Red
    Write-Host "   Backend başlatılmamış olabilir." -ForegroundColor Red
}

# 3. BACKEND HEALTH CHECK
Write-Host "`n3️⃣ BACKEND HEALTH CHECK:" -ForegroundColor Yellow
try {
    $health = curl.exe -s -m 3 http://localhost:8000/health 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Backend cevap veriyor:" -ForegroundColor Green
        Write-Host $health -ForegroundColor White
    } else {
        Write-Host "❌ Backend CEVAP VERMİYOR (timeout veya bağlantı reddi)" -ForegroundColor Red
        Write-Host "   Curl error: $health" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Health check BAŞARISIZ: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. CORS PREFLIGHT TEST
Write-Host "`n4️⃣ CORS PREFLIGHT TEST (Port 5173):" -ForegroundColor Yellow
try {
    $corsTest = curl.exe -s -m 3 -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ `
        -H "Origin: http://localhost:5173" `
        -H "Access-Control-Request-Method: POST" `
        -H "Access-Control-Request-Headers: content-type" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $hasOrigin = $corsTest | Select-String "access-control-allow-origin"
        if ($hasOrigin) {
            Write-Host "✅ CORS headers mevcut:" -ForegroundColor Green
            Write-Host ($corsTest | Select-String "access-control") -ForegroundColor White
        } else {
            Write-Host "❌ CORS headers YOK!" -ForegroundColor Red
            Write-Host $corsTest -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ CORS test BAŞARISIZ (backend cevap vermedi)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ CORS test hatası: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. DOCKER CONTAINERS
Write-Host "`n5️⃣ DOCKER CONTAINERS:" -ForegroundColor Yellow
$containers = docker ps --filter "name=mp4totext" --format "{{.Names}}: {{.Status}}" 2>&1
if ($LASTEXITCODE -eq 0) {
    $containerList = $containers | Out-String
    if ($containerList.Trim()) {
        Write-Host "✅ Docker containers:" -ForegroundColor Green
        Write-Host $containerList -ForegroundColor White
    } else {
        Write-Host "⚠️ Hiç mp4totext container çalışmıyor" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Docker kontrol edilemedi: $containers" -ForegroundColor Red
}

# 6. REDIS TEST
Write-Host "`n6️⃣ REDIS BAĞLANTI TEST:" -ForegroundColor Yellow
try {
    $redisPing = docker exec mp4totext-redis redis-cli -a dev_redis_123 ping 2>&1
    if ($redisPing -like "*PONG*") {
        Write-Host "✅ Redis cevap veriyor: PONG" -ForegroundColor Green
    } else {
        Write-Host "❌ Redis cevap vermiyor: $redisPing" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Redis test hatası: $($_.Exception.Message)" -ForegroundColor Red
}

# 7. POSTGRESQL TEST
Write-Host "`n7️⃣ POSTGRESQL BAĞLANTI TEST:" -ForegroundColor Yellow
try {
    $pgTest = docker exec mp4totext-postgres pg_isready -U dev_user 2>&1
    if ($pgTest -like "*accepting connections*") {
        Write-Host "✅ PostgreSQL accepting connections" -ForegroundColor Green
    } else {
        Write-Host "❌ PostgreSQL sorunlu: $pgTest" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ PostgreSQL test hatası: $($_.Exception.Message)" -ForegroundColor Red
}

# 8. FRONTEND STATUS
Write-Host "`n8️⃣ FRONTEND STATUS (Port 5173):" -ForegroundColor Yellow
try {
    $frontendTest = curl.exe -s -m 3 -I http://localhost:5173 2>&1
    if ($LASTEXITCODE -eq 0 -and $frontendTest -like "*200 OK*") {
        Write-Host "✅ Frontend çalışıyor (port 5173)" -ForegroundColor Green
    } else {
        Write-Host "❌ Frontend cevap vermiyor (port 5173)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Frontend test hatası" -ForegroundColor Red
}

# 9. VENV CHECK
Write-Host "`n9️⃣ PYTHON VENV KONTROLÜ:" -ForegroundColor Yellow
$venvPath = "C:\Users\hasan\OneDrive\Desktop\mp4totext-backend\venv"
if (Test-Path "$venvPath\Scripts\python.exe") {
    Write-Host "✅ Virtual environment mevcut: $venvPath" -ForegroundColor Green
    $pythonVersion = & "$venvPath\Scripts\python.exe" --version 2>&1
    Write-Host "   Python version: $pythonVersion" -ForegroundColor White
} else {
    Write-Host "❌ Virtual environment BULUNAMADI: $venvPath" -ForegroundColor Red
}

# 10. .ENV FILE CHECK
Write-Host "`n🔟 .ENV FILE KONTROLÜ:" -ForegroundColor Yellow
$envPath = "C:\Users\hasan\OneDrive\Desktop\mp4totext-backend\.env"
if (Test-Path $envPath) {
    Write-Host "✅ .env dosyası mevcut" -ForegroundColor Green
    $envContent = Get-Content $envPath | Select-String "DATABASE_URL|REDIS_URL|CELERY_BROKER_URL"
    if ($envContent) {
        Write-Host "   Önemli değişkenler:" -ForegroundColor White
        $envContent | ForEach-Object {
            $line = $_.Line -replace "=.*", "=***"  # Şifreleri gizle
            Write-Host "   $line" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "❌ .env dosyası BULUNAMADI!" -ForegroundColor Red
}

# SUMMARY
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "📊 ÖZET VE ÖNERİLER" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if (-not $pythonProcesses) {
    Write-Host "🚨 KRİTİK: Backend çalışmıyor!" -ForegroundColor Red
    Write-Host "   Çözüm: Backend'i başlatın:" -ForegroundColor Yellow
    Write-Host "   cd C:\Users\hasan\OneDrive\Desktop\mp4totext-backend" -ForegroundColor White
    Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug`n" -ForegroundColor White
}

if (-not $port8000) {
    Write-Host "🚨 KRİTİK: Port 8000 boş (hiçbir şey dinlemiyor)!" -ForegroundColor Red
    Write-Host "   Backend başlatılmamış olabilir.`n" -ForegroundColor Yellow
}

if ($pythonProcesses -and $port8000 -and ($health -notlike "*healthy*")) {
    Write-Host "⚠️ UYARI: Process var ama backend cevap vermiyor!" -ForegroundColor Yellow
    Write-Host "   Backend cokmus veya yanlis portta olabilir.`n" -ForegroundColor Yellow
}

Write-Host "========================================`n" -ForegroundColor Cyan
