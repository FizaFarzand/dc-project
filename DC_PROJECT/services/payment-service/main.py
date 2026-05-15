import os
import uuid
import random
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

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

ORDER_SERVICE_URL = os.getenv(
    "ORDER_SERVICE_URL"
)

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL"
)

PAYMENT_FAIL_RATE = float(
    os.getenv(
        "PAYMENT_FAIL_RATE",
        "0.2"
    )
)

# ---------------- REDIS ----------------

try:

    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )

    r.ping()

    print(
        "Redis connected successfully"
    )

except Exception as e:

    print(
        "Redis failed:",
        e
    )

# ---------------- MODEL ----------------

class Payment(BaseModel):

    order_id:int
    amount:float


# ---------------- PROCESS PAYMENT ----------------

def process_payment(
    order_id,
    amount
):

    # ---------------- REAL SIMULATION LOGIC ----------------
    rand_value = random.random()

    success = rand_value > PAYMENT_FAIL_RATE

    txn = (
        f"txn_{uuid.uuid4().hex[:10]}"
    )

    data = {

        "order_id": order_id,
        "amount": amount,
        "success": success,

        "transaction_id": txn,

        "timestamp":
        datetime.utcnow().isoformat()

    }

    try:

        r.hset(
            f"payment:{order_id}",
            mapping={
                k: str(v)
                for k, v in data.items()
            }
        )

        print(
            "Saved in redis"
        )

    except Exception as e:

        print(
            "Redis save error:",
            e
        )

    return data


# ---------------- UPDATE ORDER ----------------

def update_order(
        order_id,
        status,
        txn
):

    try:

        response = httpx.patch(

            f"{ORDER_SERVICE_URL}/orders/{order_id}/status",

            json={

                "status": status,

                "transaction_id": txn
            },

            timeout=20
        )

        print(
            "ORDER UPDATE:",
            response.status_code
        )

        print(
            response.text
        )

    except Exception as e:

        print(
            "ORDER UPDATE ERROR:",
            e
        )


# ---------------- API ----------------

@app.post(
    "/payments/process"
)
def pay(
    data: Payment
):

    print(
        "Processing:",
        data.order_id
    )

    result = process_payment(
        data.order_id,
        data.amount
    )

    # use real simulation result
    status = "paid" if result["success"] else "payment_failed"

    update_order(
        data.order_id,
        status,
        result["transaction_id"]
    )

    return {

        **result,
        "status": status
    }


# ---------------- HEALTH ----------------

@app.get(
    "/health"
)
def health():

    return {

        "status": "ok",

        "service":
        "payment-service"
    }