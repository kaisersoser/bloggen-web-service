# staging-test.ps1
# Test the staging environment health and connectivity

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing Staging Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test backend health
Write-Host "Testing backend health..." -ForegroundColor Yellow
try {
    $backendResponse = Invoke-WebRequest -Uri "http://localhost:5000/health" -Method GET -TimeoutSec 10
    if ($backendResponse.StatusCode -eq 200) {
        Write-Host "✓ Backend health check passed" -ForegroundColor Green
        $backendHealthy = $true
    } else {
        Write-Host "✗ Backend health check failed (Status: $($backendResponse.StatusCode))" -ForegroundColor Red
        $backendHealthy = $false
    }
} catch {
    Write-Host "✗ Backend health check failed: $($_.Exception.Message)" -ForegroundColor Red
    $backendHealthy = $false
}
Write-Host ""

# Test frontend accessibility
Write-Host "Testing frontend accessibility..." -ForegroundColor Yellow
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method GET -TimeoutSec 10
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "✓ Frontend accessible" -ForegroundColor Green
        $frontendHealthy = $true
    } else {
        Write-Host "✗ Frontend not accessible (Status: $($frontendResponse.StatusCode))" -ForegroundColor Red
        $frontendHealthy = $false
    }
} catch {
    Write-Host "✗ Frontend not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $frontendHealthy = $false
}
Write-Host ""

# Check Docker container status
Write-Host "Checking Docker container status..." -ForegroundColor Yellow
$containers = docker ps --filter "name=bloggen-.*-staging" --format "table {{.Names}}\t{{.Status}}"
Write-Host $containers
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Results Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($backendHealthy -and $frontendHealthy) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Staging environment is ready for testing." -ForegroundColor White
    Write-Host ""
    Write-Host "URLs:" -ForegroundColor Cyan
    Write-Host "  - Backend:  http://localhost:5000" -ForegroundColor White
    Write-Host "  - Frontend: http://localhost:3000" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open http://localhost:3000 in your browser" -ForegroundColor White
    Write-Host "  2. Test blog generation workflow" -ForegroundColor White
    Write-Host "  3. Check logs: docker-compose -f docker-compose.staging.yml logs -f" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "✗ Some tests failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Cyan
    Write-Host "  1. Check logs: docker-compose -f docker-compose.staging.yml logs" -ForegroundColor White
    Write-Host "  2. Verify .env.staging files are configured correctly" -ForegroundColor White
    Write-Host "  3. Ensure all required services are running" -ForegroundColor White
    Write-Host "  4. Check Docker Desktop is running properly" -ForegroundColor White
    Write-Host ""
    exit 1
}
