# 📊 Celery Worker Monitor
# Her 10 saniyede bir worker durumunu kontrol eder

Write-Host "📊 Celery Worker Monitor - Starting..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Yellow
Write-Host ""

while ($true) {
    Clear-Host
    Write-Host "📊 Celery Worker Status" -ForegroundColor Cyan
    Write-Host "Time: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Celery worker process'ini bul
    $celeryProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*celery*worker*"
    }
    
    if ($celeryProcess) {
        Write-Host "✅ Celery Worker: RUNNING" -ForegroundColor Green
        Write-Host "   PID: $($celeryProcess.Id)" -ForegroundColor White
        Write-Host "   CPU: $([math]::Round($celeryProcess.CPU, 2))%" -ForegroundColor White
        Write-Host "   Memory: $([math]::Round($celeryProcess.WorkingSet64 / 1MB, 2)) MB" -ForegroundColor White
        Write-Host "   Started: $($celeryProcess.StartTime)" -ForegroundColor White
        
        # Memory warning
        $memoryMB = [math]::Round($celeryProcess.WorkingSet64 / 1MB, 2)
        if ($memoryMB -gt 3000) {
            Write-Host "   ⚠️ WARNING: High memory usage!" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Celery Worker: NOT RUNNING" -ForegroundColor Red
        Write-Host "   Suggestion: Run start_celery.bat" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host "Next check in 10 seconds..." -ForegroundColor Gray
    
    Start-Sleep -Seconds 10
}
