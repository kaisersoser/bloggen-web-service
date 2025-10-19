# staging-clean.ps1
# Clean up all staging Docker resources (containers, volumes, networks, images)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleaning Staging Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "WARNING: This will remove all staging containers, volumes, and cached data!" -ForegroundColor Yellow
Write-Host ""
$confirmation = Read-Host "Are you sure you want to continue? (yes/no)"

if ($confirmation -ne "yes") {
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Cleaning up staging resources..." -ForegroundColor Yellow
Write-Host ""

# Stop and remove containers, networks, and volumes
Write-Host "1. Stopping and removing containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.staging.yml down -v

# Remove staging images
Write-Host "2. Removing staging images..." -ForegroundColor Yellow
docker images --filter "reference=bloggen-*-staging" -q | ForEach-Object {
    if ($_) {
        docker rmi -f $_
    }
}

# Prune unused Docker resources
Write-Host "3. Pruning unused Docker resources..." -ForegroundColor Yellow
docker system prune -f

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ Staging Environment Cleaned!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "All staging Docker resources removed." -ForegroundColor White
    Write-Host ""
    Write-Host "To restart staging: .\scripts\staging-start.ps1" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to clean staging environment" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Red
    exit 1
}
