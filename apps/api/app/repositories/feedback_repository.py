import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import FeedbackLesson
from app.models.brand import BrandProfile, BrandMemoryItem, BrandExemplar, SINGLETON_BRAND_ID
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[FeedbackLesson]):
    """Storage repository boundary for creator feedback lessons and brand memory updates."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_lesson(self, data: Dict[str, Any]) -> FeedbackLesson:
        """Create and persist a new feedback lesson proposal."""
        lesson = FeedbackLesson(
            id=data.get("id") or str(uuid.uuid4()),
            content_item_id=data.get("content_item_id"),
            lesson_type=data["lesson_type"],
            title=data["title"],
            observation=data["observation"],
            impact_level=data.get("impact_level", "MEDIUM"),
            confidence_score=data.get("confidence_score", 0.8),
            evidence_data=data.get("evidence_data", {}),
            proposed_adjustment=data.get("proposed_adjustment", {}),
            status=data.get("status", "PENDING"),
            creator_notes=data.get("creator_notes"),
        )
        self.session.add(lesson)
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def get_lesson(self, lesson_id: str) -> Optional[FeedbackLesson]:
        """Fetch single feedback lesson by ID."""
        stmt = select(FeedbackLesson).where(FeedbackLesson.id == lesson_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_lessons(
        self,
        status: Optional[str] = None,
        lesson_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[FeedbackLesson]:
        """List feedback lessons filtered by status and/or lesson type."""
        stmt = select(FeedbackLesson)
        if status:
            stmt = stmt.where(FeedbackLesson.status == status)
        if lesson_type:
            stmt = stmt.where(FeedbackLesson.lesson_type == lesson_type)
        stmt = stmt.order_by(FeedbackLesson.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def approve_lesson(self, lesson_id: str, creator_notes: Optional[str] = None) -> Optional[FeedbackLesson]:
        """Human approval gate: Creator approves a proposed lesson."""
        lesson = await self.get_lesson(lesson_id)
        if not lesson:
            return None
        lesson.status = "APPROVED"
        lesson.reviewed_at = datetime.now(timezone.utc)
        if creator_notes:
            lesson.creator_notes = creator_notes
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def reject_lesson(self, lesson_id: str, creator_notes: Optional[str] = None) -> Optional[FeedbackLesson]:
        """Human approval gate: Creator rejects a proposed lesson."""
        lesson = await self.get_lesson(lesson_id)
        if not lesson:
            return None
        lesson.status = "REJECTED"
        lesson.reviewed_at = datetime.now(timezone.utc)
        if creator_notes:
            lesson.creator_notes = creator_notes
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def apply_lesson(self, lesson_id: str) -> Optional[FeedbackLesson]:
        """Apply an approved lesson directly to Brand DNA (BrandProfile or BrandMemoryItem or BrandExemplar)."""
        lesson = await self.get_lesson(lesson_id)
        if not lesson:
            return None

        adj = lesson.proposed_adjustment or {}
        target = adj.get("target")
        field = adj.get("field")
        action = adj.get("action")
        value = adj.get("value")

        if target == "brand_profile":
            stmt = select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID)
            res = await self.session.execute(stmt)
            brand = res.scalar_one_or_none()
            if not brand:
                brand = BrandProfile(
                    id=SINGLETON_BRAND_ID,
                    brand_name="Studio Brand",
                    brand_promise="High signal content",
                    audience="Creators & Engineers",
                )
                self.session.add(brand)

            if field in ("avoid_vocabulary", "banned_cliches", "preferred_vocabulary", "voice_rules", "claim_rules", "tone"):
                current_list = list(getattr(brand, field, []) or [])
                items_to_add = [value] if isinstance(value, str) else list(value)
                for item in items_to_add:
                    if item not in current_list:
                        current_list.append(item)
                setattr(brand, field, current_list)
                flag_modified(brand, field)
            elif field in ("cta_style", "humor_policy", "controversy_policy", "sponsor_policy"):
                setattr(brand, field, str(value))

        elif target == "brand_memory":
            memory_type = field or "topic"
            content_str = str(value)
            mem_item = BrandMemoryItem(
                id=str(uuid.uuid4()),
                memory_type=memory_type,
                content=content_str,
                context_note=f"Learned from lesson: {lesson.title}",
                usage_count=1,
            )
            self.session.add(mem_item)

        elif target == "brand_exemplar":
            if isinstance(value, dict):
                exemplar = BrandExemplar(
                    id=str(uuid.uuid4()),
                    category=value.get("category", "approved_hook"),
                    title=value.get("title", lesson.title),
                    content=value.get("content", ""),
                    platform=value.get("platform", "all"),
                    context_note=value.get("context_note", f"From lesson: {lesson.title}"),
                )
            else:
                exemplar = BrandExemplar(
                    id=str(uuid.uuid4()),
                    category="approved_hook",
                    title=lesson.title,
                    content=str(value),
                    platform="all",
                    context_note=f"From lesson: {lesson.title}",
                )
            self.session.add(exemplar)

        lesson.status = "APPLIED"
        lesson.applied_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def get_feedback_summary(self) -> Dict[str, Any]:
        """Aggregate summary of all lessons by status, impact, and type."""
        stmt = select(FeedbackLesson)
        res = await self.session.execute(stmt)
        all_lessons = list(res.scalars().all())

        pending_count = sum(1 for l in all_lessons if l.status == "PENDING")
        approved_count = sum(1 for l in all_lessons if l.status == "APPROVED")
        applied_count = sum(1 for l in all_lessons if l.status == "APPLIED")
        rejected_count = sum(1 for l in all_lessons if l.status == "REJECTED")

        by_type: Dict[str, int] = {}
        by_impact: Dict[str, int] = {}

        for l in all_lessons:
            by_type[l.lesson_type] = by_type.get(l.lesson_type, 0) + 1
            by_impact[l.impact_level] = by_impact.get(l.impact_level, 0) + 1

        return {
            "total_lessons": len(all_lessons),
            "pending_count": pending_count,
            "approved_count": approved_count,
            "applied_count": applied_count,
            "rejected_count": rejected_count,
            "by_type": by_type,
            "by_impact": by_impact,
        }
