import httpx
import json
import asyncio
from typing import Dict, Any, Optional
from app.core.config import settings
from app.schemas.schemas import PricingRecommendation, ReorderRecommendation
from app.models.models import Product


async def call_llm_api(prompt: str) -> Dict[str, Any]:
    """Call the LLM API with the given prompt"""
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
        "product": "PC1"
    }
    
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.LLM_API_URL,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return {}


def create_pricing_prompt(product: Product) -> str:
    """Create a prompt for pricing recommendations"""
    return f"""Product {product.id}: price {product.current_price}, stock {product.stock_level}, 
    threshold {product.reorder_threshold}, velocity {product.demand_velocity}. 
    Suggest new price and reorder qty. Respond with JSON format:
    {{
        "recommendedPrice": <float>,
        "direction": "INCREASE"/"DECREASE"/"MAINTAIN",
        "confidence": <float>,
        "reasoning": "..."
    }}"""


def create_reorder_prompt(product: Product) -> str:
    """Create a prompt for reorder recommendations"""
    return f"""Product {product.id}: price {product.current_price}, stock {product.stock_level}, 
    threshold {product.reorder_threshold}, velocity {product.demand_velocity}. 
    Suggest reorder quantity. Respond with JSON format:
    {{
        "recommendedQuantity": <int>,
        "confidence": <float>,
        "reasoning": "..."
    }}"""


async def get_pricing_recommendation(product: Product) -> Optional[PricingRecommendation]:
    """Get pricing recommendation from LLM"""
    prompt = create_pricing_prompt(product)
    response = await call_llm_api(prompt)
    
    # Extract the content from the response
    try:
        if "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0]["message"]["content"]
            # Try to parse as JSON
            recommendation_data = json.loads(content)
            return PricingRecommendation(**recommendation_data)
    except Exception as e:
        print(f"Error parsing pricing recommendation: {e}")
        return None


async def get_reorder_recommendation(product: Product) -> Optional[ReorderRecommendation]:
    """Get reorder recommendation from LLM"""
    prompt = create_reorder_prompt(product)
    response = await call_llm_api(prompt)
    
    # Extract the content from the response
    try:
        if "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0]["message"]["content"]
            # Try to parse as JSON
            recommendation_data = json.loads(content)
            return ReorderRecommendation(**recommendation_data)
    except Exception as e:
        print(f"Error parsing reorder recommendation: {e}")
        return None