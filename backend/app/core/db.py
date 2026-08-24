from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings
from app.models.models import Product, Order, PricingSuggestion, ReorderSuggestion

# Enable SQLite multi-thread connection handling if sqlite
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session