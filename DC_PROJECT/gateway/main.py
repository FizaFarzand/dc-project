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

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL")

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
)

# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return {"message": "ok"}

# =========================
# JWT
# =========================

def decode_token(auth_header: Optional[str]):

    if not auth_header:

        raise HTTPException(
            status_code=401,
            detail="Missing token"
        )

    if not auth_header.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    token = auth_header.split(
        " ",
        1
    )[1]

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        return payload

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

# =========================
# FORWARD REQUEST
# =========================

async def forward(
    method: str,
    url: str,
    request: Request,
    json_body=None
):

    headers = {}

    if "authorization" in request.headers:

        headers["authorization"] = (
            request.headers["authorization"]
        )

    try:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_body
            )

        if response.status_code >= 400:

            try:

                detail = response.json()

            except Exception:

                detail = response.text

            raise HTTPException(
                status_code=response.status_code,
                detail=detail
            )

        return (
            response.json()
            if response.content
            else {}
        )

    except Exception as e:

        print("Gateway Error:", e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================
# ROUTER
# =========================

api = APIRouter(
    prefix="/api"
)

# =========================
# HEALTH
# =========================

@api.get("/health")
def api_health():

    return {
        "status":"ok"
    }

# =========================
# USERS
# =========================

@api.post("/users/register")
async def register(
    request: Request
):

    body=await request.json()

    return await forward(
        "POST",
        f"{USER_SERVICE_URL}/register",
        request,
        body
    )


@api.post("/users/login")
async def login(
    request:Request
):

    body=await request.json()

    return await forward(
        "POST",
        f"{USER_SERVICE_URL}/login",
        request,
        body
    )


@api.get("/users/me")
async def me(
    request:Request,
    authorization:Optional[str]=Header(None)
):

    decode_token(
        authorization
    )

    return await forward(
        "GET",
        f"{USER_SERVICE_URL}/me",
        request
    )

# =========================
# PRODUCTS
# =========================

@api.get("/products")
async def products(
    request:Request,
    authorization:Optional[str]=Header(None)
):

    decode_token(
        authorization
    )

    return await forward(
        "GET",
        f"{PRODUCT_SERVICE_URL}/products",
        request
    )


@api.get("/products/{product_id}")
async def product(
    product_id:str,
    request:Request,
    authorization:Optional[str]=Header(None)
):

    decode_token(
        authorization
    )

    return await forward(
        "GET",
        f"{PRODUCT_SERVICE_URL}/products/{product_id}",
        request
    )

# =========================
# ORDERS
# =========================

@api.post("/orders")
async def create_order(
    request:Request,
    authorization:Optional[str]=Header(None)
):

    payload=decode_token(
        authorization
    )

    body=await request.json()

    body["user_id"]=payload.get(
        "user_id"
    )

    return await forward(
        "POST",
        f"{ORDER_SERVICE_URL}/orders",
        request,
        body
    )


@api.get("/orders")
async def list_orders(
    request:Request,
    authorization:Optional[str]=Header(None)
):

    payload=decode_token(
        authorization
    )

    user_id=payload.get(
        "user_id"
    )

    role=payload.get(
        "role"
    )

    url=f"{ORDER_SERVICE_URL}/orders"

    if role!="admin":

        url += (
            f"?user_id={user_id}"
        )

    return await forward(
        "GET",
        url,
        request
    )


@api.get("/orders/{order_id}")
async def get_order(
    order_id:int,
    request:Request,
    authorization:Optional[str]=Header(None)
):

    decode_token(
        authorization
    )

    return await forward(
        "GET",
        f"{ORDER_SERVICE_URL}/orders/{order_id}",
        request
    )


# =========================
# REGISTER ROUTER
# =========================

app.include_router(
    api
)

# =========================
# ROOT HEALTH
# =========================

@app.get("/health")
def health():

    return {
        "status":"ok",
        "service":"gateway"
    }