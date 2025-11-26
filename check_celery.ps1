# Celery Worker Health Check Script
# Celery'nin çalışıp çalışmadığını kontrol eder

Write-Host "🔍 Celery Worker Durumu Kontrol Ediliyor..." -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Çalışma dizini
$WorkDir = "C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend"
Set-Location $WorkDir

# Virtual environment'ı aktifleştir
& "$WorkDir\venv\Scripts\Activate.ps1"

# 1. Python process kontrolü
Write-Host "1️⃣  Python Process Kontrolü:" -ForegroundColor Yellow
$PythonProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*mp4totext-backend*"
}

if ($PythonProcesses) {
    foreach ($proc in $PythonProcesses) {
        Write-Host "   ✅ Python Process bulundu:" -ForegroundColor Green
        Write-Host "      PID: $($proc.Id)" -ForegroundColor White
        Write-Host "      Path: $($proc.Path)" -ForegroundColor Gray
        
        # Process'in Celery olup olmadığını kontrol et
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
            if ($cmdLine -like "*celery*") {
                Write-Host "      ✅ Bu bir Celery Worker process'i" -ForegroundColor Green
            }
        } catch {
            Write-Host "      ⚠️  Command line bilgisi alınamadı" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "   ❌ Celery Worker process'i bulunamadı!" -ForegroundColor Red
}

Write-Host ""

# 2. Redis bağlantı kontrolü
Write-Host "2️⃣  Redis Bağlantı Kontrolü:" -ForegroundColor Yellow
try {
    $RedisTest = python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0); r.ping(); print('✅ Redis bağlantısı başarılı')"
    Write-Host "   $RedisTest" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Redis bağlantısı BAŞARISIZ!" -ForegroundColor Red
    Write-Host "   Redis çalışmıyor olabilir. Başlatmak için: redis-server" -ForegroundColor Yellow
}

Write-Host ""

# 3. Celery inspect kontrolü (worker aktif mi?)
Write-Host "3️⃣  Celery Worker Aktiflik Kontrolü:" -ForegroundColor Yellow
try {
    Write-Host "   Celery inspect çalıştırılıyor..." -ForegroundColor Gray
    
    # Timeout ile inspect
    $InspectJob = Start-Job -ScriptBlock {
        param($WorkDir)
        Set-Location $WorkDir
        & "$WorkDir\venv\Scripts\Activate.ps1"
        python -m celery -A app.celery_config inspect active 2>&1
    } -ArgumentList $WorkDir
    
    # 5 saniye timeout
    $Result = Wait-Job $InspectJob -Timeout 5
    
    if ($Result) {
        $Output = Receive-Job $InspectJob
        Remove-Job $InspectJob -Force
        
        if ($Output -like "*celery@*") {
            Write-Host "   ✅ Celery Worker AKTIF!" -ForegroundColor Green
            Write-Host "   Worker bilgisi:" -ForegroundColor White
            Write-Host "   $($Output -join "`n   ")" -ForegroundColor Gray
        } else {
            Write-Host "   ⚠️  Celery Worker yanıt vermiyor veya aktif task yok" -ForegroundColor Yellow
            Write-Host "   Output: $Output" -ForegroundColor Gray
        }
    } else {
        Remove-Job $InspectJob -Force
        Write-Host "   ⚠️  Celery inspect timeout (5 saniye)" -ForegroundColor Yellow
        Write-Host "   Worker çalışmıyor olabilir" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Celery inspect HATA: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan

# Özet
Write-Host ""
Write-Host "📊 ÖZET:" -ForegroundColor Cyan
if ($PythonProcesses -and $RedisTest -like "*başarılı*") {
    Write-Host "   ✅ Celery Worker muhtemelen ÇALIŞIYOR" -ForegroundColor Green
    Write-Host "   Eğer task işlenmiyor ise:" -ForegroundColor Yellow
    Write-Host "   1. start_celery.ps1 ile yeniden başlatın" -ForegroundColor White
    Write-Host "   2. Redis'in çalıştığından emin olun (redis-server)" -ForegroundColor White
} else {
    Write-Host "   ❌ Celery Worker ÇALIŞMIYOR!" -ForegroundColor Red
    Write-Host "   Başlatmak için:" -ForegroundColor Yellow
    Write-Host "   .\start_celery.ps1" -ForegroundColor White
}

Write-Host ""
