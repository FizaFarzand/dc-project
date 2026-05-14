import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------- APP ----------------
app = FastAPI(
    title="User Service",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ENV ----------------
DATABASE_URL = os.getenv("MYSQL_PUBLIC_URL")

if not DATABASE_URL:
    raise Exception("MYSQL_PUBLIC_URL is missing")

DATABASE_URL = DATABASE_URL.replace(
    "mysql://",
    "mysql+pymysql://"
)

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# IMPORTANT:
# Railway public URL must use:
# mysql+pymysql://

# ---------------- DB ----------------
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# ---------------- MODEL ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="customer")

# ---------------- SCHEMAS ----------------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "customer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ---------------- SECURITY ----------------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100000
    ).hex()

    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000
        ).hex()

        return hmac.compare_digest(digest, expected)

    except Exception:
        return False


def create_token(user):
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )

# ---------------- STARTUP ----------------
@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database connected successfully")

    except Exception as e:
        print("Database startup error:", e)

# ---------------- ROUTES ----------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "user-service"
    }

# ---------------- REGISTER ----------------
@app.post("/register")
def register(data: RegisterRequest):
    db = SessionLocal()

    try:
        existing_user = db.query(User).filter(
            User.email == data.email
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already exists"
            )

        user = User(
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            role=data.role,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()

# ---------------- LOGIN ----------------
@app.post("/login")
def login(data: LoginRequest):
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == data.email
        ).first()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if not verify_password(
            data.password,
            user.password_hash
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        token = create_token(user)

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    finally:
        db.close()

# ---------------- ME ----------------
@app.get("/me")
def me(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing token"
        )

    token = authorization.replace("Bearer ", "")

    try:
        decoded = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        return decoded

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

# ---------------- USERS ----------------
@app.get("/users")
def list_users():
    db = SessionLocal()

    try:
        users = db.query(User).all()

        return [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role
            }
            for u in users
        ]

    finally:
        db.close()