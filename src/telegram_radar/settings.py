from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Telegram user client
    telegram_api_id: int
    telegram_api_hash: str
    telethon_session_path: Path = Path("data/telethon.session")

    # Telegram bot
    tg_bot_token: str
    tg_owner_user_id: int

    # Folder discovery
    radar_folder_name: str = "Radar"

    # Fetching
    fetch_since_hours: int = 24
    fetch_limit_per_channel: int = 50

    # Comments
    comments_limit_per_post: int = 10
    comment_max_len: int = 500
    post_max_len: int = 4000

    # Digest
    digest_max_items: int = 20
    deadline_urgent_days: int = 7

    # LLM
    llm_provider: str = "openai"
    llm_model: str
    llm_api_key: str
    llm_max_chars_per_batch: int = 12000
