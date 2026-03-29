from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "speedtest-local"
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    database_url: str = Field(
        default="postgresql+psycopg://speedtest:speedtest@localhost:5432/speedtest",
        validation_alias="DATABASE_URL",
    )
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS",
    )
    server_label: str = Field(default="default", validation_alias="SERVER_LABEL")
    download_max_bytes: int = Field(default=536_870_912, validation_alias="DOWNLOAD_MAX_BYTES")  # 512 MiB
    upload_max_bytes: int = Field(default=536_870_912, validation_alias="UPLOAD_MAX_BYTES")
    default_download_duration_sec: float = Field(default=10.0, validation_alias="DEFAULT_DOWNLOAD_DURATION_SEC")
    default_upload_duration_sec: float = Field(default=10.0, validation_alias="DEFAULT_UPLOAD_DURATION_SEC")
    default_parallel_streams: int = Field(default=4, validation_alias="DEFAULT_PARALLEL_STREAMS")
    default_payload_bytes: int = Field(default=16_777_216, validation_alias="DEFAULT_PAYLOAD_BYTES")  # 16 MiB
    default_ping_samples: int = Field(default=30, validation_alias="DEFAULT_PING_SAMPLES")
    default_warmup_ping_samples: int = Field(default=5, validation_alias="DEFAULT_WARMUP_PING_SAMPLES")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    enable_metrics: bool = Field(default=True, validation_alias="ENABLE_METRICS")
    retention_days_placeholder: int = Field(default=365, validation_alias="RETENTION_DAYS_PLACEHOLDER")
    admin_prune_token: str = Field(default="", validation_alias="ADMIN_PRUNE_TOKEN")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: str | list[str]) -> str:
        if isinstance(v, list):
            return ",".join(v)
        return v

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
