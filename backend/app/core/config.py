from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AEGIS_", env_file=".env", extra="ignore")

    app_name: str = "AegisLocal"
    debug: bool = True
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_enabled: bool = False  # MVP: in-memory fallback when Redis absent

    allow_threshold: float = 0.35
    challenge_threshold: float = 0.65

    pow_default_difficulty: int = 16  # leading zero bits
    pow_ttl_seconds: int = 120

    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
