import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.models import (
    Product, ProductCategory, ProductStatus,
    PricingSuggestion, ReorderSuggestion, PricingDirection,
    SuggestionStatus, TriggerReason
)
from app.services.strategy.rule_strategy import RulePricingStrategy, RuleReorderStrategy
from app.services.strategy.ai_strategy import AIPricingStrategy, AIReorderStrategy
from app.services.ai.client import LLMClient, LLMClientError
from app.services.recommendation_engine import process_async_recommendations


# 1. Create Product
def test_create_product(client: TestClient):
    payload = {
        "id": "PRD-TEST-01",
        "sku": "SKU-TEST-01",
        "name": "Smart Scale Pro",
        "category": "ELECTRONICS",
        "current_price": 49.99,
        "stock_level": 30,
        "reorder_threshold": 10,
        "demand_velocity": 0,
        "status": "ACTIVE"
    }
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "PRD-TEST-01"
    assert data["sku"] == "SKU-TEST-01"
    assert data["current_price"] == 49.99


# 2. List Products
def test_list_products(client: TestClient):
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    ids = [p["id"] for p in data]
    assert "PRD-001" in ids


# 3. Filter by Category
def test_filter_by_category(client: TestClient):
    response = client.get("/api/v1/products?category=ELECTRONICS")
    assert response.status_code == 200
    data = response.json()
    for product in data:
        assert product["category"] == "ELECTRONICS"


# 4. Filter by Status
def test_filter_by_status(client: TestClient):
    response = client.get("/api/v1/products?status=PRICE_REVIEW_PENDING")
    assert response.status_code == 200
    data = response.json()
    for product in data:
        assert product["status"] == "PRICE_REVIEW_PENDING"


# 5. Update Stock
def test_update_stock(client: TestClient):
    response = client.patch("/api/v1/products/PRD-001/stock", json={"stock_level": 50})
    assert response.status_code == 200
    data = response.json()
    assert data["stock_level"] == 50


# 6. Prevent Negative Stock
def test_prevent_negative_stock(client: TestClient):
    response = client.patch("/api/v1/products/PRD-001/stock", json={"stock_level": -10})
    assert response.status_code in (400, 422)


# 7. Create Simulated Order
def test_create_simulated_order(client: TestClient):
    response = client.post("/api/v1/products/PRD-001/orders", json={"quantity": 2})
    assert response.status_code == 201
    data = response.json()
    assert data["product_id"] == "PRD-001"
    assert data["quantity"] == 2


# 8. Order Decrements Stock
def test_order_decrements_stock(client: TestClient):
    # Initial stock is 45
    res1 = client.get("/api/v1/products/PRD-001")
    initial_stock = res1.json()["stock_level"]

    client.post("/api/v1/products/PRD-001/orders", json={"quantity": 5})

    res2 = client.get("/api/v1/products/PRD-001")
    assert res2.json()["stock_level"] == initial_stock - 5


# 9. Inventory-Low Detection
def test_inventory_low_detection(client: TestClient):
    # PRD-001 has threshold 20. Update stock to 10 (<20)
    response = client.patch("/api/v1/products/PRD-001/stock", json={"stock_level": 10})
    assert response.status_code == 200


# 10. Demand-Spike Detection
def test_demand_spike_detection(client: TestClient):
    # Order a large quantity to elevate velocity
    response = client.post("/api/v1/products/PRD-008/orders", json={"quantity": 5})
    assert response.status_code == 201


# 11. Rule Pricing Strategy
@pytest.mark.asyncio
async def test_rule_pricing_strategy():
    strategy = RulePricingStrategy()
    
    # Low stock case -> +10%
    low_stock_prod = Product(
        id="P_LOW", sku="S_LOW", name="Item", category=ProductCategory.APPAREL,
        current_price=100.0, stock_level=5, reorder_threshold=10, demand_velocity=2
    )
    rec = await strategy.recommend(low_stock_prod, category_avg_velocity=2.0, trigger_reason=TriggerReason.INVENTORY_LOW)
    assert rec.recommendedPrice == 110.0
    assert rec.direction == PricingDirection.INCREASE

    # Stable case -> HOLD
    stable_prod = Product(
        id="P_STABLE", sku="S_STABLE", name="Item", category=ProductCategory.APPAREL,
        current_price=100.0, stock_level=50, reorder_threshold=10, demand_velocity=2
    )
    rec2 = await strategy.recommend(stable_prod, category_avg_velocity=2.0, trigger_reason=TriggerReason.INITIAL)
    assert rec2.recommendedPrice == 100.0
    assert rec2.direction == PricingDirection.HOLD


