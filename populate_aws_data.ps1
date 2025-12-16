# Populate Sample Data to AWS RDS via API
# This script sends sample products to the deployed AWS API

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Populate AWS RDS Database via API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get the ALB URL
$albUrl = aws elbv2 describe-load-balancers --names inventory-ai-alb --query 'LoadBalancers[0].DNSName' --output text

if ($LASTEXITCODE -ne 0 -or -not $albUrl) {
    Write-Host "❌ Failed to get ALB URL" -ForegroundColor Red
    exit 1
}

$apiUrl = "http://$albUrl"
Write-Host "📡 API URL: $apiUrl" -ForegroundColor Yellow
Write-Host ""

# Set environment variable for the Python script
$env:API_URL = $apiUrl

# Ensure .env file has Auth0 credentials
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  Warning: .env file not found. The script will attempt to run without authentication." -ForegroundColor Yellow
    Write-Host "   If your API requires authentication, create a .env file with your Auth0 credentials." -ForegroundColor Yellow
    Write-Host ""
}

# Run the population script
Write-Host "🌱 Starting data population..." -ForegroundColor Green
python populate_sample_data.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Sample data successfully populated to AWS RDS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now test the API:" -ForegroundColor Cyan
    Write-Host "  GET $apiUrl/products" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Failed to populate data. Check the errors above." -ForegroundColor Red
    exit 1
}
