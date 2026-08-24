import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query, status
from sqlmodel import Session

from app.core.db import get_session
from app.core.config import settings
from app.models.models import (
    Product, ProductCategory, ProductStatus,
    PricingSuggestion, ReorderSuggestion,
    PricingDirection, SuggestionStatus, TriggerReason
)
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductOut, StockUpdate,
    OrderCreate, OrderOut,
    PricingSuggestionOut, ReorderSuggestionOut,
    PendingSuggestionsOut, SuggestionStatusUpdate,
    StrategyConfig, StrategyConfigUpdate, HealthResponse
)
from app.core.crud import (
    get_product, get_products, create_product, update_product,
    delete_product, update_product_stock, create_order_transaction,
    get_orders_for_product, get_pricing_suggestions, get_reorder_suggestions,
    get_all_pending_suggestions, accept_pricing_suggestion,
    reject_pricing_suggestion, accept_reorder_suggestion, reject_reorder_suggestion
)
from app.services.strategy.manager import strategy_manager
from app.services.recommendation_engine import (
    process_async_recommendations,
    get_category_average_velocity
)
from app.services.state_service import evaluate_and_update_product_status

logger = logging.getLogger("stockpulse.routes")

router = APIRouter()


# ==========================================
# System Health & Strategy Configuration
# ==========================================

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check & strategy status"
)
def health_check(session: Session = Depends(get_session)):
    """System health check endpoint verifying database connectivity and active strategy"""
    try:
        # Simple DB probe
        get_products(session)
        db_status = "connected"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return HealthResponse(
        status="ok",
        database=db_status,
        active_strategy=strategy_manager.active_strategy,
        timestamp=datetime.now(timezone.utc)
    )


@router.get(
    "/config/strategy",
    response_model=StrategyConfig,
    tags=["Configuration"],
    summary="Get active commerce strategy configuration"
)
def get_strategy_config():
    """Returns currently active commerce strategy, model parameters, and guardrail multipliers"""
    return StrategyConfig(
        active_strategy=strategy_manager.active_strategy,
        project_name=settings.PROJECT_NAME,
        llm_model=settings.LLM_MODEL,
        llm_base_url=settings.LLM_BASE_URL,
        demand_spike_multiplier=settings.DEMAND_SPIKE_MULTIPLIER,
        price_max_multiplier=settings.PRICE_MAX_MULTIPLIER,
        price_min_multiplier=settings.PRICE_MIN_MULTIPLIER
    )


@router.patch(
    "/config/strategy",
    response_model=StrategyConfig,
    tags=["Configuration"],
    summary="Switch active commerce strategy at runtime"
)
def update_strategy_config(config_update: StrategyConfigUpdate):
    """Switch active commerce strategy between 'ai' and 'rule' at runtime without application restart"""
    try:
        strategy_manager.set_active_strategy(config_update.active_strategy)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return get_strategy_config()


# ==========================================
# Products API
# ==========================================

@router.get(
    "/products",
    response_model=List[ProductOut],
    tags=["Products"],
    summary="List and filter catalog products"
)
def list_products(
    status_filter: Optional[ProductStatus] = Query(None, alias="status", description="Filter by status"),
    category_filter: Optional[ProductCategory] = Query(None, alias="category", description="Filter by category"),
    session: Session = Depends(get_session)
):
    """List all products in the catalog with optional status and category filters"""
    return get_products(session, status=status_filter, category=category_filter)


@router.post(
    "/products",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Products"],
    summary="Create a new product"
)
def create_new_product(
    product_in: ProductCreate,
    session: Session = Depends(get_session)
):
    """Create a new catalog product with validated pricing and inventory fields"""
    # Check for duplicate SKU
    existing = session.query(Product).filter(Product.sku == product_in.sku).first() if hasattr(session, "query") else None
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Product with SKU '{product_in.sku}' already exists")
    
    return create_product(session, product_in)


@router.get(
    "/products/{product_id}",
    response_model=ProductOut,
    tags=["Products"],
    summary="Get product by ID"
)
def get_product_details(
    product_id: str,
    session: Session = Depends(get_session)
):
    """Retrieve full product details including live stock and pricing"""
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found")
    return product


