from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "jamaat_bot"
    postgres_user: str = "jamaat_bot"
    postgres_password: str = ""

    dumk_api_base_url: str = "https://api.muftyat.kz"

    log_level: str = "INFO"

    scheduler_tick_seconds: int = 60
    notification_stale_threshold_minutes: int = 10
    schedule_horizon_days: int = 35
    schedule_refresh_interval_hours: int = 6
    nearest_city_threshold_km: float = 80.0

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
