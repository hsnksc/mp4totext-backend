# ============================================
# Multi-Worker Celery Launcher for Windows
# Starts multiple solo workers for parallel processing
# ============================================

param(
    [int]$WorkerCount = 4
)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Multi-Worker Celery Launcher" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Workers to start: $WorkerCount" -ForegroundColor Yellow
Write-Host "Pool type: solo (Windows-optimized)" -ForegroundColor Yellow
Write-Host "Queues: celery, critical, high, default, low" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if already running
$existing = Get-Process -Name celery -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "WARNING: Celery processes already running!" -ForegroundColor Red
    Write-Host "Stopping existing workers..." -ForegroundColor Yellow
    Stop-Process -Name celery -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Activate virtual environment
$venvPath = Join-Path $scriptDir "venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "WARNING: Virtual environment not found at $venvPath" -ForegroundColor Red
}

# Add FFmpeg to PATH
$ffmpegPath = "C:\ffmpeg-7.1-essentials_build\bin"
if (Test-Path $ffmpegPath) {
    $env:PATH = $ffmpegPath + ";" + $env:PATH
    Write-Host "FFmpeg added to PATH" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting $WorkerCount workers..." -ForegroundColor Cyan
Write-Host ""

# Start workers in background jobs
$jobs = @()
for ($i = 1; $i -le $WorkerCount; $i++) {
    $workerName = "worker$i@%h"
    
    Write-Host "[$i/$WorkerCount] Starting worker: $workerName" -ForegroundColor Yellow
    
    # Start worker as background job
    $job = Start-Job -ScriptBlock {
        param($scriptDir, $workerName, $i)
        
        Set-Location $scriptDir
        
        # Activate venv in job
        $venvActivate = Join-Path $scriptDir "venv\Scripts\Activate.ps1"
        if (Test-Path $venvActivate) {
            & $venvActivate
        }
        
        # Add FFmpeg to PATH in job
        $ffmpegPath = "C:\ffmpeg-7.1-essentials_build\bin"
        if (Test-Path $ffmpegPath) {
            $env:PATH = $ffmpegPath + ";" + $env:PATH
        }
        
        # Run celery worker
        python -m celery -A app.celery_config worker `
            --loglevel=info `
            --pool=solo `
            --concurrency=1 `
            -Q celery,critical,high,default,low `
            -n $workerName
            
    } -ArgumentList $scriptDir, $workerName, $i
    
    $jobs += $job
    Start-Sleep -Milliseconds 500  # Stagger startup
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "All $WorkerCount workers started!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Job IDs:" -ForegroundColor Yellow
$jobs | ForEach-Object { Write-Host "  - $($_.Id): $($_.Name)" -ForegroundColor Gray }
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  Check status  : Get-Job" -ForegroundColor Gray
Write-Host "  View output   : Receive-Job -Id <ID> -Keep" -ForegroundColor Gray
Write-Host "  Stop all      : Get-Job | Stop-Job; Get-Job | Remove-Job" -ForegroundColor Gray
Write-Host "  Stop workers  : Stop-Process -Name celery -Force" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop monitoring (workers continue in background)" -ForegroundColor Cyan
Write-Host ""

# Monitor jobs
try {
    while ($true) {
        Start-Sleep -Seconds 5
        
        # Check job status
        $runningJobs = Get-Job | Where-Object { $_.State -eq 'Running' }
        $failedJobs = Get-Job | Where-Object { $_.State -eq 'Failed' }
        
        if ($failedJobs) {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] WARNING: $($failedJobs.Count) worker(s) failed!" -ForegroundColor Red
            $failedJobs | ForEach-Object {
                Write-Host "  Failed Job $($_.Id):" -ForegroundColor Red
                Receive-Job -Id $_.Id | Select-Object -Last 10
            }
        }
        
        if ($runningJobs.Count -eq 0) {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] All workers stopped!" -ForegroundColor Red
            break
        }
    }
} catch {
    Write-Host ""
    Write-Host "Monitoring stopped. Workers continue running in background." -ForegroundColor Yellow
    Write-Host "Use 'Stop-Process -Name celery -Force' to stop all workers." -ForegroundColor Yellow
}
