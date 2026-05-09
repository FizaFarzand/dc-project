# Quick Verification Script for Async Payment Processing
# Run this after: docker compose up --build

Write-Host "================================" -ForegroundColor Cyan
Write-Host "E-Commerce Async Verification" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Function to wait for service
function Wait-ForService {
    param(
        [string]$Url,
        [string]$ServiceName,
        [int]$MaxAttempts = 30
    )
    
    Write-Host "Checking $ServiceName..." -ForegroundColor Yellow
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -ErrorAction Stop
            Write-Host "✓ $ServiceName is ready" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Host "  [$i/$MaxAttempts] Waiting for $ServiceName..." -ForegroundColor Gray
            Start-Sleep -Seconds 1
        }
    }
    Write-Host "✗ $ServiceName did not start" -ForegroundColor Red
    return $false
}

# Wait for services to be ready
Write-Host ""
Write-Host "Step 1: Waiting for services to start..." -ForegroundColor Yellow
Write-Host ""

$services = @{
    "API Gateway" = "http://localhost:8000/health"
    "Order Service" = "http://localhost:8003/health"
    "Payment Service" = "http://localhost:8004/health"
    "RabbitMQ" = "http://localhost:15672/"
}

$allReady = $true
foreach ($service in $services.Keys) {
    if (-not (Wait-ForService -Url $services[$service] -ServiceName $service)) {
        $allReady = $false
    }
}

if (-not $allReady) {
    Write-Host ""
    Write-Host "ERROR: Not all services are ready!" -ForegroundColor Red
    Write-Host "Make sure: docker compose up --build" -ForegroundColor Yellow
    exit 1
}

# Test 1: Register a user
Write-Host ""
Write-Host "Step 2: Creating test user..." -ForegroundColor Yellow

$username = "testuser_$(Get-Random)"
$email = "test$(Get-Random)@example.com"

$userBody = @{
    username = $username
    email = $email
    password = "password123"
} | ConvertTo-Json

try {
    $userResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/users/register" `
        -Method POST `
        -ContentType "application/json" `
        -Body $userBody
    
    $userData = $userResponse.Content | ConvertFrom-Json
    $userId = $userData.id
    
    Write-Host "✓ User created: ID=$userId, Email=$email" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create user: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Create an order (will trigger async payment)
Write-Host ""
Write-Host "Step 3: Creating order (triggers async payment)..." -ForegroundColor Yellow

$orderBody = @{
    user_id = $userId
    product_id = "prod_001"
    quantity = 2
} | ConvertTo-Json

try {
    $orderResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/orders" `
        -Method POST `
        -ContentType "application/json" `
        -Body $orderBody
    
    $orderData = $orderResponse.Content | ConvertFrom-Json
    $orderId = $orderData.id
    $initialStatus = $orderData.status
    
    Write-Host "✓ Order created: ID=$orderId" -ForegroundColor Green
    Write-Host "  Initial status: $initialStatus" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Failed to create order: $_" -ForegroundColor Red
    exit 1
}

# Test 3: Wait for async processing
Write-Host ""
Write-Host "Step 4: Waiting for async payment processing..." -ForegroundColor Yellow

$startTime = Get-Date
$timeout = 10  # seconds
$statusUpdated = $false

for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 0.5
    
    try {
        $checkResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/orders?user_id=$userId" `
            -Method GET -TimeoutSec 5
        
        $orders = $checkResponse.Content | ConvertFrom-Json
        $currentStatus = $orders[0].status
        $transactionId = $orders[0].transaction_id
        
        if ($currentStatus -ne $initialStatus) {
            $statusUpdated = $true
            break
        }
        
        Write-Host "  [$i/20] Status: $currentStatus (waiting...)" -ForegroundColor Gray
    } catch {
        # Retry on error
        Write-Host "  [$i/20] Checking status... (retry)" -ForegroundColor Gray
    }
}

Write-Host ""
if ($statusUpdated) {
    Write-Host "✓ Payment processed asynchronously!" -ForegroundColor Green
    Write-Host "  Final status: $currentStatus" -ForegroundColor Cyan
    Write-Host "  Transaction ID: $transactionId" -ForegroundColor Cyan
} else {
    Write-Host "✗ Order status did not update (payment processing timed out)" -ForegroundColor Red
    Write-Host "  Check logs: docker logs payment-service" -ForegroundColor Yellow
}

# Test 4: Verify RabbitMQ queue
Write-Host ""
Write-Host "Step 5: Checking RabbitMQ queue..." -ForegroundColor Yellow

try {
    $queueResponse = Invoke-WebRequest -Uri "http://localhost:15672/api/queues/%2F/payment_queue" `
        -Headers @{Authorization = "Basic $(([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes('guest:guest')))))"} `
        -TimeoutSec 5
    
    $queueData = $queueResponse.Content | ConvertFrom-Json
    $readyMessages = $queueData.messages_ready
    $totalMessages = $queueData.messages
    
    Write-Host "✓ RabbitMQ queue status:" -ForegroundColor Green
    Write-Host "  Ready messages: $readyMessages" -ForegroundColor Cyan
    Write-Host "  Total messages: $totalMessages" -ForegroundColor Cyan
} catch {
    Write-Host "⚠ Could not access RabbitMQ API (but queue may still exist)" -ForegroundColor Yellow
    Write-Host "  Check manually: http://localhost:15672 (guest/guest)" -ForegroundColor Yellow
}

# Test 5: Check Payment Service logs
Write-Host ""
Write-Host "Step 6: Checking Payment Service logs..." -ForegroundColor Yellow

try {
    $logs = & docker logs payment-service 2>&1 | Select-String "Processing payment" -Last 1
    
    if ($logs) {
        Write-Host "✓ Found payment processing in logs:" -ForegroundColor Green
        Write-Host "  $logs" -ForegroundColor Cyan
    } else {
        Write-Host "⚠ No payment processing logs found yet" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not access Docker logs" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Verification Complete!" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

if ($statusUpdated) {
    Write-Host "✅ ASYNC COMMUNICATION WORKING!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Key observations:" -ForegroundColor Cyan
    Write-Host "1. Order created and returned quickly" -ForegroundColor White
    Write-Host "2. Status automatically updated to '$currentStatus' after processing" -ForegroundColor White
    Write-Host "3. Payment service processed asynchronously in background" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "- Run load tests: .\run-load-tests.cmd" -ForegroundColor White
    Write-Host "- Monitor RabbitMQ: http://localhost:15672" -ForegroundColor White
    Write-Host "- Read: TESTING.md for detailed procedures" -ForegroundColor White
} else {
    Write-Host "❌ VERIFICATION FAILED!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "1. Check docker containers: docker ps" -ForegroundColor White
    Write-Host "2. Check RabbitMQ logs: docker logs message-queue" -ForegroundColor White
    Write-Host "3. Check Payment Service logs: docker logs payment-service" -ForegroundColor White
    Write-Host "4. Restart services: docker compose down && docker compose up --build" -ForegroundColor White
}

Write-Host ""
