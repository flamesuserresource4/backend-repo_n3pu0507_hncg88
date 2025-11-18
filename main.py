import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime

from database import db, create_document, get_documents

app = FastAPI(title="ZenSupply API", version="1.0.0")

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

class CreateOrderRequest(BaseModel):
    minecraft_username: str = Field(..., description="In-game name")
    discord: Optional[str] = Field(None, description="Discord handle")
    email: Optional[str] = Field(None, description="Email for receipt")
    items: List[OrderItem]
    notes: Optional[str] = None


# ---------------------------
# Utility
# ---------------------------
DEFAULT_PRODUCTS = [
    {
        "title": "Skeleton Spawner",
        "description": "Placeable spawner for efficient bone and arrow farms.",
        "price": 14.99,
        "category": "Spawners",
        "image": "/assets/skeleton-spawner.png",
        "badge": "Popular",
    },
    {
        "title": "Money • 5M",
        "description": "Instantly boost your balance with 5 million in-game cash.",
        "price": 9.99,
        "category": "Money",
        "image": "/assets/money-5m.png",
        "badge": "Best value",
    },
    {
        "title": "Money • 10M",
        "description": "Big bankroll: ten million to dominate the economy.",
        "price": 17.99,
        "category": "Money",
        "image": "/assets/money-10m.png",
        "badge": None,
    },
    {
        "title": "Mob Coin Bundle",
        "description": "1,000 mob coins for special upgrades and perks.",
        "price": 7.99,
        "category": "Currency",
        "image": "/assets/mob-coins.png",
        "badge": None,
    },
]


def ensure_seed_products():
    if db is None:
        return
    try:
        existing = list(db.product.find().limit(1))
        if not existing:
            for p in DEFAULT_PRODUCTS:
                create_document("product", {
                    "title": p["title"],
                    "description": p["description"],
                    "price": p["price"],
                    "category": p["category"],
                    "image": p.get("image"),
                    "badge": p.get("badge"),
                    "in_stock": True,
                })
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
        products = get_documents("product", {})
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
