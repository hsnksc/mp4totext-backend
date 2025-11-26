# Test Together AI Custom Prompt with JWT Auth
$baseUri = "http://localhost:8002/api/v1"

Write-Host "🔐 Step 1: Login..." -ForegroundColor Cyan

# Login
$loginBody = @{
    username = "admin"
    password = "admin123"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUri/auth/login" -Method POST -Body $loginBody -ContentType "application/json"
    $token = $loginResponse.access_token
    Write-Host "✅ Login successful! Token: $($token.Substring(0, 20))..." -ForegroundColor Green
    
} catch {
    Write-Host "❌ Login failed!" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "`n🚀 Step 2: Test Custom Prompt API with Together AI..." -ForegroundColor Cyan

$transcriptionId = 92
$uri = "$baseUri/transcriptions/$transcriptionId/apply-custom-prompt"

# Form data
$boundary = [System.Guid]::NewGuid().ToString()
$headers = @{
    "Authorization" = "Bearer $token"
}

# Create multipart form data manually
$bodyLines = @(
    "--$boundary",
    'Content-Disposition: form-data; name="custom_prompt"',
    '',
    'Make this text more professional.',
    "--$boundary",
    'Content-Disposition: form-data; name="ai_provider"',
    '',
    'together',
    "--$boundary",
    'Content-Disposition: form-data; name="use_together"',
    '',
    'true',
    "--$boundary",
    'Content-Disposition: form-data; name="language"',
    '',
    'English',
    "--$boundary--"
)
$body = $bodyLines -join "`r`n"

try {
    $response = Invoke-RestMethod -Uri $uri -Method POST -Headers $headers -Body $body -ContentType "multipart/form-data; boundary=$boundary"
    
    Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Yellow
    $response | ConvertTo-Json -Depth 3
    
} catch {
    Write-Host "`n❌ ERROR!" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    
    # Try to read error response
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        $reader.Close()
        
        Write-Host "`nError Response Body:" -ForegroundColor Yellow
        Write-Host $errorBody
    }
    
    Write-Host "`nFull Exception:" -ForegroundColor Red
    Write-Host $_.Exception.Message
}
