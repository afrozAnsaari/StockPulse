from abc import ABC, abstractmethod
from typing import Optional
from app.models.models import Product, TriggerReason
from app.schemas.schemas import PricingRecommendation, ReorderRecommendation


class PricingStrategy(ABC):
    """Abstract interface for pricing recommendations"""
    
    @abstractmethod
    async def recommend(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> PricingRecommendation:
        pass


class ReorderStrategy(ABC):
    """Abstract interface for inventory reorder recommendations"""
    
    @abstractmethod
    async def recommend(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> ReorderRecommendation:
        pass


class CommerceAdvisor(ABC):
    """Unified commerce advisor interface"""

    @abstractmethod
    async def recommend_pricing(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> PricingRecommendation:
        pass

    @abstractmethod
    async def recommend_reorder(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> ReorderRecommendation:
        pass
