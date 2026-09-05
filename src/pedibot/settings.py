"""Runtime settings, loaded from `.env` (never committed). See `.env.example`."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_vision_model: str = "deepseek-v4-flash-vision-exp"
    photo_enabled: bool = True
    deepseek_base_url: str = "https://api.deepseek.com"
    # USD per 1M tokens (cache miss). Updated by hand; see PRD §11.
    llm_price_in_per_m: float = 0.14
    llm_price_out_per_m: float = 0.28
    max_daily_llm_usd: float = 2.0

    # Index
    index_db_path: Path = ROOT / "index" / "pedibot.db"
    retrieval_top_k: int = 6
    retrieval_min_terms: int = 1

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8601
    allowed_origins: str = "http://localhost:4321"
    rate_limit_per_10min: int = 20
    rate_limit_per_day: int = 200
    ops_db_path: Path = ROOT / "data" / "pedibot_ops.db"

    # Telegram (public chatbot; alerts use TELEGRAM_BOT_TOKEN in ops/watchdog.py)
    telegram_public_bot_token: str = ""

    # Config files
    config_dir: Path = ROOT / "config"
    # Where `pedibot publish` writes the guides. The engine reads it so an answer can link
    # to the guide built from the same sources.
    content_dir: Path = ROOT / "web" / "content"


def get_settings() -> Settings:
    return Settings()
