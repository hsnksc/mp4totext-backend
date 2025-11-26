# Frontend ve Backend Test Script
Write-Host "`n=== SERVIS DURUMU KONTROLU ===" -ForegroundColor Cyan

# Backend test
Write-Host "`n[1] Backend (Port 8000):" -ForegroundColor Yellow
try {
    $backend = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET -TimeoutSec 3 -UseBasicParsing
    if ($backend.StatusCode -eq 200) {
        Write-Host "    CALISIYOR - Status: 200" -ForegroundColor Green
        $content = $backend.Content | ConvertFrom-Json
        Write-Host "    Response: $($content.status)" -ForegroundColor Gray
    }
} catch {
    Write-Host "    CEVAP VERMIYOR!" -ForegroundColor Red
}

# Frontend test
Write-Host "`n[2] Frontend (Port 5173):" -ForegroundColor Yellow
try {
    $frontend = Invoke-WebRequest -Uri "http://localhost:5173" -Method GET -TimeoutSec 3 -UseBasicParsing
    if ($frontend.StatusCode -eq 200) {
        Write-Host "    CALISIYOR - Status: 200" -ForegroundColor Green
        if ($frontend.Content -like "*<!doctype*") {
            Write-Host "    HTML sayfasi yuklu" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "    CEVAP VERMIYOR!" -ForegroundColor Red
}

# CORS test
Write-Host "`n[3] CORS Test (Backend -> Frontend 5173):" -ForegroundColor Yellow
try {
    $headers = @{
        "Origin" = "http://localhost:5173"
    }
    $cors = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/transcriptions/" -Method OPTIONS -Headers $headers -TimeoutSec 3 -UseBasicParsing
    
    $allowOrigin = $cors.Headers["Access-Control-Allow-Origin"]
    $allowCreds = $cors.Headers["Access-Control-Allow-Credentials"]
    
    if ($allowOrigin -eq "http://localhost:5173" -and $allowCreds -eq "true") {
        Write-Host "    CORS DOGRU YAPILANDIRILMIS!" -ForegroundColor Green
        Write-Host "    Allow-Origin: $allowOrigin" -ForegroundColor Gray
        Write-Host "    Allow-Credentials: $allowCreds" -ForegroundColor Gray
    } else {
        Write-Host "    CORS YANLIS!" -ForegroundColor Red
        Write-Host "    Allow-Origin: $allowOrigin" -ForegroundColor Yellow
    }
} catch {
    Write-Host "    CORS TEST BASARISIZ!" -ForegroundColor Red
}

# Port kontrolu
Write-Host "`n[4] Port Kullanimi:" -ForegroundColor Yellow
$port8000 = netstat -ano | Select-String ":8000" | Select-String "LISTENING"
$port5173 = netstat -ano | Select-String ":5173" | Select-String "LISTENING"

if ($port8000) {
    Write-Host "    Port 8000: KULLANIMDA" -ForegroundColor Green
} else {
    Write-Host "    Port 8000: BOS!" -ForegroundColor Red
}

if ($port5173) {
    Write-Host "    Port 5173: KULLANIMDA" -ForegroundColor Green
} else {
    Write-Host "    Port 5173: BOS!" -ForegroundColor Red
}

# Ozet
Write-Host "`n=== OZET ===" -ForegroundColor Cyan
if ($backend -and $frontend -and $allowOrigin -eq "http://localhost:5173") {
    Write-Host "TUM SERVISLER CALISIYOR - UPLOAD TESTI YAPABILIRSINIZ!" -ForegroundColor Green
    Write-Host "`nSonraki Adimlar:" -ForegroundColor Yellow
    Write-Host "1. Browser'da http://localhost:5173 ac" -ForegroundColor White
    Write-Host "2. Incognito window kullan (Ctrl + Shift + N)" -ForegroundColor White
    Write-Host "3. Login ol" -ForegroundColor White
    Write-Host "4. Upload sayfasina git" -ForegroundColor White
    Write-Host "5. Audio/video dosyasi yukle" -ForegroundColor White
} else {
    Write-Host "BAZI SERVISLER CALISMIYOR!" -ForegroundColor Red
    if (-not $backend) { Write-Host "  - Backend baslatilmamis" -ForegroundColor Yellow }
    if (-not $frontend) { Write-Host "  - Frontend baslatilmamis" -ForegroundColor Yellow }
    if ($allowOrigin -ne "http://localhost:5173") { Write-Host "  - CORS yanlis yapilandirilmis" -ForegroundColor Yellow }
}

Write-Host "`n"
