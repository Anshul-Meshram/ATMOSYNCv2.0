from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    eccc_base_url: str = (
        "https://api.weather.gc.ca/collections/climate-daily/items"
    )

    scheduler_timezone: str = "Asia/Kolkata"
    daily_ingestion_hour: int = 2
    daily_ingestion_minute: int = 0
    enable_scheduler: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
