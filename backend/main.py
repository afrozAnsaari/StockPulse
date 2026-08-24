from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import init_db, engine
from app.models.models import Product
try:
    from seed import seed_database
except ImportError:
    from app.seed import seed_database
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    init_db()
    
    # Auto-seed if database is empty
    with Session(engine) as session:
        existing_products = session.exec(select(Product)).first()
        if not existing_products:
            seed_database(reset=False)
            
    yield


app = FastAPI(
    title="StockPulse API",
    description="Agentic Inventory Management & Dynamic Pricing Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes under /api/v1 as well as root level for convenience
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="")


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to StockPulse API",
        "docs_url": "/docs",
        "active_strategy": settings.ACTIVE_STRATEGY,
        "version": "1.0.0"
    }