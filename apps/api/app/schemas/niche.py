from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContentPillar(BaseModel):
    id: str = Field(..., description="Unique pillar identifier")
    name: str = Field(..., description="Pillar display name")
    description: str = Field(..., description="Description of covered topics")


class NicheProfileBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Niche name")
    one_sentence_definition: str = Field(..., min_length=5, description="Clear one-sentence summary of the niche")
    audience: str = Field(..., min_length=3, description="Target technical audience")
    audience_regions: List[str] = Field(default_factory=list)
    primary_problems: List[str] = Field(default_factory=list)
    allowed_topics: List[str] = Field(default_factory=list)
    adjacent_topics: List[str] = Field(default_factory=list)
    blocked_topics: List[str] = Field(default_factory=list)
    must_have_signals: List[str] = Field(default_factory=list)
    negative_keywords: List[str] = Field(default_factory=list)
    preferred_source_types: List[str] = Field(default_factory=list)
    content_pillars: List[ContentPillar] = Field(default_factory=list)
    commercial_intent_topics: List[str] = Field(default_factory=list)
    evergreen_topics: List[str] = Field(default_factory=list)


class NicheProfileCreate(NicheProfileBase):
    pass


class NicheProfileUpdate(NicheProfileBase):
    pass


class NicheProfileRead(NicheProfileBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
