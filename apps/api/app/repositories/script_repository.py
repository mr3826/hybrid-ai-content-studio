import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.script import ScriptDraft, ScriptSection, ScriptRevision
from app.models.content_family import ContentItem


VALID_SCRIPT_STATUSES = [
    "DRAFT",
    "SCRIPT_REVIEW",
    "SCRIPT_APPROVED",
    "REJECTED",
    "ARCHIVED",
]

SECTION_TYPES = [
    "hook",
    "problem_context",
    "method_test",
    "evidence",
    "result",
    "interpretation",
    "cta",
]


class ScriptRepository:
    """Repository handling persistence, revisions, sections, and approval for Script Studio."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_script(
        self,
        content_item_id: str,
        format: str,
        title: str,
        target_platform: str = "youtube",
        target_duration_sec: int = 60,
        version: int = 1,
    ) -> ScriptDraft:
        script = ScriptDraft(
            id=str(uuid.uuid4()),
            content_item_id=content_item_id,
            version=version,
            format=format,
            title=title,
            target_platform=target_platform,
            target_duration_sec=target_duration_sec,
            total_word_count=0,
            estimated_duration_sec=0,
            status="DRAFT",
            is_approved=False,
        )
        self.session.add(script)
        await self.session.commit()
        await self.session.refresh(script)
        return script

    async def get_script(self, script_id: str) -> Optional[ScriptDraft]:
        stmt = (
            select(ScriptDraft)
            .where(ScriptDraft.id == script_id)
            .options(
                selectinload(ScriptDraft.sections),
                selectinload(ScriptDraft.revisions),
                selectinload(ScriptDraft.content_item),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_content_item(self, content_item_id: str) -> Optional[ScriptDraft]:
        stmt = (
            select(ScriptDraft)
            .where(ScriptDraft.content_item_id == content_item_id)
            .options(
                selectinload(ScriptDraft.sections),
                selectinload(ScriptDraft.revisions),
                selectinload(ScriptDraft.content_item),
            )
            .order_by(ScriptDraft.version.desc(), ScriptDraft.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def add_section(
        self,
        script_id: str,
        section_type: str,
        order_index: int,
        heading: str,
        narration: str,
        visual_cue: str = "",
        estimated_seconds: int = 0,
        word_count: int = 0,
        linked_claim_ids: Optional[List[str]] = None,
    ) -> ScriptSection:
        if word_count == 0 and narration:
            word_count = len(narration.split())
        if estimated_seconds == 0 and word_count > 0:
            # Standard spoken cadence: ~2.5 words per second (150 wpm)
            estimated_seconds = max(1, round(word_count / 2.5))

        section = ScriptSection(
            id=str(uuid.uuid4()),
            script_id=script_id,
            section_type=section_type,
            order_index=order_index,
            heading=heading,
            narration=narration,
            visual_cue=visual_cue,
            estimated_seconds=estimated_seconds,
            word_count=word_count,
            linked_claim_ids=linked_claim_ids or [],
        )
        self.session.add(section)
        await self.session.commit()
        await self.session.refresh(section)

        await self._recalculate_metrics(script_id)
        return section

    async def update_section(self, section_id: str, **kwargs) -> Optional[ScriptSection]:
        stmt = select(ScriptSection).where(ScriptSection.id == section_id)
        res = await self.session.execute(stmt)
        section = res.scalars().first()
        if not section:
            return None

        for k, v in kwargs.items():
            if hasattr(section, k) and v is not None:
                setattr(section, k, v)

        if "narration" in kwargs and kwargs["narration"] is not None:
            section.word_count = len(section.narration.split())
            if "estimated_seconds" not in kwargs or kwargs["estimated_seconds"] is None:
                section.estimated_seconds = max(1, round(section.word_count / 2.5))

        section.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(section)

        await self._recalculate_metrics(section.script_id)
        return section

    async def delete_section(self, section_id: str) -> bool:
        stmt = select(ScriptSection).where(ScriptSection.id == section_id)
        res = await self.session.execute(stmt)
        section = res.scalars().first()
        if not section:
            return False

        script_id = section.script_id
        await self.session.delete(section)
        await self.session.commit()
        await self._recalculate_metrics(script_id)
        return True

    async def _recalculate_metrics(self, script_id: str) -> None:
        stmt = select(ScriptSection).where(ScriptSection.script_id == script_id)
        res = await self.session.execute(stmt)
        sections = list(res.scalars().all())

        total_words = sum(s.word_count for s in sections)
        total_seconds = sum(s.estimated_seconds for s in sections)

        stmt_script = select(ScriptDraft).where(ScriptDraft.id == script_id)
        res_script = await self.session.execute(stmt_script)
        script = res_script.scalars().first()
        if script:
            script.total_word_count = total_words
            script.estimated_duration_sec = total_seconds
            script.updated_at = datetime.now(timezone.utc)
            await self.session.commit()

    async def create_revision(
        self,
        script_id: str,
        trigger: str,
        notes: str = "",
        section_id: Optional[str] = None,
    ) -> ScriptRevision:
        script = await self.get_script(script_id)
        if not script:
            raise ValueError(f"Script {script_id} not found.")

        # Determine revision number
        count_stmt = select(ScriptRevision).where(ScriptRevision.script_id == script_id)
        count_res = await self.session.execute(count_stmt)
        rev_count = len(list(count_res.scalars().all()))

        snapshot = {
            "id": script.id,
            "version": script.version,
            "title": script.title,
            "format": script.format,
            "target_platform": script.target_platform,
            "total_word_count": script.total_word_count,
            "estimated_duration_sec": script.estimated_duration_sec,
            "quality_scores": script.quality_scores,
            "sections": [
                {
                    "id": s.id,
                    "section_type": s.section_type,
                    "order_index": s.order_index,
                    "heading": s.heading,
                    "narration": s.narration,
                    "visual_cue": s.visual_cue,
                    "estimated_seconds": s.estimated_seconds,
                    "word_count": s.word_count,
                    "linked_claim_ids": s.linked_claim_ids,
                }
                for s in sorted(script.sections, key=lambda x: x.order_index)
            ],
        }

        revision = ScriptRevision(
            id=str(uuid.uuid4()),
            script_id=script_id,
            section_id=section_id,
            revision_number=rev_count + 1,
            trigger=trigger,
            notes=notes,
            snapshot=snapshot,
        )
        self.session.add(revision)
        await self.session.commit()
        await self.session.refresh(revision)
        return revision

    async def restore_revision(self, script_id: str, revision_id: str) -> Optional[ScriptDraft]:
        stmt = select(ScriptRevision).where(
            ScriptRevision.id == revision_id,
            ScriptRevision.script_id == script_id,
        )
        res = await self.session.execute(stmt)
        revision = res.scalars().first()
        if not revision:
            return None

        # Create a checkpoint revision before restoring
        await self.create_revision(
            script_id=script_id,
            trigger="pre_restore_checkpoint",
            notes=f"Automatic checkpoint prior to restoring revision #{revision.revision_number}",
        )

        snapshot = revision.snapshot
        script = await self.get_script(script_id)
        if not script:
            return None

        # Update script metadata
        script.title = snapshot.get("title", script.title)
        script.total_word_count = snapshot.get("total_word_count", 0)
        script.estimated_duration_sec = snapshot.get("estimated_duration_sec", 0)
        script.updated_at = datetime.now(timezone.utc)

        # Clear existing sections and replace with snapshot
        del_stmt = delete(ScriptSection).where(ScriptSection.script_id == script_id)
        await self.session.execute(del_stmt)

        for sec_data in snapshot.get("sections", []):
            new_sec = ScriptSection(
                id=sec_data.get("id") or str(uuid.uuid4()),
                script_id=script_id,
                section_type=sec_data.get("section_type", "hook"),
                order_index=sec_data.get("order_index", 0),
                heading=sec_data.get("heading", ""),
                narration=sec_data.get("narration", ""),
                visual_cue=sec_data.get("visual_cue", ""),
                estimated_seconds=sec_data.get("estimated_seconds", 0),
                word_count=sec_data.get("word_count", 0),
                linked_claim_ids=sec_data.get("linked_claim_ids", []),
            )
            self.session.add(new_sec)

        await self.session.commit()

        # Record post-restore audit event
        await self.create_revision(
            script_id=script_id,
            trigger="restore",
            notes=f"Restored from revision #{revision.revision_number}",
        )

        return await self.get_script(script_id)

    async def update_quality_scores(self, script_id: str, scores: Dict[str, Any]) -> Optional[ScriptDraft]:
        script = await self.get_script(script_id)
        if not script:
            return None
        script.quality_scores = scores
        script.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(script)
        return script

    async def approve_script(
        self,
        script_id: str,
        reviewer: str = "creator",
        override_reason: Optional[str] = None,
    ) -> ScriptDraft:
        script = await self.get_script(script_id)
        if not script:
            raise ValueError(f"Script {script_id} not found.")

        script.status = "SCRIPT_APPROVED"
        script.is_approved = True
        script.approved_at = datetime.now(timezone.utc)
        script.approved_by = reviewer
        script.override_reason = override_reason
        script.updated_at = datetime.now(timezone.utc)

        # Transition ContentItem to SCRIPT_APPROVED and record script_version_id
        item_stmt = select(ContentItem).where(ContentItem.id == script.content_item_id)
        item_res = await self.session.execute(item_stmt)
        item = item_res.scalars().first()
        if item:
            item.status = "SCRIPT_APPROVED"
            item.script_version_id = script.id
            item.updated_at = datetime.now(timezone.utc)

        # Record revision snapshot of the approved milestone
        await self.create_revision(
            script_id=script_id,
            trigger="approval",
            notes=f"Approved by {reviewer}" + (f" with override: {override_reason}" if override_reason else ""),
        )

        await self.session.commit()
        await self.session.refresh(script)
        return script
