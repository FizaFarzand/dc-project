# 🚀 Complete Postman Testing Guide - DC Project

## 📦 What's Included

✅ **postman-collection.json** - Complete collection with all tests
✅ **POSTMAN-GUIDE.md** - This comprehensive guide
✅ **ASYNC-FLOW-DIAGRAM.txt** - Visual testing flow

---

## ⚡ Quick Start (3 minutes)

### 1️⃣ Import Collection
- Open Postman → **Import** → Select `postman-collection.json`
- Base URL automatically set to `http://localhost:8000`

### 2️⃣ Run Basic Async Test
- **Register User** → **List Products** → **Create Order**
- **Check Status (Immediate)** → Wait 3 sec → **Check Status (After)**
- ✅ Order status changes from `pending_payment` → `paid`

### 3️⃣ Run Comprehensive Tests
- **STEP 5: Core APIs Testing** - All endpoints for users/admins
- **STEP 6: Final Demo Flow** - Complete teacher demonstration

---

## 📋 Testing Sections Overview

### **1. User Management** (Basic)
- Register User, Login User

### **2. Product Catalog** (Basic)
- List Products, Get Product Details

### **3. Order Management - ASYNC FLOW TEST** ⭐
- Create Order (fast response)
- Check Status transitions

### **5. STEP 5: Core APIs Testing** 🔧
Complete testing of all service endpoints:

#### **User Service APIs:**
- `POST /users/register` - Customer & Admin registration
- `POST /users/login` - Authentication for both roles
- `GET /users/me` - Customer profile
- `GET /users` - Admin: list all users

#### **Product Service APIs:**
- `GET /products` - List all products
- `GET /products/search` - Search functionality
- `GET /products/{id}` - Product details
- `POST /products` - Admin: create product
- `PUT /products/{id}` - Admin: update product
- `DELETE /products/{id}` - Admin: delete product

#### **Order Service APIs:**
- `POST /orders` - Create order (async)
- `GET /orders` - List orders

#### **Payment Service APIs:**
- `POST /payments/simulate` - Direct payment simulation

### **6. STEP 6: Final Demo Flow (Teacher Test)** 🎯
**Complete end-to-end demonstration** that proves the entire system:

1. **Register Customer** → Creates demo customer
2. **Register Admin** → Creates demo admin
3. **Admin Login** → Authenticates admin
4. **Admin Creates Product** → Adds product to catalog
5. **Customer Login** → Authenticates customer
6. **Customer Views Products** → Browses catalog
7. **Customer Creates Order** → ASYNC order placement
8. **Check Status (Before)** → Shows `pending_payment`
9. **WAIT 5 Seconds** → RabbitMQ processing
10. **Check Status (After)** → Shows `paid` with transaction_id
11. **Admin Views All Orders** → System-wide order visibility
12. **Admin Views All Users** → System-wide user management

---

## 🎭 User Roles & Permissions

### **Customer User:**
✅ Register/Login
✅ View products (all)
✅ Search products
✅ Get product details
✅ Create orders
✅ View own orders
❌ Cannot manage products
❌ Cannot view all users/orders

### **Admin User:**
✅ All customer permissions
✅ Create/Update/Delete products
✅ View all users
✅ View all orders
✅ Full system management

---

## 🔄 Async Flow Demonstration

### **What Makes It Async:**
1. **Order Creation:** Returns immediately (~100ms) with `pending_payment`
2. **RabbitMQ Processing:** Payment happens in background
3. **Status Update:** Order automatically updates to `paid`
4. **No Blocking:** User gets instant response

### **Proof of Async Working:**
```
BEFORE: Order creation → Direct HTTP call → Wait 500ms → Return paid
AFTER:  Order creation → RabbitMQ publish → Return immediately → Async payment → Auto-update
```

---

## 📊 Test Results & Validation

### **Automatic Tests Included:**
- ✅ Status code validation (200, 201)
- ✅ Response time monitoring (<200ms for async)
- ✅ Status transitions (`pending_payment` → `paid`)
- ✅ Authentication requirements
- ✅ Role-based access control
- ✅ Data structure validation

