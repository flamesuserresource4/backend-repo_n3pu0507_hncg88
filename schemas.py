from pydantic import BaseModel, Field
from typing import Optional, List

# ZenSupply Schemas

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in USD")
    category: str = Field(..., description="Category, e.g., Spawners, Money")
    image: Optional[str] = Field(None, description="Image URL or path")
    badge: Optional[str] = Field(None, description="Small label like 'Popular'")
    in_stock: bool = Field(True, description="Whether product is available")
    # Optional variants stored with product documents (when applicable)
    # Each variant: { id, label, unit_price? , bundle_qty?, bundle_price? }

class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = Field(ge=1)
    variant_id: Optional[str] = None
    variant_label: Optional[str] = None

class Order(BaseModel):
    minecraft_username: str
    discord: Optional[str] = None
    email: Optional[str] = None
    items: List[OrderItem]
    total_amount: float = 0
    status: str = "pending"
    notes: Optional[str] = None

class Feedback(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Star rating 1-5")
    comment: Optional[str] = Field(None, description="Optional feedback text")
    minecraft_username: Optional[str] = Field(None, description="IGN if provided")
