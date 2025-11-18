import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime

from database import db, create_document, get_documents

app = FastAPI(title="ZenSupply API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# Pydantic request models
# ---------------------------
class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = Field(ge=1)
    variant_id: Optional[str] = None
    variant_label: Optional[str] = None

class CreateOrderRequest(BaseModel):
    minecraft_username: str = Field(..., description="In-game name")
    discord: Optional[str] = Field(None, description="Discord handle")
    email: Optional[str] = Field(None, description="Email for receipt")
    items: List[OrderItem]
    notes: Optional[str] = None


# ---------------------------
# Utility
# ---------------------------
WANTED_TITLES = ["Skeleton Spawner", "Money", "Elytra"]

DEFAULT_PRODUCTS = [
    {
        "title": "Skeleton Spawner",
        "description": "Placeable spawner for efficient bone and arrow farms.",
        "price": 14.99,
        "category": "Spawners",
        "image": "/assets/skeleton-spawner.png",
        "badge": "Popular",
        "in_stock": True,
        # Variants: single unit or full shulker bundle
        "variants": [
            {"id": "single", "label": "Single", "unit_price": 14.99},
            {"id": "shulker", "label": "Shulker (27x)", "bundle_qty": 27, "bundle_price": 349.99},
        ],
    },
    {
        "title": "Money",
        "description": "In-game currency to boost your balance.",
        "price": 9.99,
        "category": "Money",
        "image": "/assets/money-5m.png",
        "badge": "Best value",
        "in_stock": True,
    },
    {
        "title": "Elytra",
        "description": "Soar across the map with a pristine Elytra.",
        "price": 19.99,
        "category": "Gear",
        "image": "/assets/elytra.png",
        "badge": None,
        "in_stock": True,
    },
]


def ensure_seed_products():
    if db is None:
        return
    try:
        # Ensure each wanted product exists; insert if missing
        titles_in_db = set(p.get("title") for p in db.product.find({}, {"title": 1}))
        for prod in DEFAULT_PRODUCTS:
            if prod["title"] not in titles_in_db:
                create_document("product", prod)
    except Exception:
        pass


# ---------------------------
# Routes
# ---------------------------
@app.get("/")
def read_root():
    return {"message": "ZenSupply Backend Running"}


@app.get("/products")
def list_products():
    ensure_seed_products()
    try:
        products = list(db.product.find({"title": {"$in": WANTED_TITLES}})) if db is not None else []
        # Convert ObjectId to string
        for p in products:
            if "_id" in p:
                p["id"] = str(p.pop("_id"))
        return {"items": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orders")
def create_order(payload: CreateOrderRequest):
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items in order")

    total = sum(i.price * i.quantity for i in payload.items)
    order_doc = {
        "minecraft_username": payload.minecraft_username,
        "discord": payload.discord,
        "email": payload.email,
        "items": [i.model_dump() for i in payload.items],
        "total_amount": round(total, 2),
        "status": "pending",
        "notes": payload.notes,
        "created_at": datetime.utcnow(),
    }
    try:
        order_id = create_document("order", order_doc)
        return {"order_id": order_id, "status": "received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
