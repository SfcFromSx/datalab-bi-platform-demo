from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Optional

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

litellm.set_verbose = False


class LLMClient:
    """Unified LLM client wrapping LiteLLM for multi-provider support.

    Supports runtime model switching via set_model() and per-call overrides.
    """

    def __init__(self, model: Optional[str] = None):
        self._model = model or settings.litellm_model
        self._api_key: Optional[str] = settings.openai_api_key or None
        self._api_base: Optional[str] = settings.openai_api_base or None
        self._active_preset_id: str = "default"

    @property
    def model(self) -> str:
        return self._model

    @property
    def active_preset_id(self) -> str:
        return self._active_preset_id

    def set_model(self, preset_id: str) -> dict[str, Any]:
        """Switch to a model preset by id. Returns the active preset dict."""
        presets = settings.get_model_presets()
        for p in presets:
            if p["id"] == preset_id:
                self._model = p["model"]
                self._api_key = p.get("api_key") or None
                self._api_base = p.get("api_base") or None
                self._active_preset_id = p["id"]
                logger.info(f"Switched LLM to preset '{preset_id}': {self._model}")
                return p
        raise ValueError(f"Unknown model preset: {preset_id}")

    def _call_kwargs(self) -> dict[str, Any]:
        """Common kwargs for LiteLLM. Only include api_key/api_base when set (avoid None/empty)."""
        kw: dict[str, Any] = {"model": self._model}
        if self._api_key and self._api_key.strip():
            kw["api_key"] = self._api_key.strip()
        if self._api_base and self._api_base.strip():
            base = self._api_base.strip().rstrip("/")
            kw["api_base"] = base
        return kw

    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        tools: Optional[list[dict]] = None,
    ) -> str:
        kwargs = self._call_kwargs()
        kwargs.update(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30.0,
        )
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools
        if self._api_base:
            kwargs["drop_params"] = True
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
        # Many custom APIs (e.g. Volcengine Ark) do not support response_format.json_object
        if self._api_base:
            raw = await self.complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
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
        kwargs = self._call_kwargs()
        kwargs.update(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            timeout=30.0,
        )
        # Avoid sending unsupported params to custom OpenAI-compatible APIs (e.g. Volcengine Ark)
        if self._api_base:
            kwargs["drop_params"] = True
        try:
            response = await litellm.acompletion(**kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
            raise


llm_client = LLMClient()
