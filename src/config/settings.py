from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ThresholdSettings(BaseSettings):
    """Health and telemetry evaluation thresholds."""

    # Health status thresholds (in seconds)
    normal_health_threshold_seconds: int = Field(
        default=720,
        description="NORMAL mode: time after which sensor is considered FAULTY (12 minutes)",
    )
    emergency_health_threshold_seconds: int = Field(
        default=30,
        description="EMERGENCY mode: time after which sensor is considered FAULTY (30 seconds)",
    )

    # Telemetry status thresholds (in seconds)
    delayed_threshold_seconds: int = Field(
        default=120,
        description="Time difference to consider telemetry DELAYED (2 minutes)",
    )
    clock_skew_threshold_seconds: int = Field(
        default=30,
        description="Time difference to consider telemetry CLOCK_SKEW (30 seconds)",
    )

    model_config = SettingsConfigDict(
        env_prefix="THRESHOLD_",
        extra="ignore",
    )


class Settings(BaseSettings):
    app_name: str = "IoT Environment Monitoring API"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = Field(
        default="postgresql+psycopg://user:password@localhost:5432/iot_db"
    )
    test_database_url: str | None = None

    # Threshold settings
    thresholds: ThresholdSettings = Field(default_factory=ThresholdSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def effective_database_url(self) -> str:
        if self.app_env == "test" and self.test_database_url:
            return self.test_database_url
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
