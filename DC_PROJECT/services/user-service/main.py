import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from time import sleep

from fastapi import FastAPI, Header, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI(title="User Service")

DB_HOST = os.getenv("USER_DB_HOST", "localhost")
DB_PORT = os.getenv("USER_DB_PORT", "3306")
DB_NAME = os.getenv("USER_DB_NAME", "user_db")
DB_USER = os.getenv("USER_DB_USER", "root")
DB_PASSWORD = os.getenv("USER_DB_PASSWORD", "root")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="customer", nullable=False)


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "customer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return hmac.compare_digest(digest, expected)


def create_access_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


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
    return {"status": "ok", "service": "user-service"}


@app.post("/register")
def register(data: RegisterRequest):
    db = SessionLocal()
    try:
        hashed = hash_password(data.password)
        user = User(name=data.name, email=data.email, password_hash=hashed, role=data.role.lower())
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists") from exc
    finally:
        db.close()


@app.post("/login")
def login(data: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_access_token(user)
        return {"access_token": token, "token_type": "bearer"}
    finally:
        db.close()


@app.get("/me")
def me(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "name": user.name,
        }
    finally:
        db.close()


@app.get("/users")
def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return [
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            }
            for user in users
        ]
    finally:
        db.close()
