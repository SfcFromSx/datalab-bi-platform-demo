from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

litellm.set_verbose = False


class LLMClient:
    """Unified LLM client wrapping LiteLLM for multi-provider support."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.litellm_model

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        tools: Optional[list[dict]] = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools
        kwargs["timeout"] = 30.0

        try:
            response = await litellm.acompletion(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict:
        raw = await self.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
            raise

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                timeout=30.0,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
            raise


llm_client = LLMClient()