# 12. Rule Reorder Strategy
@pytest.mark.asyncio
async def test_rule_reorder_strategy():
    strategy = RuleReorderStrategy()
    prod = Product(
        id="P_REORDER", sku="S_REORDER", name="Item", category=ProductCategory.APPAREL,
        current_price=20.0, stock_level=8, reorder_threshold=15, demand_velocity=5
    )
    # (15 * 3) - 8 = 37
    rec = await strategy.recommend(prod, category_avg_velocity=2.0, trigger_reason=TriggerReason.INVENTORY_LOW)
    assert rec.recommendedQuantity == 37
    assert rec.suggested_lead_time_days == 5


# 13. Manual Pricing Suggestion
def test_manual_pricing_suggestion(client: TestClient):
    response = client.post("/api/v1/products/PRD-001/suggest-pricing")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "PRD-001"
    assert data["trigger_reason"] == "MANUAL"
    assert data["status"] == "PENDING"
    assert data["recommended_price"] > 0


# 14. Manual Reorder Suggestion
def test_manual_reorder_suggestion(client: TestClient):
    response = client.post("/api/v1/products/PRD-001/suggest-reorder")
    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == "PRD-001"
    assert data["trigger_reason"] == "MANUAL"
    assert data["status"] == "PENDING"
    assert data["recommended_quantity"] >= 1


