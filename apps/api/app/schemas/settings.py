from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from app.schemas.brand import (
    BrandExemplarBase,
    BrandExemplarRead,
    BrandProfileBase,
    BrandProfileRead,
)
from app.schemas.niche import NicheProfileBase, NicheProfileRead
from app.schemas.platform import PlatformSettingBase, PlatformSettingRead


class StudioStatusRead(BaseModel):
    niche_configured: bool
    brand_configured: bool
    platforms_configured_count: int
    is_setup_completed: bool
    discovery_ready: bool
    generation_ready: bool
    active_niche_name: Optional[str] = None
    active_brand_name: Optional[str] = None


class ConfigExport(BaseModel):
    exported_at: datetime
    studio_version: str
    niche: Optional[NicheProfileRead] = None
    brand: Optional[BrandProfileRead] = None
    exemplars: List[BrandExemplarRead] = []
    platforms: Dict[str, PlatformSettingRead] = {}


class ConfigImport(BaseModel):
    niche: Optional[NicheProfileBase] = None
    brand: Optional[BrandProfileBase] = None
    exemplars: Optional[List[BrandExemplarBase]] = None
    platforms: Optional[Dict[str, PlatformSettingBase]] = None
