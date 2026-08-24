from sqlmodel import Session
from sqlalchemy import text
from app.models.models import (
    Product, ProductCategory, ProductStatus,
    PricingSuggestion, ReorderSuggestion, PricingDirection,
    SuggestionStatus, TriggerReason, Order
)
from app.core.db import engine, init_db, reset_db


def seed_database(reset: bool = True):
    """Seed the database with exact initial product and suggestion data"""
    if reset:
        reset_db()
    else:
        init_db()
    with Session(engine) as session:

        # Exact products from problem specification
        products = [
            Product(
                id="PRD-001",
                sku="SKU-ELEC-001",
                name="Wireless Earbuds Pro",
                category=ProductCategory.ELECTRONICS,
                current_price=79.99,
                stock_level=45,
                reorder_threshold=20,
                demand_velocity=3,
                status=ProductStatus.ACTIVE,
                cost_price=45.00,
                supplier_id="SUP-ELEC-01"
            ),
            Product(
                id="PRD-002",
                sku="SKU-ELEC-002",
                name="USB-C Hub 7-Port",
                category=ProductCategory.ELECTRONICS,
                current_price=34.99,
                stock_level=120,
                reorder_threshold=30,
                demand_velocity=1,
                status=ProductStatus.ACTIVE,
                cost_price=18.00,
                supplier_id="SUP-ELEC-02"
            ),
            Product(
                id="PRD-003",
                sku="SKU-APP-001",
                name="Organic Cotton T-Shirt",
                category=ProductCategory.APPAREL,
                current_price=24.99,
                stock_level=8,
                reorder_threshold=15,
                demand_velocity=12,
                status=ProductStatus.PRICE_REVIEW_PENDING,
                cost_price=11.50,
                supplier_id="SUP-APP-01"
            ),
            Product(
                id="PRD-004",
                sku="SKU-APP-002",
                name="Running Shorts — Navy",
                category=ProductCategory.APPAREL,
                current_price=39.99,
                stock_level=55,
                reorder_threshold=20,
                demand_velocity=2,
                status=ProductStatus.ACTIVE,
                cost_price=19.00,
                supplier_id="SUP-APP-02"
            ),
            Product(
                id="PRD-005",
                sku="SKU-HOME-001",
                name="Ceramic Pour-Over Set",
                category=ProductCategory.HOME,
                current_price=49.99,
                stock_level=22,
                reorder_threshold=10,
                demand_velocity=4,
                status=ProductStatus.ACTIVE,
                cost_price=26.00,
                supplier_id="SUP-HOME-01"
            ),
            Product(
                id="PRD-006",
                sku="SKU-HOME-002",
                name="LED Desk Lamp — Dimmable",
                category=ProductCategory.HOME,
                current_price=59.99,
                stock_level=0,
                reorder_threshold=15,
                demand_velocity=0,
                status=ProductStatus.OUT_OF_STOCK,
                cost_price=32.00,
                supplier_id="SUP-HOME-02"
            ),
            Product(
                id="PRD-007",
                sku="SKU-ELEC-003",
                name="Portable Charger 20K",
                category=ProductCategory.ELECTRONICS,
                current_price=44.99,
                stock_level=18,
                reorder_threshold=25,
                demand_velocity=8,
                status=ProductStatus.ACTIVE,
                cost_price=24.00,
                supplier_id="SUP-ELEC-01"
            ),
            Product(
                id="PRD-008",
                sku="SKU-APP-003",
                name="Hoodie — Heather Grey",
                category=ProductCategory.APPAREL,
                current_price=54.99,
                stock_level=11,
                reorder_threshold=12,
                demand_velocity=15,
                status=ProductStatus.ACTIVE,
                cost_price=28.00,
                supplier_id="SUP-APP-01"
            ),
        ]

        for product in products:
            session.add(product)
        session.commit()

        # Seed initial pending suggestions for PRD-003 (primary inventory-low demonstration)
        initial_pricing_sugg = PricingSuggestion(
            product_id="PRD-003",
            current_price=24.99,
            recommended_price=27.49,
            direction=PricingDirection.INCREASE,
            confidence=0.86,
            reasoning="Inventory is critically low (8 units remaining vs 15 threshold) with high demand velocity (12 units/24h). Recommend a +10% price adjustment to optimize margin while rationing remaining inventory before restocking.",
            status=SuggestionStatus.PENDING,
            trigger_reason=TriggerReason.INVENTORY_LOW
        )
        initial_reorder_sugg = ReorderSuggestion(
            product_id="PRD-003",
            current_stock=8,
            recommended_quantity=37,
            suggested_lead_time_days=5,
            confidence=0.88,
            reasoning="Current stock (8 units) has only ~0.7 days of runway at current velocity (12 units/day). Restocking 37 units will restore stock to 3x safety threshold (45 units target).",
            status=SuggestionStatus.PENDING,
            trigger_reason=TriggerReason.INVENTORY_LOW
        )

        session.add(initial_pricing_sugg)
        session.add(initial_reorder_sugg)
        session.commit()

        print("StockPulse database successfully initialized and seeded with 8 products and initial suggestions!")


if __name__ == "__main__":
    seed_database()