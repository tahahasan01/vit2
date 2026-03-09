"""
Configuration — pydantic-settings based, loaded from .env
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
MOCK_DIR = ASSETS_DIR / "mock"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# ── Sub-models ───────────────────────────────────────────────────────────
class SupabaseSettings(BaseSettings):
    url: str = Field("", alias="SUPABASE_URL")
    anon_key: str = Field("", alias="SUPABASE_ANON_KEY")
    service_role_key: str = Field("", alias="SUPABASE_SERVICE_ROLE_KEY")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Bucket names
    bucket_avatars: str = "avatars"
    bucket_garments: str = "garments"
    bucket_results: str = "tryon-results"
    bucket_uploads: str = "user-uploads"


class ReplicateSettings(BaseSettings):
    api_token: str = Field("", alias="REPLICATE_API_TOKEN")
    vto_model_id: str = Field("cuuupid/idm-vton", alias="VTO_MODEL_ID")
    vto_fallback_model_id: str = Field(
        "subhash25rawat/flux-vton", alias="VTO_FALLBACK_MODEL_ID"
    )
    trellis_model_id: str = Field("firtoz/trellis", alias="TRELLIS_MODEL_ID")
    video_model_id: str = Field(
        "wan-video/wan-2.2-i2v-fast", alias="VIDEO_MODEL_ID"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class RedisSettings(BaseSettings):
    url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class PipelineSettings(BaseSettings):
    hmr_space_url: str = Field(
        "https://brjathu-hmr2-0.hf.space", alias="HMR_SPACE_URL"
    )
    timeout_seconds: int = Field(300, alias="PIPELINE_TIMEOUT_SECONDS")
    max_concurrent_jobs: int = Field(10, alias="MAX_CONCURRENT_JOBS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# ── Root settings ────────────────────────────────────────────────────────
class Settings(BaseSettings):
    """Central application settings — single source of truth."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General
    environment: Environment = Field(
        Environment.DEVELOPMENT, alias="ENVIRONMENT"
    )
    use_stubs: bool = Field(True, alias="USE_STUBS")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(
        "http://localhost:5173,http://localhost:3000", alias="CORS_ORIGINS"
    )

    # Sub-configs (composed)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    replicate: ReplicateSettings = Field(default_factory=ReplicateSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)

    # ── Derived ──────────────────────────────────────────────────────
    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
