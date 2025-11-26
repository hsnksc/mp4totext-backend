# Start Celery Worker for MP4toText - Otomatik Restart
Write-Host "Celery Worker Otomatik Baslatma" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Set-Location $PSScriptRoot
Write-Host "Calisma Dizini: $PSScriptRoot" -ForegroundColor White

# Add local FFmpeg 7.1 to PATH (TorchCodec compatible)
$env:PATH = "C:\Users\hasan\OneDrive\Desktop\mp4totext\ffmpeg\bin;" + $env:PATH
Write-Host "FFmpeg 7.1 PATH'e eklendi" -ForegroundColor Yellow

# Activate venv
& "$PSScriptRoot\venv\Scripts\Activate.ps1"
Write-Host "Virtual environment aktif" -ForegroundColor Green
Write-Host ""

# Sonsuz dongude Celery'yi surekli calistir
$RestartCount = 0
while ($true) {
    if ($RestartCount -gt 0) {
        Write-Host ""
        Write-Host "Celery Worker yeniden baslatiliyor... (Restart #$RestartCount)" -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
    
    Write-Host "Celery Worker calisiyor..." -ForegroundColor Green
    Write-Host "   MOD: CONCURRENT USER TESTING (4 workers, autoscale 4-2)" -ForegroundColor Cyan
    Write-Host "   Durdurmak icin: Ctrl+C tuslayin" -ForegroundColor Gray
    Write-Host "   Celery Broker: redis://localhost:6379/0" -ForegroundColor Gray
    Write-Host "   Queue: high (transcriptions)" -ForegroundColor Gray
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Celery'yi CONCURRENT TESTING mode ile calistir
    # --pool=solo: Single-threaded but reliable on Windows
    # Windows'ta prefork/gevent sorunlu, solo stabil
    # -Q: Tum queue'lari dinle (celery + priority queues)
    python -m celery -A app.celery_config worker --loglevel=info --pool=solo -Q celery,critical,high,default,low
    
    $RestartCount++
    Write-Host ""
    Write-Host "Celery Worker durdu! (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
    Write-Host "   3 saniye sonra yeniden baslatilacak..." -ForegroundColor Yellow
}
