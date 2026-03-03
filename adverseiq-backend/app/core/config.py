from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    k2_api_key: str
    k2_base_url: str = "https://api.k2think.ai/v1"
    k2_model: str = "MBZUAI-IFM/K2-Think-v2"

    # Supabase HTTP client (no direct DB connection)
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Kept for reference; not used by the app at runtime
    database_url: str = ""
    frontend_url: str = "http://localhost:3000"

    # Rate limiting — stay under 20 RPM, track against 18 as buffer
    k2_rate_limit: int = 18
    k2_rate_window: int = 60  # seconds

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()