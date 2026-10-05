from app.repositories.base import BaseRepository
from app.repositories.job_repository import JobRepository
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.research_repository import ResearchRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.feed_repository import FeedRepository
from app.repositories.trend_repository import TrendRepository
from app.repositories.ai_repository import AIRepository
from app.repositories.originality_repository import OriginalityRepository
from app.repositories.content_family_repository import (
    ContentFamilyRepository,
    ContentItemRepository,
)
from app.repositories.script_repository import ScriptRepository
from app.repositories.export_repository import ExportRepository
from app.repositories.publishing_repository import PublishingRepository
from app.repositories.feedback_repository import FeedbackRepository

__all__ = [
    "BaseRepository",
    "JobRepository",
    "OpportunityRepository",
    "ResearchRepository",
    "EvidenceRepository",
    "ProjectRepository",
    "ContentRepository",
    "AnalyticsRepository",
    "AssetRepository",
    "FeedRepository",
    "TrendRepository",
    "AIRepository",
    "OriginalityRepository",
    "ContentFamilyRepository",
    "ContentItemRepository",
    "ScriptRepository",
    "ExportRepository",
    "PublishingRepository",
    "FeedbackRepository",
]

