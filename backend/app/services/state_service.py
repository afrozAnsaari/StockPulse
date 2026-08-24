from datetime import datetime, timezone
from sqlmodel import Session, select
from app.models.models import (
    Product, ProductStatus, PricingSuggestion, ReorderSuggestion,
    SuggestionStatus
)


def evaluate_and_update_product_status(session: Session, product: Product) -> Product:
    """
    Formal state machine evaluating product lifecycle status:
    1. Stock == 0 -> OUT_OF_STOCK
    2. Stock > 0 and has PENDING recommendations -> PRICE_REVIEW_PENDING
    3. Stock > 0 and no PENDING recommendations -> ACTIVE
    """
    if product.stock_level <= 0:
        product.stock_level = 0
        product.status = ProductStatus.OUT_OF_STOCK
    else:
        # Check if any PENDING pricing suggestions exist
        has_pending_pricing = session.exec(
            select(PricingSuggestion).where(
                PricingSuggestion.product_id == product.id,
                PricingSuggestion.status == SuggestionStatus.PENDING
            )
        ).first() is not None

        # Check if any PENDING reorder suggestions exist
        has_pending_reorder = session.exec(
            select(ReorderSuggestion).where(
                ReorderSuggestion.product_id == product.id,
                ReorderSuggestion.status == SuggestionStatus.PENDING
            )
        ).first() is not None

        if has_pending_pricing or has_pending_reorder:
            product.status = ProductStatus.PRICE_REVIEW_PENDING
        else:
            product.status = ProductStatus.ACTIVE

    product.updated_at = datetime.now(timezone.utc)
    session.add(product)
    return product
