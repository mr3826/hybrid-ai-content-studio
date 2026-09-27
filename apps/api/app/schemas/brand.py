from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class VisualIdentity(BaseModel):
    primary_font: str = "Inter"
    secondary_font: str = "JetBrains Mono"
    caption_style: str = "clean-mono-highlight"
    logo_path: str = ""
    intro_rule: str = "First 3 seconds must show immediate result or problem demonstration."
    outro_rule: str = "Max 5 seconds; clean CTA with link reference."
    thumbnail_rules: List[str] = Field(default_factory=list)


class BrandProfileBase(BaseModel):
    brand_name: str = Field(..., min_length=2, max_length=255)
    brand_promise: str = Field(..., min_length=5)
    audience: str = Field(..., min_length=3)

    tone: List[str] = Field(default_factory=list)
    voice_rules: List[str] = Field(default_factory=list)
    preferred_vocabulary: List[str] = Field(default_factory=list)
    avoid_vocabulary: List[str] = Field(default_factory=list)
    banned_cliches: List[str] = Field(default_factory=list)
    claim_rules: List[str] = Field(default_factory=list)

    cta_style: str = ""
    humor_policy: str = ""
    controversy_policy: str = ""
    sponsor_policy: str = ""
    affiliate_disclosure_style: str = ""

    # Monetization Metadata
    default_lead_magnet: str = ""
    newsletter_cta: str = ""
    digital_product_cta: str = ""

    visual_identity: Dict[str, Any] = Field(default_factory=dict)
    platform_adaptations: Dict[str, Any] = Field(default_factory=dict)


class BrandProfileCreate(BrandProfileBase):
    pass


class BrandProfileUpdate(BrandProfileBase):
    pass


class BrandProfileRead(BrandProfileBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrandExemplarBase(BaseModel):
    category: str = Field(
        ...,
        description="approved_hook, approved_script, approved_caption, do_example, dont_example",
    )
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=2)
    context_note: Optional[str] = None
    platform: str = "all"


class BrandExemplarCreate(BrandExemplarBase):
    pass


class BrandExemplarRead(BrandExemplarBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BrandMemoryBase(BaseModel):
    memory_type: str = Field(
        ...,
        description="hook, cta, topic, tested_product, conclusion, visual_pattern, frequent_phrase, thumbnail_wording",
    )
    content: str = Field(..., min_length=2)
    context_note: Optional[str] = None
    usage_count: int = 1


class BrandMemoryCreate(BrandMemoryBase):
    pass


class BrandMemoryRead(BrandMemoryBase):
    id: str
    last_used_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

