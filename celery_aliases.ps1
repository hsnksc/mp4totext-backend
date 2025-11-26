# Celery Worker Management Aliases
# Add this to your PowerShell profile for quick access

# Show worker status
function Show-CeleryWorkers {
    & "$PSScriptRoot\show_workers.ps1"
}
Set-Alias -Name workers -Value Show-CeleryWorkers

# Quick commands
Write-Host "`nCelery Worker Aliases Loaded:" -ForegroundColor Green
Write-Host "  workers          - Show all running Celery workers" -ForegroundColor Cyan
Write-Host "`nOr use directly:" -ForegroundColor Yellow
Write-Host "  Get-Process python | Where-Object {`$_.WorkingSet64 -gt 100MB}" -ForegroundColor Gray
Write-Host ""
