import logging
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("stockpulse.llm")


class LLMClientError(Exception):
    """Base exception for LLM Client failures"""
    pass


class LLMClient:
    """HTTP client for any OpenAI-compatible chat completions API"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call the chat completions endpoint and return message content"""
        if not self.api_key:
            raise LLMClientError("LLM_API_KEY is not configured in environment")

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Calling LLM Gateway: {endpoint} with model {self.model}")
                response = await client.post(endpoint, headers=headers, json=payload)
                
                if response.status_code != 200:
                    error_msg = f"LLM API returned status {response.status_code}: {response.text[:200]}"
                    logger.warning(error_msg)
                    raise LLMClientError(error_msg)

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMClientError("LLM response contained no choices")

                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise LLMClientError("LLM response content was empty")

                return content

        except httpx.TimeoutException as e:
            logger.warning(f"LLM request timed out after {self.timeout}s: {e}")
            raise LLMClientError(f"LLM request timed out: {e}") from e
        except httpx.RequestError as e:
            logger.warning(f"LLM network error: {e}")
            raise LLMClientError(f"LLM connection error: {e}") from e
        except Exception as e:
            if isinstance(e, LLMClientError):
                raise
            logger.warning(f"Unexpected LLM client error: {e}")
            raise LLMClientError(f"Unexpected error in LLM client: {e}") from e


# Global client instance
default_llm_client = LLMClient()
