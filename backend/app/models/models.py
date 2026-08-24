from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductCategory(str, Enum):
    ELECTRONICS = "ELECTRONICS"
    APPAREL = "APPAREL"
    HOME = "HOME"


class ProductStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PRICE_REVIEW_PENDING = "PRICE_REVIEW_PENDING"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class PricingDirection(str, Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    HOLD = "HOLD"


class SuggestionStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class TriggerReason(str, Enum):
    INITIAL = "INITIAL"
    INVENTORY_LOW = "INVENTORY_LOW"
    DEMAND_SPIKE = "DEMAND_SPIKE"
    MANUAL = "MANUAL"


class Product(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    sku: str = Field(index=True, unique=True)
    name: str
    category: ProductCategory
    current_price: float
    stock_level: int
    reorder_threshold: int
    demand_velocity: int = Field(default=0)
    status: ProductStatus = Field(default=ProductStatus.ACTIVE)
    cost_price: Optional[float] = Field(default=None, nullable=True)
    supplier_id: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class PricingSuggestion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(foreign_key="product.id", index=True)
    current_price: float
    recommended_price: float
    direction: PricingDirection
    confidence: float
    reasoning: str
    status: SuggestionStatus = Field(default=SuggestionStatus.PENDING)
    trigger_reason: TriggerReason = Field(default=TriggerReason.MANUAL)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReorderSuggestion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(foreign_key="product.id", index=True)
    current_stock: int
    recommended_quantity: int
    suggested_lead_time_days: int = Field(default=5)
    confidence: float
    reasoning: str
    status: SuggestionStatus = Field(default=SuggestionStatus.PENDING)
    trigger_reason: TriggerReason = Field(default=TriggerReason.MANUAL)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Order(SQLModel, table=True):
    order_id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(foreign_key="product.id", index=True)
    quantity: int = Field(default=1)
    timestamp: datetime = Field(default_factory=utc_now)