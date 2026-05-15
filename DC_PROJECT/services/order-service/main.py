import os
from datetime import datetime
from time import sleep
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI(title="Order Service")

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

DB_HOST = os.getenv("ORDER_DB_HOST")
DB_PORT = os.getenv("ORDER_DB_PORT", "3306")
DB_NAME = os.getenv("ORDER_DB_NAME")
DB_USER = os.getenv("ORDER_DB_USER")
DB_PASSWORD = os.getenv("ORDER_DB_PASSWORD")

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ---------------- DATABASE ----------------

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()

# ---------------- MODELS ----------------


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    product_id = Column(String(100))
    quantity = Column(Integer)
    total_price = Column(Float)

    status = Column(String(50))

    transaction_id = Column(String(100))

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class OrderCreate(BaseModel):
    user_id: int
    product_id: str
    quantity: int


class OrderUpdate(BaseModel):
    status: str
    transaction_id: str


# ---------------- STARTUP ----------------

@app.on_event("startup")
def startup():

    for _ in range(30):

        try:

            Base.metadata.create_all(
                bind=engine
            )

            print("Database connected")

            break

        except OperationalError as e:

            print("DB connection failed:", e)

            sleep(2)


# ---------------- HEALTH ----------------

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "order-service"
    }


# ---------------- CREATE ORDER ----------------

@app.post("/orders")
async def create_order(data: OrderCreate):

    try:

        async with httpx.AsyncClient(
            timeout=20
        ) as client:

            product_res = await client.get(
                f"{PRODUCT_SERVICE_URL}/products/{data.product_id}"
            )

        if product_res.status_code != 200:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        product = product_res.json()

        if product["stock"] < data.quantity:
            raise HTTPException(
                status_code=400,
                detail="Not enough stock"
            )

        updated_product = product.copy()

        updated_product["stock"] -= data.quantity

        async with httpx.AsyncClient() as client:

            await client.put(
                f"{PRODUCT_SERVICE_URL}/products/{data.product_id}",
                json=updated_product
            )

        total = product["price"] * data.quantity

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

        async with httpx.AsyncClient(
            timeout=20
        ) as client:

            await client.post(
                f"{PAYMENT_SERVICE_URL}/payments/process",
                json={
                    "order_id": order.id,
                    "amount": total
                }
            )

        return {
            "id": order.id,
            "user_id": order.user_id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "total_price": order.total_price,
            "status": order.status
        }

    except Exception as e:

        print("CREATE ORDER ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------- GET ALL ORDERS ----------------

@app.get("/orders")
def get_orders(
    user_id: Optional[int] = Query(None)
):

    try:

        db = SessionLocal()

        query = db.query(Order)

        if user_id:

            query = query.filter(
                Order.user_id == user_id
            )

        orders = query.order_by(
            Order.created_at.desc()
        ).all()

        result = [

            {
                "id": o.id,
                "user_id": o.user_id,
                "product_id": o.product_id,
                "quantity": o.quantity,
                "total_price": o.total_price,
                "status": o.status,
            }

            for o in orders

        ]

        db.close()

        return result

    except Exception as e:

        print("GET ORDERS ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------- GET SINGLE ORDER ----------------

@app.get("/orders/{order_id}")
def get_order(order_id: int):

    db = SessionLocal()

    order = db.query(
        Order
    ).filter(
        Order.id == order_id
    ).first()

    db.close()

    if not order:

        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return {
        "id": order.id,
        "user_id": order.user_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "total_price": order.total_price,
        "status": order.status
    }


# ---------------- UPDATE STATUS ----------------

@app.patch("/orders/{order_id}/status")
def update_order_status(
        order_id: int,
        data: OrderUpdate
):

    db = SessionLocal()

    order = db.query(
        Order
    ).filter(
        Order.id == order_id
    ).first()

    if not order:

        db.close()

        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    order.status = data.status

    order.transaction_id = data.transaction_id

    db.commit()

    db.close()

    return {
        "message": "updated"
    }