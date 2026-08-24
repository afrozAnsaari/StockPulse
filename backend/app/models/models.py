from datetime import datetime
from typing import Optional
from sqlmodel import Field, Relationship, SQLModel
from enum import Enum


class ProductCategory(str, Enum):
    ELECTRONICS = "ELECTRONICS"
    APPAREL = "APPAREL"
    HOME = "HOME"
    OTHER = "OTHER"


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PRICE_REVIEW_PENDING = "PRICE_REVIEW_PENDING"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class Product(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    sku: str
    name: str
    category: ProductCategory
    current_price: float
    stock_level: int
    reorder_threshold: int
    demand_velocity: int = Field(default=0)
    status: ProductStatus = Field(default=ProductStatus.ACTIVE)


class Order(SQLModel, table=True):
    order_id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(foreign_key="product.id")
    quantity: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)