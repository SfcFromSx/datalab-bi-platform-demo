from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

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
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"

    # Execution sandbox
    sandbox_timeout: int = 30
    sandbox_memory_mb: int = 512

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Paths
    @property
    def data_dir(self) -> Path:
        p = Path("./data")
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def prompts_dir(self) -> Path:
        return Path(__file__).parent / "llm" / "prompts"


settings = Settings()