# 15. Accept Pricing Suggestion
def test_accept_pricing_suggestion(client: TestClient, session: Session):
    sugg = PricingSuggestion(
        product_id="PRD-001",
        current_price=79.99,
        recommended_price=89.99,
        direction=PricingDirection.INCREASE,
        confidence=0.85,
        reasoning="Test increase",
        status=SuggestionStatus.PENDING,
        trigger_reason=TriggerReason.MANUAL
    )
    session.add(sugg)
    session.commit()
    session.refresh(sugg)

    response = client.patch(f"/api/v1/pricing-suggestions/{sugg.id}", json={"status": "ACCEPTED"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACCEPTED"

    # Verify product current_price updated
    prod = client.get("/api/v1/products/PRD-001").json()
    assert prod["current_price"] == 89.99


# 16. Reject Pricing Suggestion
def test_reject_pricing_suggestion(client: TestClient, session: Session):
    sugg = PricingSuggestion(
        product_id="PRD-001",
        current_price=79.99,
        recommended_price=99.99,
        direction=PricingDirection.INCREASE,
        confidence=0.75,
        reasoning="Test rejection",
        status=SuggestionStatus.PENDING,
        trigger_reason=TriggerReason.MANUAL
    )
    session.add(sugg)
    session.commit()
    session.refresh(sugg)

    response = client.patch(f"/api/v1/pricing-suggestions/{sugg.id}", json={"status": "REJECTED"})
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


# 17. Accept Reorder Suggestion
def test_accept_reorder_suggestion(client: TestClient, session: Session):
    prod = session.get(Product, "PRD-001")
    initial_stock = prod.stock_level

    sugg = ReorderSuggestion(
        product_id="PRD-001",
        current_stock=initial_stock,
        recommended_quantity=25,
        suggested_lead_time_days=5,
        confidence=0.85,
        reasoning="Test reorder",
        status=SuggestionStatus.PENDING,
        trigger_reason=TriggerReason.MANUAL
    )
    session.add(sugg)
    session.commit()
    session.refresh(sugg)

    response = client.patch(f"/api/v1/reorder-suggestions/{sugg.id}", json={"status": "ACCEPTED"})
    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"

    # Verify stock increased
    updated_prod = client.get("/api/v1/products/PRD-001").json()
    assert updated_prod["stock_level"] == initial_stock + 25


# 18. Reject Reorder Suggestion
def test_reject_reorder_suggestion(client: TestClient, session: Session):
    sugg = ReorderSuggestion(
        product_id="PRD-001",
        current_stock=45,
        recommended_quantity=20,
        suggested_lead_time_days=5,
        confidence=0.80,
        reasoning="Test reject reorder",
        status=SuggestionStatus.PENDING,
        trigger_reason=TriggerReason.MANUAL
    )
    session.add(sugg)
    session.commit()
    session.refresh(sugg)

    response = client.patch(f"/api/v1/reorder-suggestions/{sugg.id}", json={"status": "REJECTED"})
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


# 19. Duplicate Pending Suggestion Prevention (Idempotency)
@pytest.mark.asyncio
async def test_duplicate_pending_suggestion_prevention(session: Session):
    # Insert existing PENDING suggestion
    sugg = PricingSuggestion(
        product_id="PRD-003",
        current_price=24.99,
        recommended_price=27.49,
        direction=PricingDirection.INCREASE,
        confidence=0.85,
        reasoning="Initial low stock",
        status=SuggestionStatus.PENDING,
        trigger_reason=TriggerReason.INVENTORY_LOW
    )
    session.add(sugg)
    session.commit()

    # Trigger process_async_recommendations for PRD-003 with INVENTORY_LOW
    await process_async_recommendations("PRD-003", TriggerReason.INVENTORY_LOW)

    # Count pending pricing suggestions for PRD-003
    pending = session.exec(
        select(PricingSuggestion).where(
            PricingSuggestion.product_id == "PRD-003",
            PricingSuggestion.trigger_reason == TriggerReason.INVENTORY_LOW,
            PricingSuggestion.status == SuggestionStatus.PENDING
        )
    ).all()
    # Must NOT have created a duplicate!
    assert len(pending) == 1


# 20. Invalid AI JSON Fallback
@pytest.mark.asyncio
async def test_invalid_ai_json_fallback():
    mock_client = AsyncMock(spec=LLMClient)
    mock_client.generate.return_value = "This is not valid json at all"
    
    strategy = AIPricingStrategy(llm_client=mock_client)
    prod = Product(
        id="P1", sku="S1", name="Item", category=ProductCategory.APPAREL,
        current_price=50.0, stock_level=5, reorder_threshold=10, demand_velocity=2
    )
    rec = await strategy.recommend(prod, 2.0, TriggerReason.INVENTORY_LOW)
    # Should fall back to rule pricing (+10% -> $55.0)
    assert rec.recommendedPrice == 55.0
    assert rec.direction == PricingDirection.INCREASE
    assert "AI Fallback Applied" in rec.reasoning


# 21. AI Timeout Fallback
@pytest.mark.asyncio
async def test_ai_timeout_fallback():
    mock_client = AsyncMock(spec=LLMClient)
    mock_client.generate.side_effect = LLMClientError("LLM request timed out")

    strategy = AIPricingStrategy(llm_client=mock_client)
    prod = Product(
        id="P1", sku="S1", name="Item", category=ProductCategory.APPAREL,
        current_price=50.0, stock_level=5, reorder_threshold=10, demand_velocity=2
    )
    rec = await strategy.recommend(prod, 2.0, TriggerReason.INVENTORY_LOW)
    assert rec.recommendedPrice == 55.0
    assert "AI Fallback Applied" in rec.reasoning


# 22. Invalid AI Price Fallback
@pytest.mark.asyncio
async def test_invalid_ai_price_fallback():
    mock_client = AsyncMock(spec=LLMClient)
    # Absurd price breaching guardrails ($99999.0 on a $50 product)
    mock_client.generate.return_value = '{"recommendedPrice": 99999.0, "direction": "INCREASE", "confidence": 0.9, "reasoning": "Insane price"}'

    strategy = AIPricingStrategy(llm_client=mock_client)
    prod = Product(
        id="P1", sku="S1", name="Item", category=ProductCategory.APPAREL,
        current_price=50.0, stock_level=5, reorder_threshold=10, demand_velocity=2
    )
    rec = await strategy.recommend(prod, 2.0, TriggerReason.INVENTORY_LOW)
    # Guardrail triggered -> fell back to $55.0
    assert rec.recommendedPrice == 55.0
    assert "AI Fallback Applied" in rec.reasoning


# 23. Invalid AI Reorder Quantity Fallback
@pytest.mark.asyncio
async def test_invalid_ai_reorder_quantity_fallback():
    mock_client = AsyncMock(spec=LLMClient)
    # Negative reorder quantity
    mock_client.generate.return_value = '{"recommendedQuantity": -50, "confidence": 0.8, "reasoning": "Negative qty"}'

    strategy = AIReorderStrategy(llm_client=mock_client)
    prod = Product(
        id="P1", sku="S1", name="Item", category=ProductCategory.APPAREL,
        current_price=50.0, stock_level=8, reorder_threshold=15, demand_velocity=5
    )
    rec = await strategy.recommend(prod, 2.0, TriggerReason.INVENTORY_LOW)
    # Fell back to (15 * 3) - 8 = 37
    assert rec.recommendedQuantity == 37
    assert "AI Fallback Applied" in rec.reasoning


# 24. Product Out-of-Stock Transition
def test_product_out_of_stock_transition(client: TestClient):
    response = client.patch("/api/v1/products/PRD-001/stock", json={"stock_level": 0})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OUT_OF_STOCK"
    assert data["stock_level"] == 0
