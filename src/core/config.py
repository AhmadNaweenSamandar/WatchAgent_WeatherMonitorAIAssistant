from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"

    # Automatically load from a local .env file if it exists
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Global configuration instance
settings = Settings()