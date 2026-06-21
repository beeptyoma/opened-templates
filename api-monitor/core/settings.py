from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "API Monitoring Platform"
    DEBUG: bool = False

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # пороги мониторинга
    DEFAULT_CHECK_INTERVAL_SECONDS: int = 60
    DEGRADED_RESPONSE_TIME_MS: int = 1000

    # два таймаута на HTTP-чек: отдельно на коннект, отдельно на чтение ответа
    HTTP_CONNECT_TIMEOUT_SECONDS: float = 5.0
    HTTP_READ_TIMEOUT_SECONDS: float = 10.0

    # сколько последних чеков смотрим при определении degraded (флапает/не флапает)
    DEGRADED_LOOKBACK_CHECKS: int = 5

    # кэш
    CACHE_TTL_STATS_SECONDS: int = 30
    CACHE_TTL_DASHBOARD_SECONDS: int = 15

    # rate limit
    RATE_LIMIT_PER_MINUTE: int = 60

    # опционально
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

settings = Settings()
