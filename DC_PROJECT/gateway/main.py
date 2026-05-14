import os
from typing import Optional

import httpx
from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt


app = FastAPI(title="API Gateway")

# =========================
# ENVIRONMENT VARIABLES
# =========================

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8002")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8003")

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Frontend URL for Vercel deployment
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


# =========================
# CORS CONFIGURATION
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",

        "https://dc-project-gamma.vercel.app",

        "https://dc-project-fizafarzands-projects.vercel.app",

        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# JWT TOKEN VALIDATION
# =========================

def decode_token(auth_header: Optional[str]) -> dict:
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ", 1)[1]

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload

    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


# =========================
# REQUEST FORWARDING
# =========================

async def forward(method: str, url: str, request: Request, json_body=None):
    headers = {}

    if "authorization" in request.headers:
        headers["authorization"] = request.headers["authorization"]

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.request(
            method=method,
            url=url,
            params=dict(request.query_params),
            headers=headers,
            json=json_body,
        )

        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = {"detail": response.text}

            raise HTTPException(
                status_code=response.status_code,
                detail=detail
            )

        return response.json() if response.content else {}


# =========================
# API ROUTER
# =========================

api = APIRouter(prefix="/api")


# =========================
# HEALTH CHECK
# =========================

@api.get("/health")
def api_health():
    return {
        "status": "ok",
        "service": "api-gateway"
    }


# =========================
# USER ROUTES
# =========================

@api.post("/users/register")
async def register(request: Request):
    body = await request.json()

    return await forward(
        "POST",
        f"{USER_SERVICE_URL}/register",
        request,
        body,
    )


@api.post("/users/login")
async def login(request: Request):
    body = await request.json()

    return await forward(
        "POST",
        f"{USER_SERVICE_URL}/login",
        request,
        body,
    )


@api.get("/users/me")
async def me(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    _ = decode_token(authorization)

    return await forward(
        "GET",
        f"{USER_SERVICE_URL}/me",
        request,
    )


@api.get("/users")
async def list_users(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    payload = decode_token(authorization)

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    return await forward(
        "GET",
        f"{USER_SERVICE_URL}/users",
        request,
    )


# =========================
# PRODUCT ROUTES
# =========================

@api.get("/products")
async def list_products(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    _ = decode_token(authorization)

    return await forward(
        "GET",
        f"{PRODUCT_SERVICE_URL}/products",
        request,
    )


@api.get("/products/search")
async def search_products(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    _ = decode_token(authorization)

    return await forward(
        "GET",
        f"{PRODUCT_SERVICE_URL}/products/search",
        request,
    )


@api.get("/products/{product_id}")
async def get_product(
    product_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    _ = decode_token(authorization)

    return await forward(
        "GET",
        f"{PRODUCT_SERVICE_URL}/products/{product_id}",
        request,
    )


@api.post("/products")
async def create_product(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    payload = decode_token(authorization)

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    body = await request.json()

    return await forward(
        "POST",
        f"{PRODUCT_SERVICE_URL}/products",
        request,
        body,
    )


@api.put("/products/{product_id}")
async def update_product(
    product_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    payload = decode_token(authorization)

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    body = await request.json()

    return await forward(
        "PUT",
        f"{PRODUCT_SERVICE_URL}/products/{product_id}",
        request,
        body,
    )


@api.delete("/products/{product_id}")
async def delete_product(
    product_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    payload = decode_token(authorization)

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    return await forward(
        "DELETE",
        f"{PRODUCT_SERVICE_URL}/products/{product_id}",
        request,
    )


# =========================
# ORDER ROUTES
# =========================

@api.post("/orders")
async def create_order(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    payload = decode_token(authorization)

    body = await request.json()
    body["user_id"] = payload.get("user_id")

    return await forward(
        "POST",
        f"{ORDER_SERVICE_URL}/orders",
        request,
        body,
    )


@api.get("/orders")
async def list_orders(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    payload = decode_token(authorization)

    user_id = payload.get("user_id")
    role = payload.get("role")

    params = f"?user_id={user_id}" if role != "admin" else ""

    return await forward(
        "GET",
        f"{ORDER_SERVICE_URL}/orders{params}",
        request,
    )


@api.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    payload = decode_token(authorization)

    user_id = payload.get("user_id")
    role = payload.get("role")

    if role == "admin":
        return await forward(
            "GET",
            f"{ORDER_SERVICE_URL}/orders/{order_id}",
            request,
        )

    return await forward(
        "GET",
        f"{ORDER_SERVICE_URL}/orders/{order_id}?user_id={user_id}",
        request,
    )


@api.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    payload = decode_token(authorization)

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    body = await request.json()

    return await forward(
        "PATCH",
        f"{ORDER_SERVICE_URL}/orders/{order_id}/status",
        request,
        body,
    )


# =========================
# REGISTER ROUTER
# =========================

app.include_router(api)


# =========================
# ROOT HEALTHCHECK
# =========================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "api-gateway"
    }