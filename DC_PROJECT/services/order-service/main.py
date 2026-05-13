import os
from datetime import datetime
from time import sleep
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI(title="Order Service")

# ✅ CORS ADDED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ENV ----------------
DB_HOST = os.getenv("ORDER_DB_HOST", "localhost")
DB_PORT = os.getenv("ORDER_DB_PORT", "3306")
DB_NAME = os.getenv("ORDER_DB_NAME", "order_db")
DB_USER = os.getenv("ORDER_DB_USER", "root")
DB_PASSWORD = os.getenv("ORDER_DB_PASSWORD", "root")

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8004")

# ---------------- DB ----------------
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------- MODEL ----------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(String(64), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String(30), default="created")
    transaction_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CreateOrderRequest(BaseModel):
    user_id: int
    product_id: str
    quantity: int


class UpdateStatusRequest(BaseModel):
    status: str
    transaction_id: Optional[str] = None


# ---------------- STARTUP ----------------
@app.on_event("startup")
def startup():
    for i in range(30):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if i == 29:
                raise
            sleep(2)


# ---------------- HEALTH ----------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}


# ---------------- CREATE ORDER ----------------
@app.post("/orders")
async def create_order(data: CreateOrderRequest):

    async with httpx.AsyncClient(timeout=20) as client:
        product_resp = await client.get(
            f"{PRODUCT_SERVICE_URL}/products/{data.product_id}"
        )

    if product_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Product not found")

    product = product_resp.json()

    if product.get("stock", 0) < data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    updated_product = {
        "name": product["name"],
        "description": product["description"],
        "price": product["price"],
        "stock": product["stock"] - data.quantity,
        "category": product.get("category"),
        "tags": product.get("tags"),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        await client.put(
            f"{PRODUCT_SERVICE_URL}/products/{data.product_id}",
            json=updated_product
        )

    total_price = round(product["price"] * data.quantity, 2)

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

    # call payment service
    async with httpx.AsyncClient(timeout=20) as client:
        payment_resp = await client.post(
            f"{PAYMENT_SERVICE_URL}/payments/process",
            json={"order_id": order.id, "amount": total_price}
        )

    if payment_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Payment failed")

    return order