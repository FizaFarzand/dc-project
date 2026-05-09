import os
import json
from datetime import datetime
from time import sleep
from typing import Optional

import httpx
import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI(title="Order Service")

DB_HOST = os.getenv("ORDER_DB_HOST", "localhost")
DB_PORT = os.getenv("ORDER_DB_PORT", "3306")
DB_NAME = os.getenv("ORDER_DB_NAME", "order_db")
DB_USER = os.getenv("ORDER_DB_USER", "root")
DB_PASSWORD = os.getenv("ORDER_DB_PASSWORD", "root")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    product_id = Column(String(64), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String(30), nullable=False, default="created")
    transaction_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CreateOrderRequest(BaseModel):
    user_id: int
    product_id: str
    quantity: int


class UpdateStatusRequest(BaseModel):
    status: str
    transaction_id: Optional[str] = None


@app.on_event("startup")
def startup():
    # MySQL container can be up before it is ready to accept connections.
    for attempt in range(30):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if attempt == 29:
                raise
            sleep(2)


@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}


@app.post("/orders")
async def create_order(data: CreateOrderRequest):
    async with httpx.AsyncClient(timeout=20.0) as client:
        product_resp = await client.get(f"{PRODUCT_SERVICE_URL}/products/{data.product_id}")
    if product_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Product not found")
    product = product_resp.json()
    if product.get("stock", 0) < data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    updated_payload = {
        "name": product["name"],
        "description": product["description"],
        "price": product["price"],
        "stock": product["stock"] - data.quantity,
        "category": product.get("category"),
        "tags": product.get("tags"),
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        await client.put(f"{PRODUCT_SERVICE_URL}/products/{data.product_id}", json=updated_payload)

    total_price = float(round(float(product["price"]) * data.quantity, 2))
    db = SessionLocal()
    try:
        order = Order(
            user_id=data.user_id,
            product_id=data.product_id,
            quantity=data.quantity,
            total_price=total_price,
            status="pending_payment",
        )
        db.add(order)
        db.commit()
        db.refresh(order)
    finally:
        db.close()

    # Publish payment request to RabbitMQ instead of direct HTTP call
    payment_payload = {"order_id": order.id, "amount": total_price}
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue="payment_queue", durable=True)
        channel.basic_publish(
            exchange='',
            routing_key='payment_queue',
            body=json.dumps(payment_payload),
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )
        connection.close()
    except Exception as e:
        print(f"Error publishing to RabbitMQ: {e}")
        raise HTTPException(status_code=500, detail="Failed to process payment request")

    return {
        "id": order.id,
        "user_id": order.user_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "total_price": order.total_price,
        "status": order.status,
        "transaction_id": order.transaction_id,
        "created_at": order.created_at,
    }


@app.get("/orders")
def list_orders(user_id: Optional[int] = None):
    db = SessionLocal()
    try:
        query = db.query(Order)
        if user_id is not None:
            query = query.filter(Order.user_id == user_id)
        orders = query.order_by(Order.created_at.desc()).all()
        return [
            {
                "id": o.id,
                "user_id": o.user_id,
                "product_id": o.product_id,
                "quantity": o.quantity,
                "total_price": o.total_price,
                "status": o.status,
                "transaction_id": o.transaction_id,
                "created_at": o.created_at,
            }
            for o in orders
        ]
    finally:
        db.close()


@app.get("/orders/{order_id}")
def get_order(order_id: int, user_id: Optional[int] = None):
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if user_id is not None and order.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return {
            "id": order.id,
            "user_id": order.user_id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "total_price": order.total_price,
            "status": order.status,
            "transaction_id": order.transaction_id,
            "created_at": order.created_at,
        }
    finally:
        db.close()


@app.patch("/orders/{order_id}/status")
def update_order_status(order_id: int, data: UpdateStatusRequest):
    valid_statuses = {"created", "pending_payment", "paid", "payment_failed", "cancelled"}
    status = data.status.strip().lower()
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status '{data.status}'")

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order.status = status
        if data.transaction_id:
            order.transaction_id = data.transaction_id
        db.commit()
        db.refresh(order)
        return {
            "id": order.id,
            "status": order.status,
            "transaction_id": order.transaction_id,
        }
    finally:
        db.close()
