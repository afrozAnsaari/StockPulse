import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from main import app
from app.core.db import get_session
from app.models.models import (
    Product, ProductCategory, ProductStatus,
    PricingSuggestion, ReorderSuggestion, PricingDirection,
    SuggestionStatus, TriggerReason
)
from app.services.strategy.manager import strategy_manager


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """Create a fresh in-memory SQLite database for each test"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed test data
        p1 = Product(
            id="PRD-001",
            sku="SKU-ELEC-001",
            name="Wireless Earbuds Pro",
            category=ProductCategory.ELECTRONICS,
            current_price=79.99,
            stock_level=45,
            reorder_threshold=20,
            demand_velocity=3,
            status=ProductStatus.ACTIVE
        )
        p3 = Product(
            id="PRD-003",
            sku="SKU-APP-001",
            name="Organic Cotton T-Shirt",
            category=ProductCategory.APPAREL,
            current_price=24.99,
            stock_level=8,
            reorder_threshold=15,
            demand_velocity=12,
            status=ProductStatus.PRICE_REVIEW_PENDING
        )
        p8 = Product(
            id="PRD-008",
            sku="SKU-APP-003",
            name="Hoodie — Heather Grey",
            category=ProductCategory.APPAREL,
            current_price=54.99,
            stock_level=11,
            reorder_threshold=12,
            demand_velocity=15,
            status=ProductStatus.ACTIVE
        )
        session.add(p1)
        session.add(p3)
        session.add(p8)
        session.commit()
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """TestClient overriding get_session to use test in-memory session"""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    # Default to rule strategy for deterministic tests
    strategy_manager.set_active_strategy("rule")
    
    with TestClient(app) as client:
        yield client
        
    app.dependency_overrides.clear()
