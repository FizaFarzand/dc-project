import os
import random
import uuid
from datetime import datetime

import httpx
import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Payment Service")

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dc-project-gamma.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ENV ----------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")

PAYMENT_FAIL_RATE = float(os.getenv("PAYMENT_FAIL_RATE", "0.3"))

# ---------------- REDIS ----------------
try:
    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )

    r.ping()

    print("Redis connected successfully")

except Exception as e:
    print("Redis connection failed:", e)

# ---------------- MODEL ----------------
class Payment(BaseModel):
    order_id: int
    amount: float

# ---------------- PAYMENT ----------------
def process_payment(order_id, amount):

    success = random.random() > PAYMENT_FAIL_RATE

    txn = f"txn_{uuid.uuid4().hex[:10]}"

    data = {
        "order_id": order_id,
        "amount": amount,
        "success": success,
        "transaction_id": txn,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        r.hset(
            f"payment:{order_id}",
            mapping={k: str(v) for k, v in data.items()}
        )

    except Exception as e:
        print("Redis save error:", e)

    return data

# ---------------- UPDATE ORDER ----------------
def update_order(order_id, status, txn):

    try:
        response = httpx.patch(
            f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
            json={
                "status": status,
                "transaction_id": txn
            },
            timeout=10.0
        )

        print("Order update response:", response.status_code)

    except Exception as e:
        print("Order update error:", e)

# ---------------- RESTORE STOCK ----------------
def restore(order_id):

    try:
        order_response = httpx.get(
            f"{ORDER_SERVICE_URL}/orders/{order_id}",
            timeout=10.0
        )

        order = order_response.json()

        product_response = httpx.get(
            f"{PRODUCT_SERVICE_URL}/products/{order['product_id']}",
            timeout=10.0
        )

        product = product_response.json()

        product["stock"] += order["quantity"]

        httpx.put(
            f"{PRODUCT_SERVICE_URL}/products/{order['product_id']}",
            json=product,
            timeout=10.0
        )

        print("Stock restored successfully")

    except Exception as e:
        print("Restore error:", e)

# ---------------- API ----------------
@app.post("/payments/process")
def pay(data: Payment):

    print("Processing payment for order:", data.order_id)

    result = process_payment(data.order_id, data.amount)

    status = "paid" if result["success"] else "payment_failed"

    print("Payment status:", status)

    update_order(
        data.order_id,
        status,
        result["transaction_id"]
    )

    if status == "payment_failed":
        restore(data.order_id)

    return {
        **result,
        "status": status
    }

# ---------------- HEALTH ----------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "payment-service"
    }