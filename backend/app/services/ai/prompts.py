from typing import Optional
from app.models.models import Product, TriggerReason

SYSTEM_PROMPT = """You are StockPulse AI, an expert retail merchandising and dynamic pricing strategist.
Your task is to analyze inventory data, demand velocity, category benchmarks, and business context to provide high-precision merchandising recommendations.

Output Rules:
1. You MUST respond with ONLY a valid, parseable JSON object matching the requested schema.
2. Do NOT include markdown code blocks, explanatory prose before/after, or conversational filler.
3. Pricing direction must be exactly one of: "INCREASE", "DECREASE", "HOLD".
4. Confidence must be a float between 0.0 and 1.0.
5. Provide clear, analytical reasoning in the "reasoning" field.
"""


def build_inventory_low_pricing_prompt(
    product: Product,
    category_avg_velocity: float
) -> str:
    """Prompt specialized for INVENTORY_LOW pricing scenarios"""
    cost_info = f"Cost Price: ${product.cost_price:.2f}" if product.cost_price else "Cost Price: Not specified"
    return f"""INVENTORY SCARCITY & PRICE PROTECTION ANALYSIS:
Product ID: {product.id}
Product Name: {product.name}
SKU: {product.sku}
Category: {product.category.value}
Current Price: ${product.current_price:.2f}
{cost_info}
Current Stock Level: {product.stock_level} units
Reorder Threshold: {product.reorder_threshold} units
Demand Velocity: {product.demand_velocity} units ordered in the last 24 hours
Category Average Velocity: {category_avg_velocity:.2f} units/24h
Trigger Reason: INVENTORY_LOW

Merchandising Context & Reasoning Instructions:
- The product's stock ({product.stock_level} units) has fallen below its safety threshold ({product.reorder_threshold} units).
- Analyze inventory scarcity, current velocity, and remaining runway (stock / velocity).
- Consider whether a modest price increase (typically 5% to 15%) is appropriate to protect stock and maximize gross margin while awaiting replenishment, or whether holding price is preferable.
- Avoid extreme price gouging. Maintain positive consumer perception.

Required Output JSON Schema:
{{
  "recommendedPrice": <float rounded to 2 decimal places>,
  "direction": "INCREASE" or "DECREASE" or "HOLD",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<concise analytical explanation of stock scarcity, price adjustment, and margin protection>"
}}
"""


def build_inventory_low_reorder_prompt(
    product: Product,
    category_avg_velocity: float
) -> str:
    """Prompt specialized for INVENTORY_LOW reorder scenarios"""
    return f"""INVENTORY REPLENISHMENT & RESTOCKING ANALYSIS:
Product ID: {product.id}
Product Name: {product.name}
SKU: {product.sku}
Category: {product.category.value}
Current Price: ${product.current_price:.2f}
Current Stock Level: {product.stock_level} units
Reorder Threshold: {product.reorder_threshold} units
Demand Velocity: {product.demand_velocity} units ordered in the last 24 hours
Category Average Velocity: {category_avg_velocity:.2f} units/24h
Trigger Reason: INVENTORY_LOW

Restocking Instructions:
- Analyze remaining inventory runway against standard supplier lead times (3 to 7 days).
- Calculate an optimal restocking quantity to replenish stock to a safe level (typically 2.5x to 4x reorder threshold) while considering carrying cost and stockout risks.
- Output an integer recommended quantity >= 1.

Required Output JSON Schema:
{{
  "recommendedQuantity": <positive integer>,
  "suggested_lead_time_days": <integer days, default 5>,
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<concise explanation of restocking calculation, runway protection, and order quantity>"
}}
"""


