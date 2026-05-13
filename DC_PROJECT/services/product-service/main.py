import os
from typing import Optional, List

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI(title="Product Service")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ENV
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "product_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["products"]

# ---------------- MODEL ----------------
class Product(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: Optional[str] = None
    tags: Optional[List[str]] = None

# ---------------- HELPERS ----------------
def serialize(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc

# ---------------- HEALTH ----------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "product-service"}

# ---------------- CREATE ----------------
@app.post("/products")
def create(product: Product):
    result = collection.insert_one(product.model_dump())
    doc = collection.find_one({"_id": result.inserted_id})
    return serialize(doc)

# ---------------- GET ALL ----------------
@app.get("/products")
def get_all():
    return [serialize(p) for p in collection.find()]

# ---------------- GET ONE ----------------
@app.get("/products/{product_id}")
def get_one(product_id: str):
    try:
        doc = collection.find_one({"_id": ObjectId(product_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    if not doc:
        raise HTTPException(status_code=404, detail="Not found")

    return serialize(doc)

# ---------------- UPDATE ----------------
@app.put("/products/{product_id}")
def update(product_id: str, product: Product):
    collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": product.model_dump()}
    )
    doc = collection.find_one({"_id": ObjectId(product_id)})
    return serialize(doc)

# ---------------- DELETE ----------------
@app.delete("/products/{product_id}")
def delete(product_id: str):
    collection.delete_one({"_id": ObjectId(product_id)})
    return {"message": "deleted"}