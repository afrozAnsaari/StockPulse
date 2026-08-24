import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlmodel import Session, select
from app.models.models import (
    Product, ProductCategory, ProductStatus,
    PricingSuggestion, ReorderSuggestion, Order,
    PricingDirection, SuggestionStatus, TriggerReason
)
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, StockUpdate,
    PricingRecommendation, ReorderRecommendation
)
from app.services.state_service import evaluate_and_update_product_status

logger = logging.getLogger("stockpulse.crud")


def get_product(session: Session, product_id: str) -> Optional[Product]:
    return session.get(Product, product_id)


def get_products(
    session: Session,
    status: Optional[ProductStatus] = None,
    category: Optional[ProductCategory] = None
) -> List[Product]:
    statement = select(Product)
    if status:
        statement = statement.where(Product.status == status)
    if category:
        statement = statement.where(Product.category == category)
    statement = statement.order_by(Product.id)
    return session.exec(statement).all()


def create_product(session: Session, product_in: ProductCreate) -> Product:
    if not product_in.id:
        # Generate ID if not provided
        count = len(session.exec(select(Product)).all()) + 1
        product_id = f"PRD-{count:03d}"
    else:
        product_id = product_in.id

    db_product = Product(
        id=product_id,
        sku=product_in.sku,
        name=product_in.name,
        category=product_in.category,
        current_price=product_in.current_price,
        stock_level=product_in.stock_level,
        reorder_threshold=product_in.reorder_threshold,
        demand_velocity=product_in.demand_velocity,
        status=product_in.status,
        cost_price=product_in.cost_price,
        supplier_id=product_in.supplier_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    evaluate_and_update_product_status(session, db_product)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


def update_product(session: Session, product_id: str, product_update: ProductUpdate) -> Optional[Product]:
    db_product = session.get(Product, product_id)
    if not db_product:
        return None

    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    evaluate_and_update_product_status(session, db_product)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


def delete_product(session: Session, product_id: str) -> bool:
    db_product = session.get(Product, product_id)
    if not db_product:
        return False
    session.delete(db_product)
    session.commit()
    return True


def update_product_stock(
    session: Session,
    product_id: str,
    new_stock: int
) -> Tuple[Optional[Product], Optional[TriggerReason]]:
    """Update stock level and determine if an INVENTORY_LOW trigger is tripped"""
    db_product = session.get(Product, product_id)
    if not db_product:
        return None, None

    if new_stock < 0:
        raise ValueError("Stock level cannot be negative")

    db_product.stock_level = new_stock
    trigger_reason = None

    if db_product.stock_level == 0:
        db_product.status = ProductStatus.OUT_OF_STOCK
        trigger_reason = TriggerReason.INVENTORY_LOW
    elif db_product.stock_level < db_product.reorder_threshold:
        trigger_reason = TriggerReason.INVENTORY_LOW

    evaluate_and_update_product_status(session, db_product)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product, trigger_reason


def create_order_transaction(
    session: Session,
    product_id: str,
    quantity: int,
    category_avg_velocity: float,
    demand_spike_multiplier: float = 3.0
) -> Tuple[Order, Product, Optional[TriggerReason]]:
    """
    Atomic transaction:
    1. Validates product existence and stock availability
    2. Decrements stock and increments demand velocity
    3. Records Order
    4. Evaluates triggers (INVENTORY_LOW or DEMAND_SPIKE)
    """
    db_product = session.get(Product, product_id)
    if not db_product:
        raise ValueError("Product not found")

    if quantity <= 0:
        raise ValueError("Order quantity must be positive")

    if db_product.stock_level < quantity:
        raise ValueError(
            f"Insufficient stock: requested {quantity} units but only {db_product.stock_level} available"
        )

    # Decrement stock and increment demand velocity
    db_product.stock_level -= quantity
    db_product.demand_velocity += quantity

    # Create Order record
    order = Order(
        product_id=product_id,
        quantity=quantity,
        timestamp=datetime.now(timezone.utc)
    )
    session.add(order)

    # Evaluate business triggers
    trigger_reason: Optional[TriggerReason] = None
    if db_product.stock_level < db_product.reorder_threshold:
        trigger_reason = TriggerReason.INVENTORY_LOW
    elif db_product.demand_velocity > (demand_spike_multiplier * category_avg_velocity):
        trigger_reason = TriggerReason.DEMAND_SPIKE

    evaluate_and_update_product_status(session, db_product)
    session.add(db_product)
    session.commit()
    session.refresh(order)
    session.refresh(db_product)

    return order, db_product, trigger_reason


def get_orders_for_product(session: Session, product_id: str) -> List[Order]:
    statement = select(Order).where(Order.product_id == product_id).order_by(Order.timestamp.desc())
    return session.exec(statement).all()


def get_pricing_suggestions(
    session: Session,
    product_id: Optional[str] = None,
    status: Optional[SuggestionStatus] = None
) -> List[PricingSuggestion]:
    statement = select(PricingSuggestion)
    if product_id:
        statement = statement.where(PricingSuggestion.product_id == product_id)
    if status:
        statement = statement.where(PricingSuggestion.status == status)
    statement = statement.order_by(PricingSuggestion.created_at.desc())
    return session.exec(statement).all()


def get_reorder_suggestions(
    session: Session,
    product_id: Optional[str] = None,
    status: Optional[SuggestionStatus] = None
) -> List[ReorderSuggestion]:
    statement = select(ReorderSuggestion)
    if product_id:
        statement = statement.where(ReorderSuggestion.product_id == product_id)
    if status:
        statement = statement.where(ReorderSuggestion.status == status)
    statement = statement.order_by(ReorderSuggestion.created_at.desc())
    return session.exec(statement).all()


def get_all_pending_suggestions(
    session: Session
) -> Tuple[List[PricingSuggestion], List[ReorderSuggestion]]:
    pricing = session.exec(
        select(PricingSuggestion).where(PricingSuggestion.status == SuggestionStatus.PENDING)
        .order_by(PricingSuggestion.created_at.desc())
    ).all()
    reorder = session.exec(
        select(ReorderSuggestion).where(ReorderSuggestion.status == SuggestionStatus.PENDING)
        .order_by(ReorderSuggestion.created_at.desc())
    ).all()
    return pricing, reorder


def accept_pricing_suggestion(
    session: Session,
    suggestion_id: int
) -> Tuple[PricingSuggestion, Product]:
    """Atomically accept pricing suggestion, update Product.current_price, and transition lifecycle"""
    sugg = session.get(PricingSuggestion, suggestion_id)
    if not sugg:
        raise ValueError("Pricing suggestion not found")
    if sugg.status != SuggestionStatus.PENDING:
        raise ValueError(f"Suggestion has already been {sugg.status.value.lower()}")

    product = session.get(Product, sugg.product_id)
    if not product:
        raise ValueError("Associated product not found")

    # Atomic price mutation
    product.current_price = sugg.recommended_price
    sugg.status = SuggestionStatus.ACCEPTED
    sugg.updated_at = datetime.now(timezone.utc)

    session.add(sugg)
    evaluate_and_update_product_status(session, product)
    session.add(product)
    session.commit()
    session.refresh(sugg)
    session.refresh(product)
    return sugg, product


def reject_pricing_suggestion(
    session: Session,
    suggestion_id: int
) -> Tuple[PricingSuggestion, Product]:
    """Reject pricing suggestion and transition product lifecycle"""
    sugg = session.get(PricingSuggestion, suggestion_id)
    if not sugg:
        raise ValueError("Pricing suggestion not found")
    if sugg.status != SuggestionStatus.PENDING:
        raise ValueError(f"Suggestion has already been {sugg.status.value.lower()}")

    product = session.get(Product, sugg.product_id)
    if not product:
        raise ValueError("Associated product not found")

    sugg.status = SuggestionStatus.REJECTED
    sugg.updated_at = datetime.now(timezone.utc)

    session.add(sugg)
    evaluate_and_update_product_status(session, product)
    session.add(product)
    session.commit()
    session.refresh(sugg)
    session.refresh(product)
    return sugg, product


def accept_reorder_suggestion(
    session: Session,
    suggestion_id: int
) -> Tuple[ReorderSuggestion, Product]:
    """Atomically accept reorder suggestion (simulated inbound shipment) and update stock"""
    sugg = session.get(ReorderSuggestion, suggestion_id)
    if not sugg:
        raise ValueError("Reorder suggestion not found")
    if sugg.status != SuggestionStatus.PENDING:
        raise ValueError(f"Suggestion has already been {sugg.status.value.lower()}")

    product = session.get(Product, sugg.product_id)
    if not product:
        raise ValueError("Associated product not found")

    # Atomic stock increase simulating inbound shipment
    product.stock_level += sugg.recommended_quantity
    sugg.status = SuggestionStatus.ACCEPTED
    sugg.updated_at = datetime.now(timezone.utc)

    session.add(sugg)
    evaluate_and_update_product_status(session, product)
    session.add(product)
    session.commit()
    session.refresh(sugg)
    session.refresh(product)
    return sugg, product


def reject_reorder_suggestion(
    session: Session,
    suggestion_id: int
) -> Tuple[ReorderSuggestion, Product]:
    """Reject reorder suggestion and update product state"""
    sugg = session.get(ReorderSuggestion, suggestion_id)
    if not sugg:
        raise ValueError("Reorder suggestion not found")
    if sugg.status != SuggestionStatus.PENDING:
        raise ValueError(f"Suggestion has already been {sugg.status.value.lower()}")

    product = session.get(Product, sugg.product_id)
    if not product:
        raise ValueError("Associated product not found")

    sugg.status = SuggestionStatus.REJECTED
    sugg.updated_at = datetime.now(timezone.utc)

    session.add(sugg)
    evaluate_and_update_product_status(session, product)
    session.add(product)
    session.commit()
    session.refresh(sugg)
    session.refresh(product)
    return sugg, product