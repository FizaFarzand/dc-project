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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ENV ----------------
DB_HOST = os.getenv("ORDER_DB_HOST")
DB_PORT = os.getenv("ORDER_DB_PORT", "3306")
DB_NAME = os.getenv("ORDER_DB_NAME")
DB_USER = os.getenv("ORDER_DB_USER")
DB_PASSWORD = os.getenv("ORDER_DB_PASSWORD")

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")

# ---------------- DB ----------------
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# ---------------- MODEL ----------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    product_id = Column(String(100))
    quantity = Column(Integer)
    total_price = Column(Float)
    status = Column(String(50))
    transaction_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class OrderCreate(BaseModel):
    user_id: int
    product_id: str
    quantity: int

# ---------------- STARTUP ----------------
@app.on_event("startup")
def startup():
    for _ in range(30):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except OperationalError:
            sleep(2)

# ---------------- HEALTH ----------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "order-service"}

# ---------------- CREATE ORDER ----------------
@app.post("/orders")
async def create_order(data: OrderCreate):

    async with httpx.AsyncClient(timeout=20) as client:

        # GET PRODUCT
        product_res = await client.get(
            f"{PRODUCT_SERVICE_URL}/products/{data.product_id}"
        )

    if product_res.status_code != 200:
        raise HTTPException(status_code=404, detail="Product not found")

    product = product_res.json()

    if product["stock"] < data.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    # UPDATE STOCK
    updated_product = product.copy()
    updated_product["stock"] -= data.quantity

    async with httpx.AsyncClient() as client:
        await client.put(
            f"{PRODUCT_SERVICE_URL}/products/{data.product_id}",
            json=updated_product
        )

    total = product["price"] * data.quantity

    # SAVE ORDER
    db = SessionLocal()
    order = Order(
        user_id=data.user_id,
        product_id=data.product_id,
        quantity=data.quantity,
        total_price=total,
        status="pending_payment"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    db.close()

    # CALL PAYMENT
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{PAYMENT_SERVICE_URL}/payments/process",
            json={"order_id": order.id, "amount": total}
        )

    return {
        "id": order.id,
        "status": order.status,
        "total_price": order.total_price
    }