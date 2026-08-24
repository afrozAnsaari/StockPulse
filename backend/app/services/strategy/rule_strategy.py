from app.models.models import Product, PricingDirection, TriggerReason
from app.schemas.schemas import PricingRecommendation, ReorderRecommendation
from app.services.strategy.base import PricingStrategy, ReorderStrategy, CommerceAdvisor


class RulePricingStrategy(PricingStrategy):
    """Deterministic, rule-based pricing recommendation strategy"""

    async def recommend(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> PricingRecommendation:
        current_price = product.current_price
        stock_level = product.stock_level
        reorder_threshold = product.reorder_threshold
        demand_velocity = product.demand_velocity

        # Rule 1: Stock is below reorder threshold -> 10% increase to preserve inventory
        if stock_level < reorder_threshold:
            recommended_price = round(current_price * 1.10, 2)
            direction = PricingDirection.INCREASE
            confidence = 0.85
            reasoning = (
                f"Rule Decision (Inventory Low): Current stock ({stock_level} units) is below safety "
                f"reorder threshold ({reorder_threshold} units). Applied +10% price protection to preserve "
                f"remaining inventory until restocking."
            )
        # Rule 2: Demand velocity is significantly higher than category benchmark -> 5% increase
        elif demand_velocity > (2.0 * category_avg_velocity):
            recommended_price = round(current_price * 1.05, 2)
            direction = PricingDirection.INCREASE
            confidence = 0.80
            reasoning = (
                f"Rule Decision (Demand Spike): Current demand velocity ({demand_velocity} orders/24h) "
                f"exceeds 2x category average ({category_avg_velocity:.1f} orders/24h). Applied +5% price "
                f"optimization to capture surge demand surplus."
            )
        # Rule 3: Steady state -> HOLD current price
        else:
            recommended_price = round(current_price, 2)
            direction = PricingDirection.HOLD
            confidence = 0.90
            reasoning = (
                f"Rule Decision (Hold): Stock level ({stock_level} units) and demand velocity "
                f"({demand_velocity} orders/24h) are stable within category benchmarks. Maintain current price of ${current_price:.2f}."
            )

        return PricingRecommendation(
            recommendedPrice=recommended_price,
            direction=direction,
            confidence=confidence,
            reasoning=reasoning
        )


class RuleReorderStrategy(ReorderStrategy):
    """Deterministic, rule-based inventory replenishment strategy"""

    async def recommend(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> ReorderRecommendation:
        threshold = product.reorder_threshold
        stock = product.stock_level
        target_inventory = threshold * 3
        raw_quantity = target_inventory - stock
        recommended_quantity = max(1, raw_quantity)
        lead_time_days = 5
        confidence = 0.85

        reasoning = (
            f"Rule Decision: Economic restocking formula (3 × threshold {threshold} = {target_inventory} units) "
            f"minus current stock ({stock} units) recommends ordering {recommended_quantity} units with standard "
            f"{lead_time_days}-day lead time."
        )

        return ReorderRecommendation(
            recommendedQuantity=recommended_quantity,
            suggested_lead_time_days=lead_time_days,
            confidence=confidence,
            reasoning=reasoning
        )


class RuleCommerceAdvisor(CommerceAdvisor):
    """Unified rule-based commerce advisor"""

    def __init__(self):
        self.pricing_strategy = RulePricingStrategy()
        self.reorder_strategy = RuleReorderStrategy()

    async def recommend_pricing(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> PricingRecommendation:
        return await self.pricing_strategy.recommend(product, category_avg_velocity, trigger_reason)

    async def recommend_reorder(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> ReorderRecommendation:
        return await self.reorder_strategy.recommend(product, category_avg_velocity, trigger_reason)
