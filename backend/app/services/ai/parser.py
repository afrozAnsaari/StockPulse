import json
import re
import logging
from typing import Dict, Any
from app.models.models import PricingDirection
from app.schemas.schemas import PricingRecommendation, ReorderRecommendation
from app.core.config import settings

logger = logging.getLogger("stockpulse.parser")


class AIValidationError(Exception):
    """Exception raised when LLM output violates schema or guardrails"""
    pass


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract JSON from raw LLM text or code markdown fences"""
    if not text or not text.strip():
        raise AIValidationError("Raw LLM response was empty")

    cleaned = text.strip()

    # Match ```json ... ``` or ``` ... ```
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(fence_pattern, cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()

    # If surrounded by brackets or braces, attempt to find the outermost JSON object
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace:last_brace + 1]

    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise AIValidationError(f"Expected JSON object, got {type(data).__name__}")
        return data
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from LLM output: {e}. Raw text: {text[:200]}")
        raise AIValidationError(f"Invalid JSON in LLM response: {e}") from e


def parse_and_validate_pricing(
    raw_response: str,
    current_price: float
) -> PricingRecommendation:
    """Parse, schema-validate, and apply safety guardrails to pricing recommendation"""
    data = extract_json_from_text(raw_response)

    # Normalize keys if camelCase or snake_case
    rec_price = data.get("recommendedPrice") or data.get("recommended_price")
    raw_direction = data.get("direction")
    confidence = data.get("confidence")
    reasoning = data.get("reasoning")

    if rec_price is None:
        raise AIValidationError("Missing 'recommendedPrice' in LLM output")
    if raw_direction is None:
        raise AIValidationError("Missing 'direction' in LLM output")
    if confidence is None:
        raise AIValidationError("Missing 'confidence' in LLM output")
    if not reasoning or not str(reasoning).strip():
        raise AIValidationError("Missing or empty 'reasoning' in LLM output")

    try:
        rec_price_float = round(float(rec_price), 2)
    except (ValueError, TypeError) as e:
        raise AIValidationError(f"Invalid recommendedPrice value: {rec_price}") from e

    try:
        conf_float = float(confidence)
        if not (0.0 <= conf_float <= 1.0):
            # Clamp or reject
            conf_float = max(0.0, min(1.0, conf_float))
    except (ValueError, TypeError) as e:
        raise AIValidationError(f"Invalid confidence value: {confidence}") from e

    direction_str = str(raw_direction).strip().upper()
    if direction_str == "MAINTAIN":
        direction_str = "HOLD"

    if direction_str not in ("INCREASE", "DECREASE", "HOLD"):
        raise AIValidationError(f"Invalid direction '{raw_direction}'. Expected INCREASE, DECREASE, or HOLD")

    # Guardrails: Price must be positive and within configured bounds
    if rec_price_float <= 0:
        raise AIValidationError(f"Recommended price ${rec_price_float:.2f} must be strictly positive")

    min_safe_price = round(current_price * settings.PRICE_MIN_MULTIPLIER, 2)
    max_safe_price = round(current_price * settings.PRICE_MAX_MULTIPLIER, 2)

    if not (min_safe_price <= rec_price_float <= max_safe_price):
        raise AIValidationError(
            f"Recommended price ${rec_price_float:.2f} breaches safety guardrails "
            f"[{min_safe_price:.2f}, {max_safe_price:.2f}] based on current price ${current_price:.2f}"
        )

    return PricingRecommendation(
        recommendedPrice=rec_price_float,
        direction=PricingDirection(direction_str),
        confidence=conf_float,
        reasoning=str(reasoning).strip()
    )


def parse_and_validate_reorder(
    raw_response: str
) -> ReorderRecommendation:
    """Parse, schema-validate, and apply safety guardrails to reorder recommendation"""
    data = extract_json_from_text(raw_response)

    rec_qty = data.get("recommendedQuantity") or data.get("recommended_quantity")
    lead_time = data.get("suggested_lead_time_days") or data.get("suggestedLeadTimeDays", 5)
    confidence = data.get("confidence")
    reasoning = data.get("reasoning")

    if rec_qty is None:
        raise AIValidationError("Missing 'recommendedQuantity' in LLM output")
    if confidence is None:
        raise AIValidationError("Missing 'confidence' in LLM output")
    if not reasoning or not str(reasoning).strip():
        raise AIValidationError("Missing or empty 'reasoning' in LLM output")

    try:
        qty_int = int(round(float(rec_qty)))
        if qty_int < 1:
            raise AIValidationError(f"Recommended quantity ({qty_int}) must be >= 1")
    except (ValueError, TypeError) as e:
        raise AIValidationError(f"Invalid recommendedQuantity value: {rec_qty}") from e

    try:
        lead_time_int = max(1, int(round(float(lead_time))))
    except (ValueError, TypeError):
        lead_time_int = 5

    try:
        conf_float = float(confidence)
        conf_float = max(0.0, min(1.0, conf_float))
    except (ValueError, TypeError) as e:
        raise AIValidationError(f"Invalid confidence value: {confidence}") from e

    return ReorderRecommendation(
        recommendedQuantity=qty_int,
        suggested_lead_time_days=lead_time_int,
        confidence=conf_float,
        reasoning=str(reasoning).strip()
    )
