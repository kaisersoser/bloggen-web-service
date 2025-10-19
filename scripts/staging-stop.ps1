# staging-stop.ps1
# Stop the staging environment and remove containers

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stopping Staging Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop Docker Compose services
Write-Host "Stopping Docker Compose services..." -ForegroundColor Yellow
docker-compose -f docker-compose.staging.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ Staging Environment Stopped!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Containers removed. Data volumes preserved." -ForegroundColor White
    Write-Host ""
    Write-Host "To restart: .\scripts\staging-start.ps1" -ForegroundColor Cyan
    Write-Host "To clean all data: .\scripts\staging-clean.ps1" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to stop staging environment" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Red
    exit 1
}
