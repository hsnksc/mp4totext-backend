# Start ngrok tunnel for MinIO
# This makes MinIO accessible from RunPod servers

Write-Host "🌐 Starting ngrok tunnel for MinIO on port 9000..." -ForegroundColor Cyan

# Check if ngrok is installed
$ngrokPath = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrokPath) {
    Write-Host "❌ ngrok not found in PATH" -ForegroundColor Red
    Write-Host "📥 Please install ngrok:" -ForegroundColor Yellow
    Write-Host "   1. Download from https://ngrok.com/download" -ForegroundColor Yellow
    Write-Host "   2. Extract to C:\ngrok\" -ForegroundColor Yellow
    Write-Host "   3. Run: ngrok config add-authtoken <YOUR_TOKEN>" -ForegroundColor Yellow
    Write-Host "   4. Add C:\ngrok\ to PATH or use full path" -ForegroundColor Yellow
    exit 1
}

# Check if MinIO is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -Method GET -TimeoutSec 2
    Write-Host "✅ MinIO is running on port 9000" -ForegroundColor Green
} catch {
    Write-Host "❌ MinIO is not running on port 9000" -ForegroundColor Red
    Write-Host "   Start MinIO first: docker start minio (or your MinIO service)" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "🚀 Starting ngrok tunnel..." -ForegroundColor Cyan
Write-Host "⚠️  Keep this window open while transcribing!" -ForegroundColor Yellow
Write-Host "⚠️  Copy the public URL and update storage_service.py" -ForegroundColor Yellow
Write-Host ""

# Start ngrok (http because MinIO on localhost is not using HTTPS)
# Free tier: 1 tunnel, random URL each time
ngrok http 9000

# Note: When ngrok starts, you'll see output like:
# Forwarding  https://xxxx-xx-xx-xx-xx.ngrok-free.app -> http://localhost:9000
# 
# Copy that URL (e.g., https://1234-5678-90ab-cdef.ngrok-free.app)
# and update storage.py to use it instead of localhost:9000