### **Manual Verification:**
- Check Docker logs for RabbitMQ messages
- Monitor RabbitMQ Management UI
- Verify transaction IDs are assigned
- Confirm admin operations require admin tokens

---

## 🔍 Monitoring Commands

### **Terminal Monitoring:**
```bash
# Watch payment processing
docker logs -f payment-service

# Check RabbitMQ connections
docker logs -f message-queue

# Monitor all services
docker compose logs -f
```

### **RabbitMQ Dashboard:**
- URL: http://localhost:15672
- User: guest / Password: guest
- Check: Queues → payment_queue → Messages

---

## 💡 Troubleshooting Guide

| Problem | Solution |
|---------|----------|
| 404 Not Found | Endpoints don't use `/api/` prefix |
| 401 Unauthorized | Check Authorization header has Bearer token |
| 403 Forbidden | Admin endpoints need admin token |
| Order not updating | Wait 5+ seconds for RabbitMQ processing |
| No products available | Run admin product creation first |
| Connection refused | Ensure `docker compose up` is running |

---

## 📝 Variable Management

### **Auto-Saved Variables:**
- `user_id` - From user registration
- `product_id` - From product listing
- `order_id` - From order creation
- `admin_token` - From admin login
- `customer_token` - From customer login
- `demo_*` - Demo flow specific variables

### **Manual Variables:**
- `baseUrl` - Pre-configured as `http://localhost:8000`

---

## 🎯 Viva/Interview Preparation

### **Key Demonstrations:**
- **Async Processing:** Order creation doesn't block on payment
- **Message Queue:** RabbitMQ decouples Order ↔ Payment services
- **Microservices:** Independent services with HTTP + RabbitMQ communication
- **Role-Based Security:** Different permissions for users vs admins
- **Scalability:** Async architecture handles concurrent load better

### **Common Questions:**
- How does async improve performance?
- What if RabbitMQ fails?
- How do you ensure message delivery?
- Benefits of microservices architecture?
- How does authentication work across services?

---

## 🚀 Execution Checklist

### **Phase 1: Basic Async Verification** (5 min)
- [ ] Import collection into Postman
- [ ] Run Register → Products → Create Order
- [ ] Verify fast response (~100ms)
- [ ] Check status changes: `pending_payment` → `paid`
- [ ] Confirm transaction_id assigned

### **Phase 2: Core APIs Testing** (10 min)
- [ ] Test all User Service endpoints
- [ ] Test all Product Service endpoints (CRUD)
- [ ] Test Order Service endpoints
- [ ] Test Payment Service simulation
- [ ] Verify role-based access control

### **Phase 3: Demo Flow** (15 min)
- [ ] Run complete teacher demonstration
- [ ] Verify end-to-end functionality
- [ ] Check RabbitMQ message processing
- [ ] Confirm admin system visibility

---

## 📊 Performance Expectations

| Operation | Expected Time | What It Proves |
|-----------|---------------|----------------|
| Order Creation | <200ms | Async processing works |
| Status Check (immediate) | <100ms | Order stored, payment pending |
| Status Check (after wait) | <100ms | Payment processed, order updated |
| Product CRUD | <500ms | Admin operations functional |
| User Registration | <300ms | User management working |

---

## 🎉 Success Indicators

✅ **All tests pass** with green checkmarks
✅ **Order status transitions** automatically
✅ **Response times** meet performance targets
✅ **Role-based access** enforced correctly
✅ **RabbitMQ messages** processed successfully
✅ **Transaction IDs** assigned to completed orders
✅ **Admin dashboard** shows all system data

---

## 📞 Support

If tests fail:
1. Check Docker containers are running: `docker ps`
2. Verify RabbitMQ: http://localhost:15672
3. Check service logs: `docker logs payment-service`
4. Ensure endpoints don't have `/api/` prefix
5. Wait appropriate time for async processing

**Collection File:** `postman-collection.json`
**Guide File:** `POSTMAN-GUIDE.md`
**Diagram File:** `ASYNC-FLOW-DIAGRAM.txt`