from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExportPackageRead(BaseModel):
    id: str
    content_item_id: str
    package_slug: str
    export_dir: str
    manifest_data: Dict[str, Any]
    files: List[str]
    checksum: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformPublicationRead(BaseModel):
    id: str
    content_item_id: str
    export_package_id: Optional[str] = None
    platform: str
    status: str
    title: str
    caption: str
    hashtags: List[str]
    pinned_comment: str
    checklist: Dict[str, Any]
    published_at: Optional[datetime] = None
    post_url: Optional[str] = None
    platform_post_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformPublicationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="NOT_READY, READY, PUBLISHED, SKIPPED")
    title: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    pinned_comment: Optional[str] = None
    checklist: Optional[Dict[str, bool]] = None
    published_at: Optional[datetime] = None
    post_url: Optional[str] = Field(None, description="Must be a valid HTTPS URL")
    platform_post_id: Optional[str] = None
    notes: Optional[str] = None


class PublishingOverviewResponse(BaseModel):
    content_item: Dict[str, Any]
    export_package: Optional[ExportPackageRead] = None
    publications: List[PlatformPublicationRead]
    platform_launch_urls: Dict[str, str] = Field(default_factory=dict)
