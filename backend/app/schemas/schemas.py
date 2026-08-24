from typing import Optional
from datetime import datetime
from sqlmodel import Field
from pydantic import BaseModel
from app.models.models import ProductCategory, ProductStatus


class ProductBase(BaseModel):
    sku: str
    name: str
    category: ProductCategory
    current_price: float
    stock_level: int
    reorder_threshold: int
    demand_velocity: int = 0
    status: ProductStatus = ProductStatus.ACTIVE


class ProductCreate(ProductBase):
    id: str


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[ProductCategory] = None
    current_price: Optional[float] = None
    stock_level: Optional[int] = None
    reorder_threshold: Optional[int] = None
    demand_velocity: Optional[int] = None
    status: Optional[ProductStatus] = None


class ProductOut(ProductBase):
    id: str
    model_config = {"from_attributes": True}


class OrderBase(BaseModel):
    product_id: str
    quantity: int


class OrderCreate(OrderBase):
    pass


class OrderOut(OrderBase):
    order_id: int
    timestamp: datetime
    model_config = {"from_attributes": True}


# LLM Response Models
class PricingRecommendation(BaseModel):
    recommendedPrice: float
    direction: str  # INCREASE, DECREASE, MAINTAIN
    confidence: float
    reasoning: str


class ReorderRecommendation(BaseModel):
    recommendedQuantity: int
    confidence: float
    reasoning: str