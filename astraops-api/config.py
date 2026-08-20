from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "AstraOps API"
    app_version: str = "0.1.0"
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # CelesTrak
    celestrak_gp_url: str = "https://celestrak.org/gp.php"

    # NASA DONKI
    nasa_donki_base_url: str = "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get"
    nasa_api_key: str = "DEMO_KEY"

    # Cache TTL (seconds)
    tle_cache_ttl: int = 3600          # 1 hour
    spaceweather_cache_ttl: int = 900  # 15 minutes
    conjunction_cache_ttl: int = 1800  # 30 minutes

    # HTTP client timeouts (seconds)
    http_timeout: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
