from sqlmodel import create_engine, Session
from app.core.config import settings
from app.models.models import Product, Order

engine = create_engine(settings.DATABASE_URL, echo=True)


def init_db():
    Product.metadata.create_all(engine)
    Order.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session