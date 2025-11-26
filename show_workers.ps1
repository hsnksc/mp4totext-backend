<# 
.SYNOPSIS
    Show Celery worker processes
#>

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  Celery Worker Status" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# Get all Python processes with high memory (likely workers)
$workers = Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.WorkingSet64 -gt 100MB}

if ($workers.Count -eq 0) {
    Write-Host "No Celery workers found" -ForegroundColor Red
    exit 1
}

Write-Host "Found $($workers.Count) active workers:`n" -ForegroundColor Green

foreach ($worker in $workers) {
    # Get command line to extract worker name
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId=$($worker.Id)").CommandLine
    
    # Extract worker name
    $workerName = "Unknown"
    if ($cmdLine -match "-n (\w+@\S+)") {
        $workerName = $matches[1]
    }
    
    # Calculate uptime
    $uptime = (Get-Date) - $worker.StartTime
    $uptimeStr = "{0:00}h {1:00}m {2:00}s" -f $uptime.Hours, $uptime.Minutes, $uptime.Seconds
    
    # Calculate memory
    $memoryMB = [math]::Round($worker.WorkingSet64 / 1MB, 2)
    $cpuTime = [math]::Round($worker.CPU, 2)
    
    Write-Host "  Worker: $workerName" -ForegroundColor Cyan
    Write-Host "    PID:      $($worker.Id)" -ForegroundColor Gray
    Write-Host "    Memory:   $memoryMB MB" -ForegroundColor Gray
    Write-Host "    CPU Time: $cpuTime seconds" -ForegroundColor Gray
    Write-Host "    Uptime:   $uptimeStr" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Total Workers: $($workers.Count)" -ForegroundColor Green
Write-Host "Total Memory:  $([math]::Round(($workers | Measure-Object WorkingSet64 -Sum).Sum / 1MB, 2)) MB" -ForegroundColor Green
Write-Host "============================================`n" -ForegroundColor Cyan
