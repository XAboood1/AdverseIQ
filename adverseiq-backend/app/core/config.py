from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    k2_api_key: str

    # Standard endpoint — Rapid Check and Mechanism Trace
    k2_base_url: str = "https://api.k2think.ai/v1"
    k2_model: str = "MBZUAI-IFM/K2-Think-v2"

    # Agentic endpoint — Mystery Solver only
    k2_build_url: str = "https://build-api.k2think.ai/v1"
    k2_build_model: str = "MBZUAI-IFM/K2-V2-Instruct"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    database_url: str = ""
    frontend_url: str = "*"

    # Rate limiting — build-api rate limit unknown; conservative threshold
    k2_rate_limit: int = 15
    k2_rate_window: int = 60  # seconds


@lru_cache()
def get_settings() -> Settings:
    return Settings()