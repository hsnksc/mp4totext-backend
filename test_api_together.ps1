# Test Together AI Custom Prompt via API
$transcriptionId = 92
$uri = "http://localhost:8002/api/v1/transcriptions/$transcriptionId/apply-custom-prompt"

# Form data
$form = @{
    custom_prompt = "Make this text more professional."
    ai_provider = "together"
    ai_model = $null
    use_together = "True"
    language = "English"
}

Write-Host "🚀 Testing Custom Prompt API with Together AI..." -ForegroundColor Cyan
Write-Host "URI: $uri"
Write-Host "Form Data:" -ForegroundColor Yellow
$form | Format-Table

try {
    $response = Invoke-WebRequest -Uri $uri -Method POST -Body $form -UseBasicParsing -TimeoutSec 30
    
    Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
    Write-Host "Status Code: $($response.StatusCode)"
    Write-Host "Content Length: $($response.Content.Length)"
    Write-Host "`nResponse (first 500 chars):"
    Write-Host $response.Content.Substring(0, [Math]::Min(500, $response.Content.Length))
    
} catch {
    Write-Host "`n❌ ERROR!" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Status Description: $($_.Exception.Response.StatusDescription)"
    
    # Try to read error response
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        $reader.Close()
        
        Write-Host "`nError Response Body:"
        Write-Host $errorBody -ForegroundColor Yellow
    }
    
    Write-Host "`nFull Exception:"
    Write-Host $_.Exception.Message
}
