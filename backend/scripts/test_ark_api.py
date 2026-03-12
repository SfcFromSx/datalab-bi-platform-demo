#!/usr/bin/env python3
"""
Test script for Volcengine Ark (OpenAI-compatible) API.

Usage (from backend directory):
  uv run python scripts/test_ark_api.py
  # or with explicit env:
  OPENAI_API_KEY=your-key OPENAI_API_BASE=https://ark.cn-beijing.volces.com/api/coding/v3 uv run python scripts/test_ark_api.py

Expects .env in backend/ with OPENAI_API_KEY and OPENAI_API_BASE set.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Load backend .env
backend_root = Path(__file__).resolve().parent.parent
env_file = backend_root / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)
else:
    print("Warning: no .env found at", env_file, file=sys.stderr)

API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
API_BASE = os.environ.get("OPENAI_API_BASE", "https://ark.cn-beijing.volces.com/api/coding/v3").strip().rstrip("/")
MODEL = os.environ.get("LITELLM_MODEL", "openai/ark-code-latest").strip()


async def test_completion():
    import litellm
    print("Test 1: completion (no stream)")
    print("  model:", MODEL)
    print("  api_base:", API_BASE)
    if not API_KEY:
        print("  ERROR: OPENAI_API_KEY not set")
        return False
    try:
        r = await litellm.acompletion(
            model=MODEL,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            api_key=API_KEY,
            api_base=API_BASE,
            timeout=30.0,
            drop_params=True,
        )
        text = (r.choices[0].message.content or "").strip()
        print("  response:", text[:200])
        print("  PASS")
        return True
    except Exception as e:
        print("  FAIL:", type(e).__name__, str(e))
        return False


async def test_stream():
    import litellm
    print("\nTest 2: stream")
    try:
        r = await litellm.acompletion(
            model=MODEL,
            messages=[{"role": "user", "content": "Say hello in one short sentence."}],
            api_key=API_KEY,
            api_base=API_BASE,
            stream=True,
            timeout=30.0,
            drop_params=True,
            temperature=0.0,
            max_tokens=4096,
        )
        chunks = []
        async for chunk in r:
            delta = chunk.choices[0].delta.content
            if delta:
                chunks.append(delta)
        text = "".join(chunks).strip()
        print("  response:", text[:200])
        print("  PASS")
        return True
    except Exception as e:
        print("  FAIL:", type(e).__name__, str(e))
        return False


async def main():
    print("Ark API test (OpenAI-compatible)")
    print("=" * 50)
    ok1 = await test_completion()
    ok2 = await test_stream()
    print("=" * 50)
    if ok1 and ok2:
        print("All tests passed.")
        return 0
    print("Some tests failed.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
