# ============================================
# Fast Multi-Worker Celery Launcher
# Starts workers as separate processes (not jobs)
# ============================================

param(
    [int]$WorkerCount = 4
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Fast Multi-Worker Celery" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Workers: $WorkerCount solo processes" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Stop existing workers
Stop-Process -Name celery -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Get script directory
$scriptDir = $PSScriptRoot
Set-Location $scriptDir

# Setup environment
$venvPython = Join-Path $scriptDir "venv\Scripts\python.exe"
$ffmpegPath = "C:\ffmpeg-7.1-essentials_build\bin"
$env:PATH = $ffmpegPath + ";" + $env:PATH

Write-Host "Starting $WorkerCount workers..." -ForegroundColor Yellow
Write-Host ""

# Start each worker as separate process
for ($i = 1; $i -le $WorkerCount; $i++) {
    $workerName = "worker$i"
    
    Write-Host "[$i/$WorkerCount] Launching: $workerName" -ForegroundColor Cyan
    
    # Start worker process (detached)
    $processArgs = @(
        "-m", "celery",
        "-A", "app.celery_config",
        "worker",
        "--loglevel=info",
        "--pool=solo",
        "--concurrency=1",
        "-Q", "celery,critical,high,default,low",
        "-n", "$workerName@%h"
    )
    
    Start-Process -FilePath $venvPython `
                  -ArgumentList $processArgs `
                  -WorkingDirectory $scriptDir `
                  -WindowStyle Minimized
    
    Start-Sleep -Milliseconds 800  # Stagger startup
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "All $WorkerCount workers launched!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Workers running in background (minimized windows)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  Check workers : Get-Process -Name celery" -ForegroundColor Gray
Write-Host "  Stop all      : Stop-Process -Name celery -Force" -ForegroundColor Gray
Write-Host "  View logs     : Check terminal windows or use Flower (port 5555)" -ForegroundColor Gray
Write-Host ""

# Wait a moment for workers to start
Start-Sleep -Seconds 3

# Show running workers
$workers = Get-Process -Name celery -ErrorAction SilentlyContinue
if ($workers) {
    Write-Host "Running workers:" -ForegroundColor Green
    $workers | ForEach-Object {
        $memoryMB = [math]::Round($_.WorkingSet64 / 1MB, 2)
        Write-Host "  PID $($_.Id) - Memory: ${memoryMB}MB" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Total: $($workers.Count) worker(s) active" -ForegroundColor Green
} else {
    Write-Host "WARNING: No workers detected!" -ForegroundColor Red
}
