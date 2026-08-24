from typing import Optional, List
from sqlmodel import Session, select
from app.models.models import Product, Order
from app.schemas.schemas import ProductCreate, ProductUpdate, OrderCreate


def get_product(session: Session, product_id: str) -> Optional[Product]:
    return session.get(Product, product_id)


def get_products(session: Session) -> List[Product]:
    statement = select(Product)
    return session.exec(statement).all()


def create_product(session: Session, product: ProductCreate) -> Product:
    db_product = Product.from_orm(product)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


def update_product(session: Session, product_id: str, product_update: ProductUpdate) -> Optional[Product]:
    db_product = session.get(Product, product_id)
    if not db_product:
        return None
    
    product_data = product_update.dict(exclude_unset=True)
    for key, value in product_data.items():
        setattr(db_product, key, value)
    
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


def create_order(session: Session, order: OrderCreate) -> Order:
    db_order = Order.from_orm(order)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order


def get_orders_for_product(session: Session, product_id: str) -> List[Order]:
    statement = select(Order).where(Order.product_id == product_id)
    return session.exec(statement).all()