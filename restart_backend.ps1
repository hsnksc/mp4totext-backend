# KILL PORT 8000 AND RESTART BACKEND
Write-Host "`n=== KILLING BACKEND ON PORT 8000 ===" -ForegroundColor Red

# Method 1: Find by port and kill
$portInfo = netstat -ano | findstr ":8000" | findstr "LISTENING"
if ($portInfo) {
    Write-Host "Found process on port 8000:" -ForegroundColor Yellow
    Write-Host $portInfo
    
    # Extract PID (last column)
    $pid = ($portInfo -split '\s+')[-1]
    Write-Host "Killing PID: $pid" -ForegroundColor Yellow
    
    try {
        taskkill /F /PID $pid 2>&1 | Out-Null
        Write-Host "Process killed!" -ForegroundColor Green
    } catch {
        Write-Host "Failed to kill process" -ForegroundColor Red
    }
}

Start-Sleep -Seconds 2

# Verify port is free
$stillRunning = netstat -ano | findstr ":8000" | findstr "LISTENING"
if ($stillRunning) {
    Write-Host "`nWARNING: Port 8000 still in use!" -ForegroundColor Red
    Write-Host "You may need to restart your computer or manually close the process." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "`nPort 8000 is now FREE!" -ForegroundColor Green
}

# Start backend
Write-Host "`n=== STARTING BACKEND ===" -ForegroundColor Cyan
cd C:\Users\hasan\OneDrive\Desktop\mp4totext-backend

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

Write-Host "Starting uvicorn with request logging..." -ForegroundColor Yellow
Write-Host "Watch for these logs:" -ForegroundColor Cyan
Write-Host "  🔵 INCOMING: POST /api/v1/transcriptions/ ..." -ForegroundColor Cyan
Write-Host "  🟢 RESPONSE: POST /api/v1/transcriptions/ -> 201" -ForegroundColor Cyan
Write-Host "`n"

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
