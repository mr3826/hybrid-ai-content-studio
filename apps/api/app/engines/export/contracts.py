from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PublishingChecklist(BaseModel):
    """The 7-point pre-publication quality and compliance checklist."""
    media_ready: bool = Field(default=False, description="Final media render or companion graphic verified")
    thumbnail_ready: bool = Field(default=False, description="Eye-catching thumbnail rendered and checked")
    title_caption_ready: bool = Field(default=True, description="Platform-tailored title, description, and hashtags approved")
    sources_checked: bool = Field(default=True, description="Primary sources and citations fact-checked")
    affiliate_disclosure_needed: bool = Field(default=False, description="Affiliate/promotional disclosures declared")
    ai_disclosure_recommended: bool = Field(default=True, description="Transparent AI-assistance declared")
    asset_rights_verified: bool = Field(default=True, description="Visual, audio, and font rights confirmed")

    model_config = ConfigDict(from_attributes=True)


class PlatformPackageData(BaseModel):
    """Metadata tailored for a specific social or video distribution platform."""
    platform: str
    status: str = Field(default="NOT_READY")
    title: str = Field(default="")
    caption: str = Field(default="")
    hashtags: List[str] = Field(default_factory=list)
    pinned_comment: str = Field(default="")
    checklist: Dict[str, bool] = Field(default_factory=dict)
    files_generated: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ExportEngineInput(BaseModel):
    """Input payload for ExportEngine package generation."""
    content_item_id: str
    working_title: str
    slug: str
    format: str
    platform_target: str = "youtube"
    script_id: Optional[str] = None
    script_version: int = 1
    script_title: str = ""
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    brand_name: str = "Fresh Local Content"
    brand_tone: str = "authoritative, practical, direct"
    banned_cliches: List[str] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    originality_summary: str = ""
    experiments: List[Dict[str, Any]] = Field(default_factory=list)
    engine_versions: Dict[str, str] = Field(default_factory=dict)
    dry_run: bool = False

    model_config = ConfigDict(from_attributes=True)


class ExportPackageOutput(BaseModel):
    """Output contract produced by ExportEngine."""
    package_id: str
    package_slug: str
    export_dir: str
    files: List[str] = Field(default_factory=list)
    checksum: str
    manifest_data: Dict[str, Any] = Field(default_factory=dict)
    platform_packages: Dict[str, PlatformPackageData] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
