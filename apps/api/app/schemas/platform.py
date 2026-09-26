from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlatformSettingBase(BaseModel):
    platform: str = Field(..., description="youtube, facebook, instagram, tiktok")
    channel_name: str = ""
    channel_url: str = ""
    publishing_url: str = ""
    account_handle: str = ""
    is_active: bool = True

    @field_validator("channel_url", "publishing_url", mode="before")
    @classmethod
    def validate_https_url(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        v = v.strip()
        if v and not v.startswith("https://"):
            raise ValueError(f"Platform URLs must use HTTPS: received '{v}'")
        return v


class PlatformSettingUpdate(PlatformSettingBase):
    pass


class PlatformSettingRead(PlatformSettingBase):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformSettingsMap(BaseModel):
    platforms: Dict[str, PlatformSettingRead]
