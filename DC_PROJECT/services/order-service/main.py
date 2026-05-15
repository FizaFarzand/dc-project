import os
from datetime import datetime
from time import sleep
from typing import Optional

import httpx
from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Header
)
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI(title="Order Service")

# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dc-project-gamma.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ENV
# =========================

DB_HOST = os.getenv("ORDER_DB_HOST")
DB_PORT = os.getenv("ORDER_DB_PORT", "3306")
DB_NAME = os.getenv("ORDER_DB_NAME")
DB_USER = os.getenv("ORDER_DB_USER")
DB_PASSWORD = os.getenv("ORDER_DB_PASSWORD")

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL"
)

PAYMENT_SERVICE_URL = os.getenv(
    "PAYMENT_SERVICE_URL"
)

JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "supersecretkey"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# =========================
# DATABASE
# =========================

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

# =========================
# MODELS
# =========================

class Order(Base):

    __tablename__ = "orders"

    id = Column(
        Integer,
        primary_key=True
    )

    user_id = Column(Integer)

    product_id = Column(
        String(100)
    )

    quantity = Column(Integer)

    total_price = Column(Float)

    status = Column(
        String(50)
    )

    transaction_id = Column(
        String(100),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

# =========================
# SCHEMAS
# =========================

class OrderCreate(BaseModel):

    user_id: int
    product_id: str
    quantity: int


class OrderUpdate(BaseModel):

    status: str
    transaction_id: Optional[str] = None

# =========================
# AUTH
# =========================

def get_current_user(
    authorization: Optional[str]
):

    try:

        if not authorization:
            return None

        token = authorization.replace(
            "Bearer ",
            ""
        )

        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = (
            decoded.get("user_id")
            or decoded.get("id")
            or decoded.get("sub")
        )

        return user_id

    except Exception as e:

        print(
            "JWT ERROR:",
            e
        )

        return None


# =========================
# STARTUP
# =========================

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

            print(
                "DB connection failed:",
                e
            )

            sleep(2)

# =========================
# HEALTH
# =========================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "order-service"
    }

# =========================
# CREATE ORDER
# =========================

@app.post("/orders")
async def create_order(
    data: OrderCreate
):

    db = SessionLocal()

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

        async with httpx.AsyncClient(
            timeout=20
        ) as client:

            update_res = await client.put(
                f"{PRODUCT_SERVICE_URL}/products/{data.product_id}",
                json=updated_product
            )

        if update_res.status_code >= 400:

            raise HTTPException(
                status_code=500,
                detail="Failed to update stock"
            )

        total = (
            product["price"] *
            data.quantity
        )

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

    except HTTPException:
        raise

    except Exception as e:

        print(
            "CREATE ORDER ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()

# =========================
# GET ALL ORDERS
# =========================

@app.get("/orders")
def get_orders(
    authorization: Optional[str] = Header(None)
):

    db = SessionLocal()

    try:

        user_id = get_current_user(
            authorization
        )

        query = db.query(Order)

        if user_id:

            query = query.filter(
                Order.user_id ==
                int(user_id)
            )

        orders = query.order_by(
            Order.created_at.desc()
        ).all()

        return [

            {
                "id": o.id,
                "user_id": o.user_id,
                "product_id": o.product_id,
                "quantity": o.quantity,
                "total_price": o.total_price,
                "status": o.status,
                "transaction_id": o.transaction_id,
                "created_at": o.created_at
            }

            for o in orders
        ]

    finally:

        db.close()

# =========================
# GET SINGLE ORDER
# =========================

@app.get("/orders/{order_id}")
def get_order(
    order_id: int,
    authorization: Optional[str] = Header(None)
):

    db = SessionLocal()

    try:

        user_id = get_current_user(
            authorization
        )

        order = db.query(
            Order
        ).filter(
            Order.id == order_id
        ).first()

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        if user_id:

            if int(user_id) != order.user_id:

                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )

        return {
            "id": order.id,
            "user_id": order.user_id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "total_price": order.total_price,
            "status": order.status,
            "transaction_id": order.transaction_id,
            "created_at": order.created_at
        }

    finally:

        db.close()

# =========================
# UPDATE ORDER STATUS
# =========================

@app.patch("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    data: OrderUpdate
):

    db = SessionLocal()

    try:

        order = db.query(
            Order
        ).filter(
            Order.id == order_id
        ).first()

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        order.status = data.status

        if data.transaction_id:

            order.transaction_id = (
                data.transaction_id
            )

        db.commit()

        return {
            "message": "updated",
            "order_id": order.id,
            "status": order.status
        }

    except Exception as e:

        print(
            "UPDATE ORDER ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        db.close()