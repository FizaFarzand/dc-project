import os
from typing import Optional

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI(title="Product Service")

# ✅ CORS ADDED
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    result = products_collection.insert_one(product.model_dump())
    doc = products_collection.find_one({"_id": result.inserted_id})
    return serialize_product(doc)


@app.get("/products")
def list_products():
    return [serialize_product(p) for p in products_collection.find()]


@app.get("/products/{product_id}")
def get_product(product_id: str):
    try:
        oid = ObjectId(product_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid product id")

    doc = products_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(doc)


@app.put("/products/{product_id}")
def update_product(product_id: str, product: ProductIn):
    oid = ObjectId(product_id)
    products_collection.update_one({"_id": oid}, {"$set": product.model_dump()})
    doc = products_collection.find_one({"_id": oid})
    return serialize_product(doc)


@app.delete("/products/{product_id}")
def delete_product(product_id: str):
    oid = ObjectId(product_id)
    products_collection.delete_one({"_id": oid})
    return {"deleted": True}