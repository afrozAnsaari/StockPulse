import logging
from typing import Dict, Optional
from app.core.config import settings
from app.services.strategy.base import CommerceAdvisor
from app.services.strategy.rule_strategy import RuleCommerceAdvisor
from app.services.strategy.ai_strategy import AICommerceAdvisor

logger = logging.getLogger("stockpulse.strategy_manager")


class StrategyManager:
    """Central registry and runtime strategy manager"""

    def __init__(self):
        self._advisors: Dict[str, CommerceAdvisor] = {
            "rule": RuleCommerceAdvisor(),
            "ai": AICommerceAdvisor()
        }
        self._active_strategy: str = settings.ACTIVE_STRATEGY.strip().lower()
        if self._active_strategy not in self._advisors:
            self._active_strategy = "ai"

    @property
    def active_strategy(self) -> str:
        return self._active_strategy

    def set_active_strategy(self, strategy_name: str) -> str:
        cleaned = strategy_name.strip().lower()
        if cleaned not in self._advisors:
            raise ValueError(f"Unknown strategy '{cleaned}'. Supported strategies: {list(self._advisors.keys())}")
        self._active_strategy = cleaned
        logger.info(f"Active commerce strategy switched to '{self._active_strategy}'")
        return self._active_strategy

    def register_strategy(self, name: str, advisor: CommerceAdvisor) -> None:
        """Extension seam for future strategies, e.g. 'competitor_aware'"""
        self._advisors[name.strip().lower()] = advisor
        logger.info(f"Registered new strategy '{name}'")

    def get_advisor(self, strategy_name: Optional[str] = None) -> CommerceAdvisor:
        key = (strategy_name or self._active_strategy).strip().lower()
        return self._advisors.get(key, self._advisors["ai"])


# Global strategy manager singleton
strategy_manager = StrategyManager()
