from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/datalab.db"

    # LLM
    litellm_model: str = "gpt-4o"
    openai_api_key: str = ""
    openai_api_base: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    llm_extra_models: str = "[]"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # Execution sandbox
    sandbox_timeout: int = 30
    sandbox_memory_mb: int = 512

    # CORS
    cors_origins: List[str] = ["http://localhost:5171", "http://localhost:5173", "http://localhost:3000"]

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    @property
    def data_dir(self) -> Path:
        p = Path("./data")
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def prompts_dir(self) -> Path:
        return Path(__file__).parent / "llm" / "prompts"

    def get_model_presets(self) -> list[dict[str, Any]]:
        """Build the list of available model presets from env config."""
        presets: list[dict[str, Any]] = []

        presets.append({
            "id": "default",
            "name": _display_name(self.litellm_model),
            "model": self.litellm_model,
            "api_key": self.openai_api_key or None,
            "api_base": self.openai_api_base or None,
        })

        if self.ollama_base_url and not self.litellm_model.startswith("ollama"):
            presets.append({
                "id": "ollama",
                "name": "Ollama (Local)",
                "model": "ollama_chat/glm-4.7-flash:latest",
                "api_base": self.ollama_base_url,
            })

        try:
            extras = json.loads(self.llm_extra_models)
            if isinstance(extras, list):
                for entry in extras:
                    if isinstance(entry, dict) and "id" in entry and "model" in entry:
                        entry.setdefault("name", _display_name(entry["model"]))
                        presets.append(entry)
        except json.JSONDecodeError:
            pass

        return presets


def _display_name(model_id: str) -> str:
    """Derive a human-friendly name from a LiteLLM model id."""
    clean = model_id.split("/")[-1]
    return clean.replace("-", " ").replace("_", " ").title()


settings = Settings()
