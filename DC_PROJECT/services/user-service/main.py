import os
import random
import uuid
from datetime import datetime

import redis
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Payment Service")

# ENV VARIABLES
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

PAYMENT_FAIL_RATE = float(os.getenv("PAYMENT_FAIL_RATE", "0.3"))

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8003")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002")

# Redis (optional but kept for audit trail)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# -------------------------
# REQUEST MODEL
# -------------------------
class PaymentRequest(BaseModel):
    order_id: int
    amount: float


# -------------------------
# CORE PAYMENT LOGIC
# -------------------------
def process_payment(order_id: int, amount: float) -> dict:
    success = random.random() > PAYMENT_FAIL_RATE

    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

    payload = {
        "order_id": order_id,
        "amount": amount,
        "success": success,
        "transaction_id": transaction_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # store in Redis (audit trail)
    try:
        r.hset(
            f"payment:{order_id}",
            mapping={k: str(v) for k, v in payload.items()}
        )
    except Exception as e:
        print(f"Redis error: {e}")

    return payload


# -------------------------
# ORDER UPDATE
# -------------------------
def update_order_status(order_id: int, status: str, transaction_id: str):
    try:
        response = httpx.patch(
            f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
            json={
                "status": status,
                "transaction_id": transaction_id
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        print(f"Error updating order status: {exc}")
        return None


# -------------------------
# RESTORE STOCK ON FAILURE
# -------------------------
def restore_stock_for_order(order_id: int):
    try:
        order_resp = httpx.get(
            f"{ORDER_SERVICE_URL}/orders/{order_id}",
            timeout=10,
        )
        order_resp.raise_for_status()
        order = order_resp.json()

        product_id = order.get("product_id")
        quantity = order.get("quantity")

        if not product_id or quantity is None:
            return

        product_resp = httpx.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            timeout=10,
        )

        if product_resp.status_code != 200:
            return

        product = product_resp.json()

        updated_payload = {
            "name": product["name"],
            "description": product["description"],
            "price": product["price"],
            "stock": product["stock"] + quantity,
            "category": product.get("category"),
            "tags": product.get("tags"),
        }

        httpx.put(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            json=updated_payload,
            timeout=10,
        )

    except Exception as exc:
        print(f"Error restoring stock: {exc}")


# -------------------------
# MAIN PAYMENT ENDPOINT
# -------------------------
@app.post("/payments/process")
def process_payment_request(data: PaymentRequest):
    payment_result = process_payment(data.order_id, data.amount)

    status = "paid" if payment_result["success"] else "payment_failed"

    update_order_status(
        data.order_id,
        status,
        payment_result["transaction_id"]
    )

    if status == "payment_failed":
        restore_stock_for_order(data.order_id)

    return {
        **payment_result,
        "order_status": status
    }


# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "payment-service"}