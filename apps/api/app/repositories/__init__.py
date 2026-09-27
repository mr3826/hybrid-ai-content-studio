from app.repositories.base import BaseRepository
from app.repositories.job_repository import JobRepository
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.research_repository import ResearchRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.content_repository import ContentRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.asset_repository import AssetRepository

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
]
