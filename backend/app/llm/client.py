from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Optional

import litellm

from app.config import settings

logger = logging.getLogger(__name__)

litellm.set_verbose = False

# ---------------------------------------------------------------------------
# Background log writer – writes LLMLog rows without blocking the caller
# ---------------------------------------------------------------------------

_log_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
_writer_started = False


async def _log_writer():
    """Background coroutine that drains _log_queue and persists LLMLog rows."""
    from app.database import async_session_factory
    from app.models.llm_log import LLMLog

    while True:
        entry = await _log_queue.get()
        try:
            async with async_session_factory() as session:
                log = LLMLog(**entry)
                session.add(log)
                await session.commit()
        except Exception as exc:
            logger.warning(f"Failed to persist LLM log: {exc}")
        finally:
            _log_queue.task_done()


def _ensure_writer():
    """Start the background writer task if not already running."""
    global _writer_started
    if _writer_started:
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_log_writer())
        _writer_started = True
    except RuntimeError:
        pass  # No event loop – skip (e.g. during import)


def _enqueue_log(
    *,
    feature: str,
    model: str,
    messages: list[dict[str, str]],
    response: str,
    tokens_prompt: int,
    tokens_completion: int,
    duration_ms: int,
    status: str,
    error: str | None,
    cell_id: str | None,
    notebook_id: str | None,
):
    _ensure_writer()
    _log_queue.put_nowait(
        {
            "id": str(uuid.uuid4()),
            "feature": feature,
            "model": model,
            "messages": messages,
            "response": response,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
            "duration_ms": duration_ms,
            "status": status,
            "error": error,
            "cell_id": cell_id,
            "notebook_id": notebook_id,
        }
    )


def _extract_usage(response) -> tuple[int, int]:
    """Best-effort token extraction from LiteLLM response."""
    try:
        usage = response.usage
        return (usage.prompt_tokens or 0, usage.completion_tokens or 0)
    except Exception:
        return (0, 0)


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------


class LLMClient:
    """Unified LLM client wrapping LiteLLM for multi-provider support.

    Supports runtime model switching via set_model() and per-call overrides.
    Every call is logged to the llm_logs table via a non-blocking background writer.
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
        log_meta: Optional[dict[str, str]] = None,
    ) -> str:
        meta = log_meta or {}
        kwargs = self._call_kwargs()
        kwargs.update(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=60.0,
        )
        if response_format:
            kwargs["response_format"] = response_format
        if tools:
            kwargs["tools"] = tools
        if self._api_base:
            kwargs["drop_params"] = True

        t0 = time.monotonic()
        try:
            response = await litellm.acompletion(**kwargs)
            content = response.choices[0].message.content or ""
            pt, ct = _extract_usage(response)
            _enqueue_log(
                feature=meta.get("feature", "unknown"),
                model=self._model,
                messages=messages,
                response=content,
                tokens_prompt=pt,
                tokens_completion=ct,
                duration_ms=int((time.monotonic() - t0) * 1000),
                status="success",
                error=None,
                cell_id=meta.get("cell_id"),
                notebook_id=meta.get("notebook_id"),
            )
            return content
        except Exception as e:
            _enqueue_log(
                feature=meta.get("feature", "unknown"),
                model=self._model,
                messages=messages,
                response="",
                tokens_prompt=0,
                tokens_completion=0,
                duration_ms=int((time.monotonic() - t0) * 1000),
                status="error",
                error=str(e),
                cell_id=meta.get("cell_id"),
                notebook_id=meta.get("notebook_id"),
            )
            logger.error(f"LLM call failed: {e}")
            raise

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        log_meta: Optional[dict[str, str]] = None,
    ) -> dict:
        # Many custom APIs (e.g. Volcengine Ark) do not support response_format.json_object
        if self._api_base:
            raw = await self.complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                log_meta=log_meta,
            )
        else:
            raw = await self.complete(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                log_meta=log_meta,
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
        log_meta: Optional[dict[str, str]] = None,
    ) -> AsyncGenerator[str, None]:
        meta = log_meta or {}
        kwargs = self._call_kwargs()
        kwargs.update(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            timeout=60.0,
        )
        # Avoid sending unsupported params to custom OpenAI-compatible APIs (e.g. Volcengine Ark)
        if self._api_base:
            kwargs["drop_params"] = True

        t0 = time.monotonic()
        collected: list[str] = []
        try:
            response = await litellm.acompletion(**kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    collected.append(delta)
                    yield delta
            _enqueue_log(
                feature=meta.get("feature", "unknown"),
                model=self._model,
                messages=messages,
                response="".join(collected),
                tokens_prompt=0,
                tokens_completion=0,
                duration_ms=int((time.monotonic() - t0) * 1000),
                status="success",
                error=None,
                cell_id=meta.get("cell_id"),
                notebook_id=meta.get("notebook_id"),
            )
        except Exception as e:
            _enqueue_log(
                feature=meta.get("feature", "unknown"),
                model=self._model,
                messages=messages,
                response="".join(collected),
                tokens_prompt=0,
                tokens_completion=0,
                duration_ms=int((time.monotonic() - t0) * 1000),
                status="error",
                error=str(e),
                cell_id=meta.get("cell_id"),
                notebook_id=meta.get("notebook_id"),
            )
            logger.error(f"LLM stream failed: {e}")
            raise


llm_client = LLMClient()
