from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List, Union

class Settings(BaseSettings):
    """
    Centralized application settings using Pydantic.
    Settings are loaded from environment variables. Case-insensitive.
    """
    # Application Metadata
    APP_NAME: str = "HWA Dashboard"
    APP_VERSION: str = "2.0.0"

    # Environment Configuration
    APP_ENV: str = "production"  # "development" or "production"
    TESTING: bool = False
    FORCE_CONSOLE_MODE: bool = False

    # Server Configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 63136

    # HWA Connection Configuration
    HWA_HOSTNAME: str
    HWA_PORT: int = 31116
    HWA_USERNAME: str
    HWA_PASSWORD: str

    # Database and Redis Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./hwa_dashboard.db"
    REDIS_URL: str = "redis://localhost:6379"

    # Celery result backend override for testing
    CELERY_RESULT_BACKEND_OVERRIDE: str = ""

    # Monitoring Configuration
    CRITICAL_STATUSES: List[str] = ["ABEND", "ERROR", "FAIL"]
    MONITORING_POLL_INTERVAL: int = 30
    HWA_HOW_MANY_LIMIT: int = 500

    # Security Configuration
    API_KEY: str = "default_api_key"  # A default key for development
    CORS_ALLOWED_ORIGINS: Union[List[str], str] = []

    # Model and Layout Path Overrides (primarily for testing)
    LAYOUT_FILE_OVERRIDE: str = ""
    MODEL_DIR_OVERRIDE: str = ""
    FORECAST_MODEL_DIR_OVERRIDE: str = ""

    @property
    def BASE_URL(self) -> str:
        return f"http://{self.SERVER_HOST}:{self.SERVER_PORT}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

# Instantiate the settings object that will be used throughout the application
settings = Settings()