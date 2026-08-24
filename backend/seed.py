from sqlmodel import Session, create_engine
from app.models.models import Product
from app.core.db import engine
from sqlalchemy import text

def seed_database():
    """Seed the database with initial product data"""
    with Session(engine) as session:
        # Clear existing data
        session.execute(text("DELETE FROM product"))
        session.commit()
        
        # Sample products
        products = [
            Product(
                id="PRD-001",
                sku="SKU-001",
                name="Smartphone X",
                category="ELECTRONICS",
                current_price=699.99,
                stock_level=50,
                reorder_threshold=10,
                demand_velocity=0,
                status="ACTIVE"
            ),
            Product(
                id="PRD-002",
                sku="SKU-002",
                name="Laptop Pro",
                category="ELECTRONICS",
                current_price=1299.99,
                stock_level=25,
                reorder_threshold=5,
                demand_velocity=0,
                status="ACTIVE"
            ),
            Product(
                id="PRD-003",
                sku="SKU-003",
                name="T-Shirt",
                category="APPAREL",
                current_price=19.99,
                stock_level=20,  # Start with low stock for demo
                reorder_threshold=15,
                demand_velocity=0,
                status="ACTIVE"
            ),
            Product(
                id="PRD-004",
                sku="SKU-004",
                name="Coffee Maker",
                category="HOME",
                current_price=89.99,
                stock_level=30,
                reorder_threshold=10,
                demand_velocity=0,
                status="ACTIVE"
            ),
            Product(
                id="PRD-005",
                sku="SKU-005",
                name="Headphones",
                category="ELECTRONICS",
                current_price=149.99,
                stock_level=40,
                reorder_threshold=15,
                demand_velocity=0,
                status="ACTIVE"
            ),
            Product(
                id="PRD-006",
                sku="SKU-006",
                name="Running Shoes",
                category="APPAREL",
                current_price=89.99,
                stock_level=35,
                reorder_threshold=10,
                demand_velocity=0,
                status="ACTIVE"
            ),
            Product(
                id="PRD-007",
                sku="SKU-007",
                name="Desk Lamp",
                category="HOME",
                current_price=29.99,
                stock_level=50,
                reorder_threshold=15,
                demand_velocity=0,
                status="ACTIVE"
            ),
            Product(
                id="PRD-008",
                sku="SKU-008",
                name="Hoodie",
                category="APPAREL",
                current_price=49.99,
                stock_level=100,
                reorder_threshold=20,
                demand_velocity=15,  # High initial velocity for demand spike demo
                status="ACTIVE"
            ),
        ]
        
        # Add products to session
        for product in products:
            session.add(product)
            
        session.commit()
        print("Database seeded successfully!")


if __name__ == "__main__":
    seed_database()