def build_demand_spike_pricing_prompt(
    product: Product,
    category_avg_velocity: float
) -> str:
    """Prompt specialized for DEMAND_SPIKE pricing scenarios"""
    cost_info = f"Cost Price: ${product.cost_price:.2f}" if product.cost_price else "Cost Price: Not specified"
    velocity_multiple = (product.demand_velocity / category_avg_velocity) if category_avg_velocity > 0 else 1.0
    return f"""DEMAND ACCELERATION & SURGE MONETIZATION ANALYSIS:
Product ID: {product.id}
Product Name: {product.name}
SKU: {product.sku}
Category: {product.category.value}
Current Price: ${product.current_price:.2f}
{cost_info}
Current Stock Level: {product.stock_level} units
Reorder Threshold: {product.reorder_threshold} units
Current Demand Velocity: {product.demand_velocity} units ordered in the last 24 hours
Category Benchmark Velocity: {category_avg_velocity:.2f} units/24h
Surge Multiple: {velocity_multiple:.2f}x category average
Trigger Reason: DEMAND_SPIKE

Merchandising Context & Reasoning Instructions:
- The product is experiencing an exceptional demand surge ({product.demand_velocity} orders/24h, {velocity_multiple:.1f}x category average).
- Reason about monetizing heightened consumer demand by capturing surplus without causing demand cliff or customer friction.
- Evaluate remaining inventory runway given the accelerated burn rate.
- Determine a moderate, justified price increase (e.g. +5% to +20%) or hold if inventory is abundant.

Required Output JSON Schema:
{{
  "recommendedPrice": <float rounded to 2 decimal places>,
  "direction": "INCREASE" or "DECREASE" or "HOLD",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<concise analytical explanation of demand acceleration, surge capture, and inventory runway>"
}}
"""


def build_demand_spike_reorder_prompt(
    product: Product,
    category_avg_velocity: float
) -> str:
    """Prompt specialized for DEMAND_SPIKE reorder scenarios"""
    velocity_multiple = (product.demand_velocity / category_avg_velocity) if category_avg_velocity > 0 else 1.0
    return f"""DEMAND SPIKE RESTOCKING & SURGE BUFFER ANALYSIS:
Product ID: {product.id}
Product Name: {product.name}
SKU: {product.sku}
Category: {product.category.value}
Current Stock Level: {product.stock_level} units
Reorder Threshold: {product.reorder_threshold} units
Current Demand Velocity: {product.demand_velocity} units ordered in the last 24 hours
Category Average Velocity: {category_avg_velocity:.2f} units/24h
Surge Multiple: {velocity_multiple:.2f}x
Trigger Reason: DEMAND_SPIKE

Restocking Instructions:
- Because demand velocity has spiked, standard reorder quantities may lead to premature stockouts during lead times.
- Calculate an expedited or enlarged replenishment quantity accounting for the higher velocity run-rate.

Required Output JSON Schema:
{{
  "recommendedQuantity": <positive integer>,
  "suggested_lead_time_days": <integer days, default 5>,
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<concise explanation of surge replenishment buffer and lead-time demand coverage>"
}}
"""


def build_generic_pricing_prompt(
    product: Product,
    category_avg_velocity: float,
    trigger_reason: TriggerReason
) -> str:
    """Fallback / Manual pricing prompt"""
    return f"""COMMERCE PRICING REVIEW (Trigger: {trigger_reason.value}):
Product ID: {product.id}
Product Name: {product.name}
Category: {product.category.value}
Current Price: ${product.current_price:.2f}
Current Stock Level: {product.stock_level} units
Reorder Threshold: {product.reorder_threshold} units
Demand Velocity: {product.demand_velocity} units/24h
Category Average Velocity: {category_avg_velocity:.2f} units/24h

Provide dynamic pricing recommendation in JSON:
{{
  "recommendedPrice": <float rounded to 2 decimal places>,
  "direction": "INCREASE" or "DECREASE" or "HOLD",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<analytical explanation>"
}}
"""


def build_generic_reorder_prompt(
    product: Product,
    category_avg_velocity: float,
    trigger_reason: TriggerReason
) -> str:
    """Fallback / Manual reorder prompt"""
    return f"""COMMERCE REORDER REVIEW (Trigger: {trigger_reason.value}):
Product ID: {product.id}
Product Name: {product.name}
Category: {product.category.value}
Current Stock Level: {product.stock_level} units
Reorder Threshold: {product.reorder_threshold} units
Demand Velocity: {product.demand_velocity} units/24h
Category Average Velocity: {category_avg_velocity:.2f} units/24h

Provide reorder quantity recommendation in JSON:
{{
  "recommendedQuantity": <positive integer>,
  "suggested_lead_time_days": <integer days, default 5>,
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<analytical explanation>"
}}
"""
