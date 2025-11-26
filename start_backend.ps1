# Start Backend Server Script
# Run this from mp4totext-backend directory

Write-Host "🚀 Starting MP4toText Backend..." -ForegroundColor Green
Set-Location $PSScriptRoot
Write-Host "Working Directory: $PSScriptRoot" -ForegroundColor Cyan

.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
