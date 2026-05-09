# 🚀 Postman Collection Setup & Testing Guide

## Quick Setup

### 1️⃣ **Import Collection**
- Open Postman
- Click **Import** (top left)
- Select **postman-collection.json** from your project folder
- Collection will appear with all endpoints organized

### 2️⃣ **Environment Variables Already Set**
The collection has these variables built-in (no external environment file needed):
- `{{baseUrl}}` = `http://localhost:8000` ✅
- `{{user_id}}` = Auto-saved from registration
- `{{product_id}}` = Auto-saved from products list
- `{{order_id}}` = Auto-saved from order creation

---

## 📋 Complete Testing Flow

### **Phase 1: User & Product Setup** (1 minute)

#### Request 1: Register User
```
POST {{baseUrl}}/users/register
Body (JSON):
{
  "email": "testuser@example.com",
  "password": "password123",
  "name": "Test User"
}
```
✅ **Expected:** Status 200-201, `user_id` saved automatically

---

#### Request 2: List Products
```
GET {{baseUrl}}/products
```
✅ **Expected:** Status 200, array of products, `product_id` saved automatically

---

### **Phase 2: ASYNC Payment Flow Test** (5 minutes) ⭐ KEY TEST

#### Request 3: Create Order
```
POST {{baseUrl}}/orders
Body (JSON):
{
  "user_id": "{{user_id}}",
  "product_id": "{{product_id}}",
  "quantity": 2
}
```

**OBSERVE:**
- ✅ Response comes **FAST** (~80-100ms) 🚀
- ✅ Status: `"pending_payment"` (not immediately paid like sync would be)
- ✅ No `transaction_id` yet (payment processing in background)
- ✅ `order_id` saved automatically

**What's happening?**
- Order Service publishes to RabbitMQ immediately ✅
- Returns response without waiting for payment ✅
- Payment Service consumes message from queue in background 🔄

---

#### Request 4: Check Order Status IMMEDIATELY
```
GET {{baseUrl}}/orders?user_id={{user_id}}
```

**OBSERVE:**
- Status is still `"pending_payment"`
- `transaction_id` is `null`
- This is normal! Payment is being processed asynchronously 🔄

---

#### ⏳ **WAIT 3 SECONDS**
Go grab coffee ☕ while RabbitMQ processes the payment...

---

#### Request 5: Check Order Status AFTER 3 Seconds
```
GET {{baseUrl}}/orders?user_id={{user_id}}
```

**OBSERVE - THIS PROVES ASYNC WORKS! 🎉**
- ✅ Status changed to `"paid"` or `"payment_success"`
- ✅ `transaction_id` is NOW populated (e.g., `"txn_abc123xyz"`)
- ✅ Order automatically updated by Payment Service!

**What happened?**
1. Payment Service consumed message from queue ✅
2. Processed payment asynchronously ✅
3. Updated order status back to `paid` ✅
4. **NO manual intervention needed** - it's async! 🤖

---

## 🧪 Execution Checklist

### Must-Run in Order:
- [ ] **1. Register User** → Saves `user_id`
- [ ] **2. List Products** → Saves `product_id`
- [ ] **3. Create Order** → Record response time, observe `pending_payment` status
- [ ] **4. Check Status (Immediate)** → Should be `pending_payment`, no transaction_id
- [ ] **5. Wait 3 seconds** → Let RabbitMQ process
- [ ] **6. Check Status (After Wait)** → Should be `paid` with transaction_id ✅

---

## 📊 What Each Test Verifies

| Test | What It Checks | Expected Result |
|------|---|---|
| Register User | User creation works | 200 status, user_id saved |
| List Products | Product catalog available | 200 status, array returned |
| Create Order | Order published to queue | `pending_payment` status, <200ms response |
| Check Status (Immediate) | Async not yet complete | Still `pending_payment` |
| Check Status (After Wait) | Async completed ✅ | `paid` status, transaction_id assigned |

---

## 🔍 Real-Time Monitoring (Optional)

While running Postman tests, monitor in terminal:

```bash
# Watch Payment Service processing messages
docker logs -f payment-service
```

You should see:
```
Processing payment for order_id=123, amount=599.99
✅ Payment successful
Updated order 123 status to: paid
```

---

## 🎯 Success Criteria - You Know It Works When:

✅ **Immediate Response:** Order creation returns in <200ms (proves async)  
✅ **Status Transition:** Status changes from `pending_payment` → `paid`  
✅ **Transaction ID:** Gets assigned after payment processes  
✅ **No Errors:** All responses are 200 status  
✅ **Docker Logs:** Payment service shows "Payment successful" messages  

---

## 💡 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| `baseUrl` says undefined | Collection already has it configured, just use it as `{{baseUrl}}` |
| "Connection refused" | Make sure `docker compose up` is running |
| Order status not changing | Wait 5 seconds instead of 3, check `docker logs payment-service` |
| "Cannot find payment_queue" | Docker containers are not connected to same RabbitMQ - restart: `docker compose down && docker compose up` |

---

## 📝 Notes

- **Variables persist:** When you run "Register User", the `user_id` is automatically extracted and saved
- **Same for product_id:** Running "List Products" extracts the first product ID
- **Same for order_id:** Running "Create Order" extracts and saves the order ID
- **No manual copy-paste needed:** All variables are chained through Tests scripts

---

## Next Steps

After successful testing:
1. Run load tests: `cd load-tests && locust -f locustfile.py --host=http://localhost:8000`
2. Check metrics in RabbitMQ dashboard: http://localhost:15672 (user: guest, pw: guest)
3. Review VIVA-CHECKLIST.md for interview preparation
