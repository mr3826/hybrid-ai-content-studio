import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content_family import ContentFamily, ContentItem, ContentItemEvidenceSelection
from app.models.evidence import Claim
from app.repositories.base import BaseRepository

VALID_FAMILY_STATUSES = ["DRAFT", "READY_FOR_CONTENT", "ACTIVE", "COMPLETED", "ARCHIVED"]

VALID_CHILD_STATUSES = [
    "PLANNED",
    "DRAFT",
    "SCRIPT_REVIEW",
    "SCRIPT_APPROVED",
    "READY_FOR_EXPORT",
    "EXPORTED",
    "READY_TO_PUBLISH",
    "PUBLISHED",
    "REJECTED",
]

VALID_FORMATS = [
    "short_vertical",
    "youtube_long",
    "social_post",
    "newsletter",
    "article",
]

VALID_PLATFORMS = [
    "youtube",
    "facebook",
    "instagram",
    "tiktok",
    "cross_platform",
    "none",
]


class ContentFamilyRepository(BaseRepository[ContentFamily]):
    """Repository managing Content Families (one research/evidence/originality investment
    generating multiple format/platform child items).
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^\w\s-]", "", text).strip().lower()
        return re.sub(r"[-\s]+", "-", s)[:200]

    async def create_family(
        self,
        title: str,
        content_pillar: str = "Core",
        original_value_type: str = "benchmark",
        summary: str = "",
        topic_id: Optional[str] = None,
        research_packet_id: Optional[str] = None,
        originality_plan_id: Optional[str] = None,
        primary_experiment_id: Optional[str] = None,
        status: str = "DRAFT",
        research_cost: float = 0.0,
        experiment_cost: float = 0.0,
        ai_cost: float = 0.0,
        media_cost: float = 0.0,
        manual_time_minutes: int = 0,
        local_compute_seconds: float = 0.0,
    ) -> ContentFamily:
        slug = f"{self._slugify(title)}-{uuid.uuid4().hex[:6]}"
        family = ContentFamily(
            id=str(uuid.uuid4()),
            title=title,
            slug=slug,
            topic_id=topic_id,
            research_packet_id=research_packet_id,
            originality_plan_id=originality_plan_id,
            primary_experiment_id=primary_experiment_id,
            status=status if status in VALID_FAMILY_STATUSES else "DRAFT",
            content_pillar=content_pillar,
            original_value_type=original_value_type,
            summary=summary,
            research_cost=research_cost,
            experiment_cost=experiment_cost,
            ai_cost=ai_cost,
            media_cost=media_cost,
            manual_time_minutes=manual_time_minutes,
            local_compute_seconds=local_compute_seconds,
        )
        self.session.add(family)
        await self.session.commit()
        await self.session.refresh(family)
        return family

    async def get_family(self, family_id: str) -> Optional[ContentFamily]:
        query = (
            select(ContentFamily)
            .where(ContentFamily.id == family_id)
            .options(
                selectinload(ContentFamily.opportunity),
                selectinload(ContentFamily.research_packet),
                selectinload(ContentFamily.originality_plan),
                selectinload(ContentFamily.primary_experiment),
                selectinload(ContentFamily.items).selectinload(
                    ContentItem.evidence_selections
                ).selectinload(ContentItemEvidenceSelection.claim),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_family_by_slug(self, slug: str) -> Optional[ContentFamily]:
        query = (
            select(ContentFamily)
            .where(ContentFamily.slug == slug)
            .options(
                selectinload(ContentFamily.items).selectinload(
                    ContentItem.evidence_selections
                ).selectinload(ContentItemEvidenceSelection.claim),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_families(
        self,
        status: Optional[str] = None,
        content_pillar: Optional[str] = None,
        topic_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ContentFamily]:
        query = (
            select(ContentFamily)
            .options(
                selectinload(ContentFamily.items),
                selectinload(ContentFamily.opportunity),
                selectinload(ContentFamily.research_packet),
                selectinload(ContentFamily.originality_plan),
            )
            .order_by(desc(ContentFamily.created_at))
        )
        if status:
            query = query.where(ContentFamily.status == status)
        if content_pillar:
            query = query.where(ContentFamily.content_pillar == content_pillar)
        if topic_id:
            query = query.where(ContentFamily.topic_id == topic_id)

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_family(self, family_id: str, **kwargs) -> Optional[ContentFamily]:
        family = await self.get_family(family_id)
        if not family:
            return None

        for k, v in kwargs.items():
            if hasattr(family, k) and v is not None:
                setattr(family, k, v)

        family.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(family)
        return family

    async def approve_family(self, family_id: str, reviewer: str = "creator") -> ContentFamily:
        family = await self.get_family(family_id)
        if not family:
            raise ValueError(f"ContentFamily {family_id} not found.")

        family.status = "READY_FOR_CONTENT"
        family.approved_at = datetime.now(timezone.utc)
        family.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(family)
        return family

    async def archive_family(self, family_id: str) -> ContentFamily:
        family = await self.get_family(family_id)
        if not family:
            raise ValueError(f"ContentFamily {family_id} not found.")

        family.status = "ARCHIVED"
        family.archived_at = datetime.now(timezone.utc)
        family.updated_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(family)
        return family

    async def calculate_economics(self, family_id: str) -> Dict[str, Any]:
        """Calculate shared vs incremental costs and cost-per-child metrics."""
        family = await self.get_family(family_id)
        if not family:
            raise ValueError(f"ContentFamily {family_id} not found.")

        shared_cost = (
            family.research_cost
            + family.experiment_cost
            + family.ai_cost
            + family.media_cost
        )
        shared_time = family.manual_time_minutes
        shared_compute = family.local_compute_seconds

        total_incremental_cost = sum(item.incremental_cost for item in family.items)
        total_child_time = sum(item.manual_time_minutes for item in family.items)
        total_child_compute = sum(item.local_compute_seconds for item in family.items)

        total_family_cost = shared_cost + total_incremental_cost
        total_time_minutes = shared_time + total_child_time
        total_compute_seconds = shared_compute + total_child_compute

        item_count = len(family.items)
        cost_per_child = (
            (total_family_cost / item_count) if item_count > 0 else total_family_cost
        )

        return {
            "family_id": family_id,
            "item_count": item_count,
            "shared_family_cost": round(shared_cost, 4),
            "shared_manual_time_minutes": shared_time,
            "shared_compute_seconds": round(shared_compute, 2),
            "total_incremental_cost": round(total_incremental_cost, 4),
            "total_family_cost": round(total_family_cost, 4),
            "cost_per_child": round(cost_per_child, 4),
            "total_time_minutes": total_time_minutes,
            "total_compute_seconds": round(total_compute_seconds, 2),
            "roi_ratio": 0.0,  # Revenue tracking baseline for later phases
        }


class ContentItemRepository(BaseRepository[ContentItem]):
    """Repository managing child content items and their evidence selections."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_item(
        self,
        content_family_id: str,
        format: str,
        working_title: str,
        angle: str,
        platform_target: str = "youtube",
        hook_type: str = "bold_claim",
        status: str = "PLANNED",
        incremental_cost: float = 0.0,
        manual_time_minutes: int = 0,
        local_compute_seconds: float = 0.0,
        original_value_connection: str = "",
        viewer_value: str = "",
        claim_ids: Optional[List[str]] = None,
    ) -> ContentItem:
        if status not in VALID_CHILD_STATUSES:
            status = "PLANNED"

        item = ContentItem(
            id=str(uuid.uuid4()),
            content_family_id=content_family_id,
            format=format,
            platform_target=platform_target,
            working_title=working_title,
            angle=angle,
            hook_type=hook_type,
            status=status if status in VALID_CHILD_STATUSES else "PLANNED",
            incremental_cost=incremental_cost,
            manual_time_minutes=manual_time_minutes,
            local_compute_seconds=local_compute_seconds,
            original_value_connection=original_value_connection,
            viewer_value=viewer_value,
        )
        self.session.add(item)
        await self.session.flush()

        if claim_ids:
            for claim_id in claim_ids:
                selection = ContentItemEvidenceSelection(
                    id=str(uuid.uuid4()),
                    content_item_id=item.id,
                    claim_id=claim_id,
                    is_primary=False,
                )
                self.session.add(selection)

        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_item(self, item_id: str) -> Optional[ContentItem]:
        query = (
            select(ContentItem)
            .where(ContentItem.id == item_id)
            .options(
                selectinload(ContentItem.family),
                selectinload(ContentItem.evidence_selections).selectinload(
                    ContentItemEvidenceSelection.claim
                ),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_items(
        self,
        content_family_id: str,
        status: Optional[str] = None,
        format: Optional[str] = None,
        platform_target: Optional[str] = None,
    ) -> List[ContentItem]:
        query = (
            select(ContentItem)
            .where(ContentItem.content_family_id == content_family_id)
            .options(
                selectinload(ContentItem.evidence_selections).selectinload(
                    ContentItemEvidenceSelection.claim
                )
            )
            .order_by(ContentItem.created_at)
        )
        if status:
            query = query.where(ContentItem.status == status)
        if format:
            query = query.where(ContentItem.format == format)
        if platform_target:
            query = query.where(ContentItem.platform_target == platform_target)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_item(self, item_id: str, **kwargs) -> Optional[ContentItem]:
        item = await self.get_item(item_id)
        if not item:
            return None

        if kwargs.get("status") and kwargs["status"] not in VALID_CHILD_STATUSES:
            raise ValueError(f"Invalid child status: {kwargs['status']}")

        # SCRIPT_APPROVED can only be reached through the Script Studio approval gate
        if kwargs.get("status") == "SCRIPT_APPROVED":
            raise ValueError(
                "SCRIPT_APPROVED status cannot be set directly. "
                "Use the Script Studio approval flow (POST /scripts/{id}/approve) instead."
            )

        for k, v in kwargs.items():
            if hasattr(item, k) and v is not None:
                setattr(item, k, v)

        item.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete_item(self, item_id: str) -> bool:
        item = await self.get_item(item_id)
        if not item:
            return False

        await self.session.delete(item)
        await self.session.commit()
        return True

    async def link_evidence(
        self,
        content_item_id: str,
        claim_id: str,
        relevance_note: Optional[str] = None,
        is_primary: bool = False,
    ) -> ContentItemEvidenceSelection:
        """Link an existing claim to this child item without duplicating the claim record."""
        # Check if already linked
        existing = await self.session.execute(
            select(ContentItemEvidenceSelection).where(
                ContentItemEvidenceSelection.content_item_id == content_item_id,
                ContentItemEvidenceSelection.claim_id == claim_id,
            )
        )
        existing_sel = existing.scalar_one_or_none()
        if existing_sel:
            existing_sel.relevance_note = relevance_note
            existing_sel.is_primary = is_primary
            await self.session.commit()
            await self.session.refresh(existing_sel)
            return existing_sel

        selection = ContentItemEvidenceSelection(
            id=str(uuid.uuid4()),
            content_item_id=content_item_id,
            claim_id=claim_id,
            relevance_note=relevance_note,
            is_primary=is_primary,
        )
        self.session.add(selection)
        await self.session.commit()
        await self.session.refresh(selection)
        return selection

    async def unlink_evidence(self, content_item_id: str, claim_id: str) -> bool:
        result = await self.session.execute(
            select(ContentItemEvidenceSelection).where(
                ContentItemEvidenceSelection.content_item_id == content_item_id,
                ContentItemEvidenceSelection.claim_id == claim_id,
            )
        )
        sel = result.scalar_one_or_none()
        if not sel:
            return False
        await self.session.delete(sel)
        await self.session.commit()
        return True

    async def get_selected_claims(self, content_item_id: str) -> List[Claim]:
        query = (
            select(Claim)
            .join(
                ContentItemEvidenceSelection,
                ContentItemEvidenceSelection.claim_id == Claim.id,
            )
            .where(ContentItemEvidenceSelection.content_item_id == content_item_id)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
