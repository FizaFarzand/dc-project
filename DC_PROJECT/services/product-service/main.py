import os
from typing import Optional, List

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI(title="Product Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "dc_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["products"]


class Product(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: Optional[str] = None
    tags: Optional[List[str]] = None


def serialize(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc


@app.get("/health")
def health():
    return {"status": "ok", "service": "product-service"}


@app.post("/products")
def create(product: Product):
    result = collection.insert_one(product.model_dump())
    doc = collection.find_one({"_id": result.inserted_id})
    return serialize(doc)


@app.get("/products")
def get_products(
    page: int = Query(1),
    limit: int = Query(12),
):
    skip = (page - 1) * limit

    total = collection.count_documents({})

    items = [
        serialize(p)
        for p in collection.find().skip(skip).limit(limit)
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


@app.get("/products/search")
def search_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
):
    query = {}

    if q:
        query["name"] = {
            "$regex": q,
            "$options": "i"
        }

    if category:
        query["category"] = {
            "$regex": category,
            "$options": "i"
        }

    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

        query["tags"] = {
            "$in": tag_list
        }

    products = [
        serialize(p)
        for p in collection.find(query)
    ]

    return products


@app.get("/products/{product_id}")
def get_one(product_id: str):
    try:
        doc = collection.find_one({"_id": ObjectId(product_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    return serialize(doc)


@app.put("/products/{product_id}")
def update(product_id: str, product: Product):

    collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": product.model_dump()}
    )

    doc = collection.find_one({"_id": ObjectId(product_id)})

    return serialize(doc)


@app.delete("/products/{product_id}")
def delete(product_id: str):

    collection.delete_one({"_id": ObjectId(product_id)})

    return {"message": "deleted"}