import logging
from typing import Optional
from app.models.models import Product, TriggerReason
from app.schemas.schemas import PricingRecommendation, ReorderRecommendation
from app.services.strategy.base import PricingStrategy, ReorderStrategy, CommerceAdvisor
from app.services.strategy.rule_strategy import RulePricingStrategy, RuleReorderStrategy
from app.services.ai.client import LLMClient, default_llm_client, LLMClientError
from app.services.ai.parser import (
    parse_and_validate_pricing,
    parse_and_validate_reorder,
    AIValidationError
)
from app.services.ai.prompts import (
    SYSTEM_PROMPT,
    build_inventory_low_pricing_prompt,
    build_inventory_low_reorder_prompt,
    build_demand_spike_pricing_prompt,
    build_demand_spike_reorder_prompt,
    build_generic_pricing_prompt,
    build_generic_reorder_prompt
)

logger = logging.getLogger("stockpulse.ai_strategy")


class AIPricingStrategy(PricingStrategy):
    """AI-powered pricing strategy with automatic rule-based fallback"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        rule_fallback: Optional[RulePricingStrategy] = None
    ):
        self.llm_client = llm_client or default_llm_client
        self.rule_fallback = rule_fallback or RulePricingStrategy()

    async def recommend(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> PricingRecommendation:
        # Select trigger-specific prompt
        if trigger_reason == TriggerReason.INVENTORY_LOW:
            user_prompt = build_inventory_low_pricing_prompt(product, category_avg_velocity)
        elif trigger_reason == TriggerReason.DEMAND_SPIKE:
            user_prompt = build_demand_spike_pricing_prompt(product, category_avg_velocity)
        else:
            user_prompt = build_generic_pricing_prompt(product, category_avg_velocity, trigger_reason)

        try:
            raw_response = await self.llm_client.generate(SYSTEM_PROMPT, user_prompt)
            recommendation = parse_and_validate_pricing(raw_response, product.current_price)
            logger.info(
                f"Successfully generated AI pricing recommendation for {product.id}: "
                f"${recommendation.recommendedPrice} ({recommendation.direction.value})"
            )
            return recommendation

        except (LLMClientError, AIValidationError, Exception) as e:
            logger.warning(
                f"AI pricing generation failed for {product.id} ({type(e).__name__}: {e}). "
                f"Gracefully falling back to deterministic rule strategy."
            )
            fallback_rec = await self.rule_fallback.recommend(
                product, category_avg_velocity, trigger_reason
            )
            # Add fallback context to reasoning
            fallback_rec.reasoning = f"{fallback_rec.reasoning} [AI Fallback Applied: {type(e).__name__}]"
            return fallback_rec


class AIReorderStrategy(ReorderStrategy):
    """AI-powered inventory reorder strategy with automatic rule-based fallback"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        rule_fallback: Optional[RuleReorderStrategy] = None
    ):
        self.llm_client = llm_client or default_llm_client
        self.rule_fallback = rule_fallback or RuleReorderStrategy()

    async def recommend(
        self,
        product: Product,
        category_avg_velocity: float,
        trigger_reason: TriggerReason
    ) -> ReorderRecommendation:
        # Select trigger-specific prompt
        if trigger_reason == TriggerReason.INVENTORY_LOW:
            user_prompt = build_inventory_low_reorder_prompt(product, category_avg_velocity)
        elif trigger_reason == TriggerReason.DEMAND_SPIKE:
            user_prompt = build_demand_spike_reorder_prompt(product, category_avg_velocity)
        else:
            user_prompt = build_generic_reorder_prompt(product, category_avg_velocity, trigger_reason)

        try:
            raw_response = await self.llm_client.generate(SYSTEM_PROMPT, user_prompt)
            recommendation = parse_and_validate_reorder(raw_response)
            logger.info(
                f"Successfully generated AI reorder recommendation for {product.id}: "
                f"{recommendation.recommendedQuantity} units (confidence: {recommendation.confidence:.2f})"
            )
            return recommendation

        except (LLMClientError, AIValidationError, Exception) as e:
            logger.warning(
                f"AI reorder generation failed for {product.id} ({type(e).__name__}: {e}). "
                f"Gracefully falling back to deterministic rule strategy."
            )
            fallback_rec = await self.rule_fallback.recommend(
                product, category_avg_velocity, trigger_reason
            )
            fallback_rec.reasoning = f"{fallback_rec.reasoning} [AI Fallback Applied: {type(e).__name__}]"
            return fallback_rec


class AICommerceAdvisor(CommerceAdvisor):
    """Unified AI-powered commerce advisor with automatic rule fallback"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        rule_pricing: Optional[RulePricingStrategy] = None,
        rule_reorder: Optional[RuleReorderStrategy] = None
    ):
        self.pricing_strategy = AIPricingStrategy(llm_client, rule_pricing)
        self.reorder_strategy = AIReorderStrategy(llm_client, rule_reorder)

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
