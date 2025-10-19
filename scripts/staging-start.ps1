# staging-start.ps1
# Start the staging environment using Docker Compose

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Staging Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
$dockerRunning = docker info 2>&1 | Select-String "Server Version"
if (-not $dockerRunning) {
    Write-Host "ERROR: Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker is running" -ForegroundColor Green
Write-Host ""

# Check if .env.staging files exist
Write-Host "Checking environment files..." -ForegroundColor Yellow
$backendEnv = "backend\.env.staging"
$frontendEnv = "frontend-nextjs\blog-generator-ui\.env.staging"

if (-not (Test-Path $backendEnv)) {
    Write-Host "ERROR: Missing $backendEnv" -ForegroundColor Red
    Write-Host "Please create and configure the backend .env.staging file." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Backend .env.staging found" -ForegroundColor Green

if (-not (Test-Path $frontendEnv)) {
    Write-Host "ERROR: Missing $frontendEnv" -ForegroundColor Red
    Write-Host "Please create and configure the frontend .env.staging file." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Frontend .env.staging found" -ForegroundColor Green
Write-Host ""

# Start Docker Compose services
Write-Host "Starting Docker Compose services..." -ForegroundColor Yellow
docker-compose -f docker-compose.staging.yml up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ Staging Environment Started!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services:" -ForegroundColor Cyan
    Write-Host "  - Backend:  http://localhost:5000" -ForegroundColor White
    Write-Host "  - Frontend: http://localhost:3000" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run .\scripts\staging-test.ps1 to test the services" -ForegroundColor White
    Write-Host "  2. View logs: docker-compose -f docker-compose.staging.yml logs -f" -ForegroundColor White
    Write-Host "  3. Stop staging: .\scripts\staging-stop.ps1" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to start staging environment" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Red
    exit 1
}
