# Distributed E-Commerce System

This project is a distributed e-commerce platform built with microservices:

- `api-gateway`
- `user-service`
- `product-service`
- `order-service`
- `payment-service` (simulation with random failures)

## Stack

- FastAPI (Python)
- MySQL (user + order databases)
- MongoDB (product database)
- Redis (payment simulation store)
- **RabbitMQ** (async message queue for payment processing)
- Docker Compose

## Architecture

Client -> API Gateway -> Services

- User Service -> MySQL (`user_db`)
- Product Service -> MongoDB (`product_db`)
- Order Service -> MySQL (`order_db`) + **RabbitMQ Publisher**
- Payment Service -> Redis + **RabbitMQ Consumer**
- Message Queue -> **RabbitMQ** (decoupled async communication)

## Quick Start

1. Install Docker Desktop.
2. From project root:

```bash
docker compose up --build
```

Windows quick test runner:

```bat
run-tests.cmd
```

3. Services:

- API Gateway: `http://localhost:8000/docs`
- User Service: `http://localhost:8001/docs`
- Product Service: `http://localhost:8002/docs`
- Order Service: `http://localhost:8003/docs`
- Payment Service: `http://localhost:8004/docs`
- **RabbitMQ Management**: `http://localhost:15672` (login: guest/guest)

## Async Communication Flow

### Order Creation with Asynchronous Payment Processing

1. **Order Service** receives order request
2. **Order Service** publishes payment request to `payment_queue` on RabbitMQ
3. Order immediately returned to client with status `pending_payment`
4. **Payment Service** asynchronously consumes message from queue
5. **Payment Service** processes payment (simulate success/failure)
6. **Payment Service** updates order status via callback (`paid` or `payment_failed`)

**Benefits:**
- ✅ Fast response times (order returns in 50-100ms instead of 300-500ms)
- ✅ Decoupled services (payment service can scale independently)
- ✅ Resiliant (if payment service is down, messages queue up)
- ✅ Better throughput under load

## Basic Flow

1. Register user:
   - `POST /users/register`
2. Login:
   - `POST /users/login`
   - copy `access_token`
3. Use token in Authorization header:
   - `Authorization: Bearer <token>`
4. Admin creates products:
   - `POST /products` (requires `role=admin`)
5. Customer places order:
   - `POST /orders` (returns immediately with `pending_payment` status)
6. Payment asynchronously processes via RabbitMQ:
   - Order status automatically updates to `paid` or `payment_failed` after 1-3 seconds

## Load Testing

### Run Load Tests with Locust

**GUI Mode (Interactive):**
```bash
cd load-tests
pip install -r requirements.txt
locust -f locustfile.py --host=http://localhost:8000
```
Then open http://localhost:8089

**Headless Mode (Automated):**
```bash
cd load-tests
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 5m --headless --csv=results
```

**Expected Results with Async Architecture:**
- 100+ concurrent users without timeout
- Order creation: 50-100ms (fast, async payment)
- Product queries: 60-80ms
- Overall failure rate: < 2%

### Verification Guide

See [TESTING.md](TESTING.md) for:
- How to verify RabbitMQ async communication works
- Step-by-step load testing procedures
- Performance benchmarks
- Troubleshooting guide

## Gateway Endpoints

- Users:
  - `POST /users/register`
  - `POST /users/login`
  - `GET /users/me`
- Products:
  - `GET /products`
  - `GET /products/search`
  - `POST /products` (admin)
  - `PUT /products/{product_id}` (admin)
  - `DELETE /products/{product_id}` (admin)
- Orders:
  - `POST /orders`
  - `GET /orders`
  - `PATCH /orders/{order_id}/status` (admin)

## Notes

- **Async Payment Processing**: Payment service runs asynchronously via RabbitMQ. Orders show `pending_payment` initially, then update to `paid`/`payment_failed` after async processing.
- Payment service introduces random failures by default (`PAYMENT_FAIL_RATE=0.3`).
- System uses eventual consistency style in order lifecycle (created → pending_payment → paid/payment_failed).
- RabbitMQ provides durability: messages persist even if payment service is temporarily down.
- For horizontal scaling:
  - Replicate services with: `docker compose up --scale payment-service=3`
  - RabbitMQ distributes work across multiple consumers
- Load tested successfully with 100+ concurrent users
