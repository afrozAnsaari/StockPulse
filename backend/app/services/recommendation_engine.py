import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlmodel import Session, select, func
from app.core.db import engine
from app.models.models import (
    Product, ProductCategory, ProductStatus,
    PricingSuggestion, ReorderSuggestion,
    SuggestionStatus, TriggerReason
)
from app.services.strategy.manager import strategy_manager
from app.services.state_service import evaluate_and_update_product_status

logger = logging.getLogger("stockpulse.engine")


def get_category_average_velocity(session: Session, category: ProductCategory) -> float:
    """Calculate the average demand velocity for all products in a category"""
    statement = select(func.avg(Product.demand_velocity)).where(Product.category == category)
    avg_velocity = session.exec(statement).first()
    if avg_velocity is None or avg_velocity <= 0:
        return 1.0
    return float(avg_velocity)


def has_pending_pricing_suggestion(
    session: Session,
    product_id: str,
    trigger_reason: TriggerReason
) -> bool:
    """Idempotency check: returns True if an identical pending pricing suggestion exists"""
    statement = select(PricingSuggestion).where(
        PricingSuggestion.product_id == product_id,
        PricingSuggestion.trigger_reason == trigger_reason,
        PricingSuggestion.status == SuggestionStatus.PENDING
    )
    return session.exec(statement).first() is not None


def has_pending_reorder_suggestion(
    session: Session,
    product_id: str,
    trigger_reason: TriggerReason
) -> bool:
    """Idempotency check: returns True if an identical pending reorder suggestion exists"""
    statement = select(ReorderSuggestion).where(
        ReorderSuggestion.product_id == product_id,
        ReorderSuggestion.trigger_reason == trigger_reason,
        ReorderSuggestion.status == SuggestionStatus.PENDING
    )
    return session.exec(statement).first() is not None


async def process_async_recommendations(
    product_id: str,
    trigger_reason: TriggerReason
) -> None:
    """
    Background Task: Evaluates product, calculates category benchmarks,
    generates pricing & reorder recommendations with active strategy,
    persists suggestions idempotently, and transitions product status.
    """
    logger.info(f"Starting async recommendation loop for product={product_id}, trigger={trigger_reason.value}")
    
    with Session(engine) as session:
        product = session.get(Product, product_id)
        if not product:
            logger.warning(f"Product {product_id} not found during async recommendation processing")
            return

        category_avg_velocity = get_category_average_velocity(session, product.category)
        advisor = strategy_manager.get_advisor()

        # 1. Process Pricing Suggestion (Idempotency Check)
        if not has_pending_pricing_suggestion(session, product.id, trigger_reason):
            try:
                pricing_rec = await advisor.recommend_pricing(
                    product=product,
                    category_avg_velocity=category_avg_velocity,
                    trigger_reason=trigger_reason
                )

                pricing_sugg = PricingSuggestion(
                    product_id=product.id,
                    current_price=product.current_price,
                    recommended_price=pricing_rec.recommendedPrice,
                    direction=pricing_rec.direction,
                    confidence=pricing_rec.confidence,
                    reasoning=pricing_rec.reasoning,
                    status=SuggestionStatus.PENDING,
                    trigger_reason=trigger_reason,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(pricing_sugg)
                logger.info(f"Persisted PENDING pricing suggestion for {product.id} (${pricing_rec.recommendedPrice})")
            except Exception as e:
                logger.error(f"Error generating pricing suggestion for {product.id}: {e}", exc_info=True)
        else:
            logger.info(f"Skipping pricing suggestion for {product.id}: matching PENDING suggestion already exists")

        # 2. Process Reorder Suggestion (Idempotency Check)
        if not has_pending_reorder_suggestion(session, product.id, trigger_reason):
            try:
                reorder_rec = await advisor.recommend_reorder(
                    product=product,
                    category_avg_velocity=category_avg_velocity,
                    trigger_reason=trigger_reason
                )

                reorder_sugg = ReorderSuggestion(
                    product_id=product.id,
                    current_stock=product.stock_level,
                    recommended_quantity=reorder_rec.recommendedQuantity,
                    suggested_lead_time_days=reorder_rec.suggested_lead_time_days,
                    confidence=reorder_rec.confidence,
                    reasoning=reorder_rec.reasoning,
                    status=SuggestionStatus.PENDING,
                    trigger_reason=trigger_reason,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(reorder_sugg)
                logger.info(f"Persisted PENDING reorder suggestion for {product.id} ({reorder_rec.recommendedQuantity} units)")
            except Exception as e:
                logger.error(f"Error generating reorder suggestion for {product.id}: {e}", exc_info=True)
        else:
            logger.info(f"Skipping reorder suggestion for {product.id}: matching PENDING suggestion already exists")

        # 3. Update Product Lifecycle State
        evaluate_and_update_product_status(session, product)
        session.commit()
        logger.info(f"Completed async recommendation loop for product={product_id}. Status is now {product.status.value}")
