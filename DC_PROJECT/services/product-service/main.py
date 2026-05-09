import os
from typing import Optional

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI(title="Product Service")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "product_db")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
products_collection = db["products"]


class ProductIn(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: Optional[str] = None
    tags: Optional[list[str]] = None


def serialize_product(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


@app.get("/health")
def health():
    return {"status": "ok", "service": "product-service"}


@app.post("/products")
def create_product(product: ProductIn):
    result = products_collection.insert_one(product.model_dump(exclude_none=True))
    doc = products_collection.find_one({"_id": result.inserted_id})
    return serialize_product(doc)


@app.get("/products")
def list_products(page: int = 1, limit: int = 12):
    """Paginated listing; defaults match storefront grid UX."""
    page = max(1, page)
    limit = min(max(1, limit), 100)
    skip = (page - 1) * limit
    cursor = products_collection.find().skip(skip).limit(limit)
    total = products_collection.count_documents({})
    items = [serialize_product(p) for p in cursor]
    return {"items": items, "total": total, "page": page, "limit": limit}


@app.get("/products/search")
def search_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = Query(
        None,
        description="Comma-separated tags; product must contain all listed tags",
    ),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
):
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            query["tags"] = {"$all": tag_list}
    if min_price is not None or max_price is not None:
        price = {}
        if min_price is not None:
            price["$gte"] = min_price
        if max_price is not None:
            price["$lte"] = max_price
        query["price"] = price
    return [serialize_product(p) for p in products_collection.find(query)]


@app.get("/products/{product_id}")
def get_product(product_id: str):
    try:
        oid = ObjectId(product_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid product id") from exc
    doc = products_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(doc)


@app.put("/products/{product_id}")
def update_product(product_id: str, product: ProductIn):
    try:
        oid = ObjectId(product_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid product id") from exc
    result = products_collection.update_one(
        {"_id": oid},
        {"$set": product.model_dump(exclude_none=True)},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = products_collection.find_one({"_id": oid})
    return serialize_product(doc)


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    try:
        oid = ObjectId(product_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid product id") from exc
    result = products_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"deleted": True}
