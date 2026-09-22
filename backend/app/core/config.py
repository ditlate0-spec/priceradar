from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- PostgreSQL ---
    postgres_db: str = Field(default="priceradar")
    postgres_user: str = Field(default="priceradar")
    postgres_password: str = Field(default="priceradar_secret")
    postgres_host: str = Field(default="db")
    postgres_port: int = Field(default=5432)

    # --- Redis ---
    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)

    # --- Backend ---
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    # --- Fees (доли: 0.001 = 0.1%) ---
    fee_binance: float = Field(default=0.001)
    fee_bybit: float = Field(default=0.001)
    fee_okx: float = Field(default=0.001)

    # --- Thresholds ---
    threshold_version: str = Field(default="thresholds_v1")
    highlight_thresholds: str = Field(default="0.3,0.8,1.5,2.0")
    peak_thresholds: str = Field(default="0.3,0.5,1.0,2.0")
    minute_highlight_seconds: int = Field(default=30)

    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    telegram_enabled: bool = Field(default=False)
    telegram_min_threshold: float = Field(default=0.5)
    telegram_cooldown_minutes: int = Field(default=5)

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def database_url(self) -> str:
        """DSN для SQLAlchemy с asyncpg."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def highlight_thresholds_list(self) -> list[float]:
        return [float(x.strip()) for x in self.highlight_thresholds.split(",") if x.strip()]

    @property
    def peak_thresholds_list(self) -> list[float]:
        return [float(x.strip()) for x in self.peak_thresholds.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()