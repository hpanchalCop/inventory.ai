# Regenerate embeddings for all products by deleting and recreating them

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Regenerate ALL Product Embeddings" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$alb = "inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com"
$apiUrl = "http://$alb"

# Get Auth0 token
Write-Host "🔐 Getting Auth0 token..." -ForegroundColor Yellow
$token = & .venv\Scripts\python.exe get_token.py

if (-not $token) {
    Write-Host "❌ Failed to get Auth0 token" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Token obtained`n" -ForegroundColor Green

# Set up headers
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# Fetch all products
Write-Host "📦 Fetching all products..." -ForegroundColor Yellow
try {
    $products = Invoke-RestMethod -Uri "$apiUrl/products?limit=1000" -Headers $headers
    Write-Host "✅ Found $($products.Count) products`n" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to fetch products: $_" -ForegroundColor Red
    exit 1
}

if ($products.Count -eq 0) {
    Write-Host "No products to regenerate" -ForegroundColor Yellow
    exit 0
}

# Delete all products
Write-Host "🗑️  Deleting existing products..." -ForegroundColor Yellow
$deleteCount = 0
foreach ($product in $products) {
    try {
        Invoke-RestMethod -Uri "$apiUrl/products/$($product.id)" -Method DELETE -Headers $headers | Out-Null
        Write-Host "  ✓ Deleted: $($product.name)" -ForegroundColor Gray
        $deleteCount++
    } catch {
        Write-Host "  ✗ Failed to delete $($product.id): $_" -ForegroundColor Red
    }
}

Write-Host "✅ Deleted $deleteCount products`n" -ForegroundColor Green

# Recreate all products with embeddings
Write-Host "🌱 Recreating products with embeddings..." -ForegroundColor Yellow
$createCount = 0
foreach ($product in $products) {
    try {
        $body = @{
            name = $product.name
            description = $product.description
            category = $product.category
            price = $product.price
        } | ConvertTo-Json
        
        $newProduct = Invoke-RestMethod -Uri "$apiUrl/products/text-only" -Method POST -Headers $headers -Body $body
        Write-Host "  ✓ Created with embeddings: $($newProduct.name)" -ForegroundColor Gray
        $createCount++
    } catch {
        Write-Host "  ✗ Failed to create $($product.name): $_" -ForegroundColor Red
    }
}

Write-Host "`n✅ Successfully recreated $createCount/$($products.Count) products with embeddings!`n" -ForegroundColor Green

# Test search
Write-Host "🔍 Testing search functionality..." -ForegroundColor Yellow
try {
    $searchBody = @{
        query = "wheelchair"
        top_k = 5
    } | ConvertTo-Json
    
    $results = Invoke-RestMethod -Uri "$apiUrl/search/text" -Method POST -Headers $headers -Body $searchBody
    Write-Host "✅ Search returned $($results.Count) results" -ForegroundColor Green
    
    if ($results.Count -gt 0) {
        Write-Host "`nTop results:" -ForegroundColor Cyan
        $results | Select-Object -First 3 | ForEach-Object {
            Write-Host "  - $($_.product.name) (score: $([math]::Round($_.similarity_score, 3)))" -ForegroundColor White
        }
    }
} catch {
    Write-Host "❌ Search test failed: $_" -ForegroundColor Red
}

Write-Host "`n✅ Embedding regeneration complete!`n" -ForegroundColor Green
