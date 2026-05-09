import os
import json
import random
import uuid
import threading
from datetime import datetime

import redis
import pika
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Payment Service")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
PAYMENT_FAIL_RATE = float(os.getenv("PAYMENT_FAIL_RATE", "0.3"))
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8003")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class PaymentRequest(BaseModel):
    order_id: int
    amount: float


def get_rabbitmq_connection():
    """Create connection to RabbitMQ"""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        connection_attempts=5,
        retry_delay=2
    )
    return pika.BlockingConnection(parameters)


def process_payment(order_id: int, amount: float) -> dict:
    """Process payment and return result"""
    success = random.random() > PAYMENT_FAIL_RATE
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    payload = {
        "order_id": order_id,
        "amount": amount,
        "success": success,
        "transaction_id": transaction_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    # Store in Redis for audit trail
    r.hset(f"payment:{order_id}", mapping={k: str(v) for k, v in payload.items()})
    return payload


def update_order_status(order_id: int, status: str, transaction_id: str):
    try:
        response = httpx.patch(
            f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
            json={"status": status, "transaction_id": transaction_id},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        print(f"Error updating order status: {exc}")
        return None


def restore_stock_for_order(order_id: int):
    try:
        response = httpx.get(f"{ORDER_SERVICE_URL}/orders/{order_id}", timeout=10)
        response.raise_for_status()
        order = response.json()
        product_id = order.get("product_id")
        quantity = order.get("quantity")
        if not product_id or quantity is None:
            return

        product_resp = httpx.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}", timeout=10)
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
        httpx.put(f"{PRODUCT_SERVICE_URL}/products/{product_id}", json=updated_payload, timeout=10)
    except Exception as exc:
        print(f"Error restoring stock for order {order_id}: {exc}")


def callback(ch, method, properties, body):
    """Callback for RabbitMQ message consumer"""
    try:
        message = json.loads(body)
        order_id = message.get("order_id")
        amount = message.get("amount")
        
        print(f"Processing payment for order {order_id}, amount: {amount}")
        
        # Process the payment
        payment_result = process_payment(order_id, amount)
        status = "paid" if payment_result.get("success") else "payment_failed"
        transaction_id = payment_result.get("transaction_id")
        
        update_order_status(order_id, status, transaction_id)
        if status == "payment_failed":
            restore_stock_for_order(order_id)

        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def start_payment_consumer():
    """Start RabbitMQ consumer in background thread"""
    def consume():
        try:
            import sys
            sys.stdout.flush()
            print("Attempting to connect to RabbitMQ...", flush=True)
            sys.stdout.flush()
            
            connection = get_rabbitmq_connection()
            print("Connected to RabbitMQ", flush=True)
            sys.stdout.flush()
            
            channel = connection.channel()
            print("Channel created", flush=True)
            sys.stdout.flush()
            
            channel.queue_declare(queue="payment_queue", durable=True)
            print("Queue declared", flush=True)
            sys.stdout.flush()
            
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue="payment_queue", on_message_callback=callback)
            
            print("🚀 Payment consumer started, waiting for messages...", flush=True)
            sys.stdout.flush()
            channel.start_consuming()
        except Exception as e:
            import traceback
            print(f"❌ Consumer error: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            # Retry after 5 seconds
            threading.Timer(5.0, start_payment_consumer).start()
    
    thread = threading.Thread(target=consume, daemon=True)
    thread.start()


@app.on_event("startup")
def startup():
    """Start payment consumer on app startup"""
    start_payment_consumer()


@app.get("/health")
def health():
    return {"status": "ok", "service": "payment-service"}


@app.post("/payments/simulate")
def simulate_payment(data: PaymentRequest):
    """Direct payment endpoint (for backwards compatibility)"""
    payload = process_payment(data.order_id, data.amount)
    status = "paid" if payload.get("success") else "payment_failed"
    update_order_status(data.order_id, status, payload.get("transaction_id"))
    if status == "payment_failed":
        restore_stock_for_order(data.order_id)
    return {
        **payload,
        "order_status": status,
    }