@router.patch(
    "/products/{product_id}/stock",
    response_model=ProductOut,
    tags=["Products"],
    summary="Update product stock level"
)
def update_stock_level(
    product_id: str,
    stock_in: StockUpdate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Directly update product stock level.
    If new stock falls below reorder threshold or hits 0, asynchronously triggers recommendation loop.
    Returns immediately without blocking for LLM completion.
    """
    try:
        product, trigger = update_product_stock(session, product_id, stock_in.stock_level)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found")

    if trigger:
        background_tasks.add_task(process_async_recommendations, product_id, trigger)

    return product


# ==========================================
# Orders & Sales Simulation
# ==========================================

@router.post(
    "/products/{product_id}/orders",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Orders"],
    summary="Simulate a sale / place an order"
)
def simulate_sale_order(
    product_id: str,
    order_in: OrderCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    Simulate an order / sale.
    Atomically decrements stock, records order, updates demand velocity, evaluates triggers,
    and returns immediately while dispatching asynchronous recommendation tasks.
    """
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found")

    category_avg = get_category_average_velocity(session, product.category)

    try:
        order, updated_product, trigger = create_order_transaction(
            session=session,
            product_id=product_id,
            quantity=order_in.quantity,
            category_avg_velocity=category_avg,
            demand_spike_multiplier=settings.DEMAND_SPIKE_MULTIPLIER
        )
    except ValueError as e:
        err_msg = str(e)
        if "Insufficient stock" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    if trigger:
        background_tasks.add_task(process_async_recommendations, product_id, trigger)

    return order


# ==========================================
# Recommendations & Suggestions API
# ==========================================

@router.post(
    "/products/{product_id}/suggest-pricing",
    response_model=PricingSuggestionOut,
    tags=["Recommendations"],
    summary="Generate on-demand pricing recommendation"
)
async def generate_manual_pricing_suggestion(
    product_id: str,
    session: Session = Depends(get_session)
):
    """Generate and persist an on-demand pricing suggestion using the active strategy (trigger: MANUAL)"""
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found")

    category_avg = get_category_average_velocity(session, product.category)
    advisor = strategy_manager.get_advisor()

    pricing_rec = await advisor.recommend_pricing(
        product=product,
        category_avg_velocity=category_avg,
        trigger_reason=TriggerReason.MANUAL
    )

    sugg = PricingSuggestion(
        product_id=product.id,
        current_price=product.current_price,
        recommended_price=pricing_rec.recommendedPrice,
        direction=pricing_rec.direction,
        confidence=pricing_rec.confidence,
        reasoning=pricing_rec.reasoning,
        status=SuggestionStatus.PENDING,
        trigger_reason=TriggerReason.MANUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(sugg)
    evaluate_and_update_product_status(session, product)
    session.commit()
    session.refresh(sugg)

    return sugg


@router.post(
    "/products/{product_id}/suggest-reorder",
    response_model=ReorderSuggestionOut,
    tags=["Recommendations"],
    summary="Generate on-demand reorder recommendation"
)
async def generate_manual_reorder_suggestion(
    product_id: str,
    session: Session = Depends(get_session)
):
    """Generate and persist an on-demand reorder suggestion using the active strategy (trigger: MANUAL)"""
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found")

    category_avg = get_category_average_velocity(session, product.category)
    advisor = strategy_manager.get_advisor()

    reorder_rec = await advisor.recommend_reorder(
        product=product,
        category_avg_velocity=category_avg,
        trigger_reason=TriggerReason.MANUAL
    )

    sugg = ReorderSuggestion(
        product_id=product.id,
        current_stock=product.stock_level,
        recommended_quantity=reorder_rec.recommendedQuantity,
        suggested_lead_time_days=reorder_rec.suggested_lead_time_days,
        confidence=reorder_rec.confidence,
        reasoning=reorder_rec.reasoning,
        status=SuggestionStatus.PENDING,
        trigger_reason=TriggerReason.MANUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    session.add(sugg)
    evaluate_and_update_product_status(session, product)
    session.commit()
    session.refresh(sugg)

    return sugg


@router.get(
    "/products/{product_id}/pricing-suggestions",
    response_model=List[PricingSuggestionOut],
    tags=["Recommendations"],
    summary="Get pricing suggestions for a product"
)
def list_product_pricing_suggestions(
    product_id: str,
    session: Session = Depends(get_session)
):
    """List all pricing recommendations for a specific product"""
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found")
    return get_pricing_suggestions(session, product_id=product_id)


@router.get(
    "/products/{product_id}/reorder-suggestions",
    response_model=List[ReorderSuggestionOut],
    tags=["Recommendations"],
    summary="Get reorder suggestions for a product"
)
def list_product_reorder_suggestions(
    product_id: str,
    session: Session = Depends(get_session)
):
    """List all reorder recommendations for a specific product"""
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product '{product_id}' not found")
    return get_reorder_suggestions(session, product_id=product_id)


@router.get(
    "/suggestions/pending",
    response_model=PendingSuggestionsOut,
    tags=["Recommendations"],
    summary="Get all pending suggestions"
)
def get_pending_suggestions_queue(
    session: Session = Depends(get_session)
):
    """Fetch all pending pricing and reorder suggestions across the catalog for the merchandiser review queue"""
    pricing, reorder = get_all_pending_suggestions(session)
    return PendingSuggestionsOut(
        pricing_suggestions=pricing,
        reorder_suggestions=reorder
    )


# ==========================================
# Human Checkpoint: Accept / Reject Actions
# ==========================================

@router.patch(
    "/pricing-suggestions/{suggestion_id}",
    response_model=PricingSuggestionOut,
    tags=["Human Checkpoint"],
    summary="Accept or reject a pricing suggestion"
)
def update_pricing_suggestion_status(
    suggestion_id: int,
    action: SuggestionStatusUpdate,
    session: Session = Depends(get_session)
):
    """
    Accept or reject a pending pricing recommendation.
    If ACCEPTED: atomically updates Product.current_price to recommended price.
    Transitions product review state.
    """
    try:
        if action.status == SuggestionStatus.ACCEPTED:
            sugg, _ = accept_pricing_suggestion(session, suggestion_id)
        else:
            sugg, _ = reject_pricing_suggestion(session, suggestion_id)
        return sugg
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/reorder-suggestions/{suggestion_id}",
    response_model=ReorderSuggestionOut,
    tags=["Human Checkpoint"],
    summary="Accept or reject a reorder suggestion"
)
def update_reorder_suggestion_status(
    suggestion_id: int,
    action: SuggestionStatusUpdate,
    session: Session = Depends(get_session)
):
    """
    Accept or reject a pending reorder recommendation.
    If ACCEPTED: atomically increments Product.stock_level by recommended_quantity (simulated inbound shipment).
    Transitions product review state.
    """
    try:
        if action.status == SuggestionStatus.ACCEPTED:
            sugg, _ = accept_reorder_suggestion(session, suggestion_id)
        else:
            sugg, _ = reject_reorder_suggestion(session, suggestion_id)
        return sugg
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))