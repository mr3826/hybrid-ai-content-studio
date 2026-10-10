import os
from pathlib import Path
from typing import Any, List, Optional, Union
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_gemini_api_key(configured_value: Any, environ: Any = None) -> Optional[str]:
    """Resolve Gemini credentials with explicit process variables ahead of dotenv."""
    environment = os.environ if environ is None else environ
    candidates = (
        environment.get("CONTENT_STUDIO_GEMINI"),
        environment.get("GEMINI_API_KEY"),
        environment.get("GEMINI_KEY"),
        environment.get("GOOGLE_API_KEY"),
        configured_value,
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8400

    DATABASE_URL: str = "sqlite+aiosqlite:///data/db/studio.sqlite"
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    STORAGE_BASE_DIR: str = "data"

    # Cost Controls
    MAX_AI_COST_PER_DAY: float = 5.00
    MAX_GENERATION_COST_PER_PROJECT: float = 2.00
    MAX_VIDEO_SECONDS_PER_PROJECT: int = 180

    # Provider Mode Flags
    AI_MOCK_MODE: bool = True
    TTS_MOCK_MODE: bool = False
    FFMPEG_BINARY: str = "ffmpeg"

    # AI Provider Settings
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GEMINI_KEY", "GOOGLE_API_KEY"),
    )
    GEMINI_MODEL: str = "gemini-3.8-flash"

    @model_validator(mode="before")
    @classmethod
    def populate_defaults_from_env(cls, values: Any) -> Any:
        if isinstance(values, dict):
            values["GEMINI_API_KEY"] = _resolve_gemini_api_key(
                values.get("GEMINI_API_KEY")
            )
        return values

    # Manual Publishing Platform Default URLs
    PLATFORM_YOUTUBE_STUDIO_URL: str = "https://studio.youtube.com/"
    PLATFORM_FACEBOOK_URL: str = "https://www.facebook.com/"
    PLATFORM_INSTAGRAM_URL: str = "https://www.instagram.com/"
    PLATFORM_TIKTOK_URL: str = "https://www.tiktok.com/upload"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def anchor_database_url(cls, v: str) -> str:
        if v.startswith("sqlite+aiosqlite:///") and not v.startswith("sqlite+aiosqlite:///:memory:"):
            raw_path = v.replace("sqlite+aiosqlite:///", "")
            path_obj = Path(raw_path)
            if not path_obj.is_absolute():
                # Find repo root
                root = Path(__file__).resolve()
                for p in root.parents:
                    if (p / "apps").exists() and (p / "docs").exists():
                        root = p
                        break
                abs_db = (root / raw_path).resolve()
                return f"sqlite+aiosqlite:///{abs_db.as_posix()}"
        return v

    @property
    def storage_path(self) -> Path:
        return Path(self.STORAGE_BASE_DIR)


settings = Settings()
