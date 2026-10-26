"""Application settings loaded via Pydantic BaseSettings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    perplexity_api_key: str = ""
    perplexity_model: str = "sonar-pro"
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    anki_connect_url: str = "http://127.0.0.1:8765"
    database_url: str = "sqlite:///./data/omnivore.db"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()