from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.models.models import (
    ProductCategory, ProductStatus, PricingDirection,
    SuggestionStatus, TriggerReason
)


class ProductBase(BaseModel):
    sku: str
    name: str
    category: ProductCategory
    current_price: float = Field(gt=0, description="Current selling price, must be positive")
    stock_level: int = Field(ge=0, description="Available stock quantity, cannot be negative")
    reorder_threshold: int = Field(ge=0, description="Inventory reorder threshold")
    demand_velocity: int = Field(default=0, ge=0, description="Units ordered in the last 24 hours")
    status: ProductStatus = Field(default=ProductStatus.ACTIVE)
    cost_price: Optional[float] = Field(default=None, gt=0, description="Optional unit cost price")
    supplier_id: Optional[str] = Field(default=None, description="Optional supplier reference")


class ProductCreate(ProductBase):
    id: Optional[str] = Field(default=None, description="Unique product ID, e.g. PRD-001")


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[ProductCategory] = None
    current_price: Optional[float] = Field(default=None, gt=0)
    stock_level: Optional[int] = Field(default=None, ge=0)
    reorder_threshold: Optional[int] = Field(default=None, ge=0)
    demand_velocity: Optional[int] = Field(default=None, ge=0)
    status: Optional[ProductStatus] = None
    cost_price: Optional[float] = Field(default=None, gt=0)
    supplier_id: Optional[str] = None


class StockUpdate(BaseModel):
    stock_level: int = Field(ge=0, description="New stock level to set")


class ProductOut(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class OrderBase(BaseModel):
    product_id: str
    quantity: int = Field(default=1, gt=0, description="Order quantity must be at least 1")


class OrderCreate(OrderBase):
    pass


class OrderOut(OrderBase):
    order_id: int
    timestamp: datetime
    model_config = {"from_attributes": True}


class PricingSuggestionOut(BaseModel):
    id: int
    product_id: str
    current_price: float
    recommended_price: float
    direction: PricingDirection
    confidence: float
    reasoning: str
    status: SuggestionStatus
    trigger_reason: TriggerReason
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ReorderSuggestionOut(BaseModel):
    id: int
    product_id: str
    current_stock: int
    recommended_quantity: int
    suggested_lead_time_days: int
    confidence: float
    reasoning: str
    status: SuggestionStatus
    trigger_reason: TriggerReason
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class SuggestionStatusUpdate(BaseModel):
    status: SuggestionStatus

    @field_validator("status")
    @classmethod
    def validate_action(cls, v: SuggestionStatus) -> SuggestionStatus:
        if v not in (SuggestionStatus.ACCEPTED, SuggestionStatus.REJECTED):
            raise ValueError("Status update must be either ACCEPTED or REJECTED")
        return v


class PricingRecommendation(BaseModel):
    recommendedPrice: float = Field(gt=0, description="Recommended price must be positive")
    direction: PricingDirection
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence between 0 and 1")
    reasoning: str = Field(min_length=1, description="Explanation for recommendation")


class ReorderRecommendation(BaseModel):
    recommendedQuantity: int = Field(ge=1, description="Recommended quantity must be >= 1")
    suggested_lead_time_days: int = Field(default=5, ge=1)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence between 0 and 1")
    reasoning: str = Field(min_length=1, description="Explanation for recommendation")


class StrategyConfig(BaseModel):
    active_strategy: str = Field(description="'ai' or 'rule'")
    project_name: str
    llm_model: str


class StrategyConfigUpdate(BaseModel):
    active_strategy: str = Field(description="'ai' or 'rule'")

    @field_validator("active_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ("ai", "rule"):
            raise ValueError("active_strategy must be 'ai' or 'rule'")
        return v_clean


class PendingSuggestionsOut(BaseModel):
    pricing_suggestions: List[PricingSuggestionOut]
    reorder_suggestions: List[ReorderSuggestionOut]