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

# ✅ CORS ADDED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ENV ----------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

PAYMENT_FAIL_RATE = float(os.getenv("PAYMENT_FAIL_RATE", "0.3"))

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8003")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# ---------------- MODEL ----------------
class PaymentRequest(BaseModel):
    order_id: int
    amount: float


# ---------------- PAYMENT LOGIC ----------------
def process_payment(order_id: int, amount: float):
    success = random.random() > PAYMENT_FAIL_RATE
    txn_id = f"txn_{uuid.uuid4().hex[:10]}"

    data = {
        "order_id": order_id,
        "amount": amount,
        "success": success,
        "transaction_id": txn_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        r.hset(f"payment:{order_id}", mapping={k: str(v) for k, v in data.items()})
    except:
        pass

    return data


def update_order(order_id: int, status: str, txn_id: str):
    try:
        httpx.patch(
            f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
            json={"status": status, "transaction_id": txn_id},
            timeout=10,
        )
    except:
        pass


def restore_stock(order_id: int):
    try:
        order = httpx.get(f"{ORDER_SERVICE_URL}/orders/{order_id}", timeout=10).json()

        product = httpx.get(
            f"{PRODUCT_SERVICE_URL}/products/{order['product_id']}",
            timeout=10
        ).json()

        product["stock"] += order["quantity"]

        httpx.put(
            f"{PRODUCT_SERVICE_URL}/products/{order['product_id']}",
            json=product,
            timeout=10,
        )
    except:
        pass


# ---------------- MAIN API ----------------
@app.post("/payments/process")
def pay(data: PaymentRequest):

    result = process_payment(data.order_id, data.amount)

    status = "paid" if result["success"] else "payment_failed"

    update_order(data.order_id, status, result["transaction_id"])

    if status == "payment_failed":
        restore_stock(data.order_id)

    return {
        **result,
        "order_status": status
    }


# ---------------- HEALTH ----------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "payment-service"}