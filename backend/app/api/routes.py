from fastapi import APIRouter, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from sqlmodel import Session
from typing import List
import asyncio
from app.core.db import get_session
from app.core.crud import (
    get_product, get_products, create_product, update_product, 
    delete_product, create_order, get_orders_for_product
)
from app.models.models import Product, Order
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductOut,
    OrderCreate, OrderOut, PricingRecommendation, ReorderRecommendation
)
from app.services.llm_service import get_pricing_recommendation, get_reorder_recommendation

router = APIRouter()

# In-memory storage for WebSocket connections
active_connections: List[WebSocket] = []


@router.get("/products", response_model=List[ProductOut])
def read_products(session: Session = Depends(get_session)):
    """Get all products"""
    products = get_products(session)
    return products


@router.get("/products/{product_id}", response_model=ProductOut)
def read_product(product_id: str, session: Session = Depends(get_session)):
    """Get a specific product"""
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/orders", response_model=OrderOut)
async def create_order_endpoint(
    order: OrderCreate, 
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """Create an order and update product inventory"""
    # Get the product
    product = get_product(session, order.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create the order
    db_order = create_order(session, order)
    
    # Update product stock and demand velocity
    product.stock_level -= order.quantity
    product.demand_velocity += order.quantity
    
    # Check if we need to trigger AI recommendations
    trigger_ai = False
    if product.stock_level < product.reorder_threshold:
        product.status = "PRICE_REVIEW_PENDING"
        trigger_ai = True
    elif product.demand_velocity > product.reorder_threshold:  # Demand spike threshold
        product.status = "PRICE_REVIEW_PENDING"
        trigger_ai = True
    
    # Update product in database
    session.add(product)
    session.commit()
    session.refresh(product)
    
    # Trigger AI recommendations in background if needed
    if trigger_ai:
        background_tasks.add_task(process_ai_recommendations, product, session)
    
    return db_order


@router.get("/recommendations/price")
async def get_price_recommendation(product_id: str, session: Session = Depends(get_session)):
    """Get price recommendation for a product"""
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    recommendation = await get_pricing_recommendation(product)
    return recommendation


@router.get("/recommendations/reorder")
async def get_reorder_recommendation(product_id: str, session: Session = Depends(get_session)):
    """Get reorder recommendation for a product"""
    product = get_product(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    recommendation = await get_reorder_recommendation(product)
    return recommendation


async def process_ai_recommendations(product: Product, session: Session):
    """Process AI recommendations in background"""
    try:
        # Get pricing recommendation
        pricing_rec = await get_pricing_recommendation(product)
        
        # Get reorder recommendation
        reorder_rec = await get_reorder_recommendation(product)
        
        # Prepare message for WebSocket broadcast
        message = {
            "product_id": product.id,
            "pricing_recommendation": pricing_rec.dict() if pricing_rec else None,
            "reorder_recommendation": reorder_rec.dict() if reorder_rec else None
        }
        
        # Broadcast to all active WebSocket connections
        for connection in active_connections[:]:  # Create a copy to avoid modification during iteration
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                active_connections.remove(connection)
            except Exception as e:
                print(f"Error sending WebSocket message: {e}")
                
    except Exception as e:
        print(f"Error processing AI recommendations: {e}")


@router.websocket("/ws/products")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time product updates"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Just keep the connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        active_connections.remove(websocket)