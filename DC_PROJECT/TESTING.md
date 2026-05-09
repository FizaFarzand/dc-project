# Testing Guide - RabbitMQ Async Communication & Load Testing

## Part 1: Verify RabbitMQ Async Communication

### 1. Start the System
```bash
docker compose up --build
```

Wait for all services to be ready (check logs for "Payment consumer started").

### 2. Verify RabbitMQ is Running
- Management UI: http://localhost:15672
- Login: `guest` / `guest`
- Check: Queues section should show `payment_queue`

### 3. Create a Test Order to Verify Async Flow

**Open Terminal and run:**
```bash
# Set variables
$GATEWAY_URL = "http://localhost:8000"

# 1. Register a user
$registerBody = @{
    username = "testuser_$(Get-Random)"
    email = "test$(Get-Random)@example.com"
    password = "password123"
} | ConvertTo-Json

$userResponse = Invoke-WebRequest -Uri "$GATEWAY_URL/api/users/register" `
  -Method POST -ContentType "application/json" -Body $registerBody
  
$userId = ($userResponse.Content | ConvertFrom-Json).id
Write-Host "Created user: $userId"

# 2. Create an order (will be sent to RabbitMQ)
$orderBody = @{
    user_id = $userId
    product_id = "prod_001"
    quantity = 2
} | ConvertTo-Json

$orderResponse = Invoke-WebRequest -Uri "$GATEWAY_URL/api/orders" `
  -Method POST -ContentType "application/json" -Body $orderBody

$orderId = ($orderResponse.Content | ConvertFrom-Json).id
$orderStatus = ($orderResponse.Content | ConvertFrom-Json).status

Write-Host "Created order: $orderId with status: $orderStatus"

# 3. Wait 2-3 seconds for async processing
Start-Sleep -Seconds 3

# 4. Check order status (should be 'paid' or 'payment_failed')
$finalResponse = Invoke-WebRequest -Uri "$GATEWAY_URL/api/orders?user_id=$userId" -Method GET
$orders = $finalResponse.Content | ConvertFrom-Json
Write-Host "Final order status: $($orders[0].status)"
```

**Expected Results:**
- Initial order status: `pending_payment` (order created but payment not processed yet)
- After 2-3 seconds: `paid` or `payment_failed` (async payment processed)

### 4. Verify in Docker Logs

**Option A: Check Order Service logs**
```bash
docker logs order-service
```
Look for: "Publish payment request to RabbitMQ"

**Option B: Check Payment Service logs**
```bash
docker logs payment-service
```
Look for:
- "Payment consumer started, waiting for messages..."
- "Processing payment for order X, amount: Y"
- "Updated order X status to paid/payment_failed"

### 5. Monitor RabbitMQ Queue
1. Go to http://localhost:15672
2. Navigate to **Queues** → **payment_queue**
3. You should see:
   - Ready messages: 0 (all processed)
   - Unacked messages: 0 (successfully delivered)

---

## Part 2: Load Testing with Locust

### 1. Install Locust
```bash
cd load-tests
pip install -r requirements.txt
```

### 2. Run Load Test (GUI Mode - EASY)
```bash
cd load-tests
locust -f locustfile.py --host=http://localhost:8000
```

Open browser: http://localhost:8089

**Configuration:**
- Number of users: `50` (start small)
- Spawn rate: `5` users/second
- Click "Start swarming"

**Monitor:**
- Response times
- Request counts
- Failure rates
- Charts update in real-time

### 3. Run Headless Load Test (for Reports)
```bash
cd load-tests
locust -f locustfile.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless \
  --csv=results
```

**Output Files:**
- `results_stats.csv`: Request statistics
- `results_stats_history.csv`: Performance over time

### 4. Alternative: Simple Script Test
```bash
# Windows PowerShell - Simple concurrent requests
$parallelJobs = @()

for ($i = 1; $i -le 10; $i++) {
    $job = Start-Job -ScriptBlock {
        $startTime = Get-Date
        
        # Make 10 requests per job
        for ($j = 1; $j -le 10; $j++) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/api/products" `
                  -TimeoutSec 5
                Write-Output "Job $($args[0]) - Request $j: Success ($(($response.StatusCode)))"
            } catch {
                Write-Output "Job $($args[0]) - Request $j: Failed"
            }
        }
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        Write-Output "Job $($args[0]) - Completed in $duration seconds"
    } -ArgumentList $i
    
    $parallelJobs += $job
}

# Wait for all jobs to complete
$parallelJobs | Wait-Job

# Get results
$parallelJobs | Receive-Job

# Clean up
$parallelJobs | Remove-Job
```

---

## Part 3: Analyze Results

### Performance Metrics to Review:

1. **Response Times:**
   - List Products: Should be < 100ms
   - Create Order: 150-300ms (includes product update)
   - Create Order (async): Now still quick response, payment happens in background

2. **Expected Load Test Results:**

| Endpoint | Requests | Avg Response | P95 | P99 | Failures |
|----------|----------|--------------|-----|-----|----------|
| GET /api/products | 500 | 80ms | 150ms | 200ms | 0% |
| GET /api/products/[id] | 300 | 60ms | 120ms | 150ms | 0% |
| POST /api/orders | 200 | 200ms | 350ms | 400ms | 2-5% |
| GET /api/orders | 150 | 70ms | 140ms | 180ms | 0% |

3. **Async Benefit:**
   ```
   BEFORE (Synchronous):
   - Order creation blocks until payment completes (300-500ms)
   - Timeout issues if payment service is slow
   
   AFTER (Asynchronous):
   - Order creation returns immediately (50-100ms)
   - Payment processed in background
   - Better scalability under load
   ```

### Verify Async Improvements:

```bash
# Test order creation response time with async
# Should see significant improvement in response time

# Check payment throughput:
docker logs payment-service | grep "Processing payment"

# Count successful payments:
docker logs payment-service | grep "status to paid" | wc -l
```

---

## Part 4: Troubleshooting

### Issue: Order still shows "pending_payment"
**Solution:**
1. Check payment service logs: `docker logs payment-service`
2. Verify RabbitMQ is running: `docker ps | grep rabbitmq`
3. Check RabbitMQ queue: http://localhost:15672

### Issue: RabbitMQ connection refused
**Solution:**
```bash
# Restart RabbitMQ
docker restart message-queue

# Wait 10 seconds and check logs
docker logs message-queue
```

### Issue: High failure rate in load test
**Solution:**
1. Increase spawn rate gradually
2. Check database connection limits
3. Monitor CPU/Memory: `docker stats`
4. Reduce number of concurrent users

### Issue: Message queue backing up
**Solution:**
1. Check Payment Service: `docker logs payment-service`
2. Monitor CPU usage: `docker stats payment-service`
3. Consider scaling: Use multiple payment-service replicas

---

## Summary: What Changed?

✅ **Before:**
- Direct HTTP call: Order Service → Payment Service (synchronous)
- Blocking call (300-500ms wait)
- Tight coupling

✅ **After:**
- Async messaging: Order Service → RabbitMQ
- Payment Service consumes asynchronously
- Fast response (50-100ms)
- Decoupled, scalable architecture

This allows:
- Better performance under load
- Ability to process payments offline
- Scale payment processing independently
- Resilience to payment service failures
