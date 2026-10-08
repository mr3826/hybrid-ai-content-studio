from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_family import ContentItem
from app.models.quality_gate import QualityGateAudit
from app.models.script import ScriptDraft


class QualityGateRepository:
    """Repository handling CRUD operations for QualityGateAudit records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_audit_by_item(self, content_item_id: str) -> Optional[QualityGateAudit]:
        stmt = (
            select(QualityGateAudit)
            .where(QualityGateAudit.content_item_id == content_item_id)
            .order_by(QualityGateAudit.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def create_or_update_audit(
        self,
        content_item_id: str,
        script_id: Optional[str],
        eval_result: Dict[str, Any],
    ) -> QualityGateAudit:
        existing = await self.get_audit_by_item(content_item_id)

        dims = {d.id: d.model_dump() for d in eval_result.get("dimensions", [])}
        recs = [r.model_dump() for r in eval_result.get("recommendations", [])]
        overall_score = eval_result.get("overall_score", 0.0)
        status = eval_result.get("status", "PENDING")

        if existing:
            existing.script_id = script_id or existing.script_id
            existing.status = status if not existing.is_approved else "FINAL_APPROVED"
            existing.overall_score = overall_score
            existing.evidence_quality = dims.get("evidence_quality", {})
            existing.brand_fit = dims.get("brand_fit", {})
            existing.originality = dims.get("originality", {})
            existing.viewer_value = dims.get("viewer_value", {})
            existing.niche_fit = dims.get("niche_fit", {})
            existing.repetition_intelligence = dims.get("repetition_intelligence", {})
            existing.asset_rights = dims.get("asset_rights", {})
            existing.media_qc = dims.get("media_qc", {})
            existing.estimated_cost = dims.get("estimated_cost", {})
            existing.actionable_recommendations = recs
            existing.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        audit = QualityGateAudit(
            content_item_id=content_item_id,
            script_id=script_id,
            status=status,
            overall_score=overall_score,
            evidence_quality=dims.get("evidence_quality", {}),
            brand_fit=dims.get("brand_fit", {}),
            originality=dims.get("originality", {}),
            viewer_value=dims.get("viewer_value", {}),
            niche_fit=dims.get("niche_fit", {}),
            repetition_intelligence=dims.get("repetition_intelligence", {}),
            asset_rights=dims.get("asset_rights", {}),
            media_qc=dims.get("media_qc", {}),
            estimated_cost=dims.get("estimated_cost", {}),
            actionable_recommendations=recs,
            is_approved=False,
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(audit)
        return audit

    async def approve_audit(
        self,
        content_item_id: str,
        approved_by: str = "Creator",
        override_reason: Optional[str] = None,
    ) -> QualityGateAudit:
        audit = await self.get_audit_by_item(content_item_id)
        if not audit:
            raise ValueError(f"No audit found for content item {content_item_id}. Run evaluation first.")

        now = datetime.now(timezone.utc)
        audit.is_approved = True
        audit.approved_by = approved_by
        audit.approved_at = now
        audit.override_reason = override_reason
        audit.status = "FINAL_APPROVED"
        audit.updated_at = now

        # Update ContentItem status
        item_stmt = select(ContentItem).where(ContentItem.id == content_item_id)
        item_res = await self.session.execute(item_stmt)
        item = item_res.scalar_one_or_none()
        if item:
            item.status = "FINAL_APPROVED"
            item.updated_at = now

        # Update ScriptDraft status
        if audit.script_id:
            script_stmt = select(ScriptDraft).where(ScriptDraft.id == audit.script_id)
            script_res = await self.session.execute(script_stmt)
            script = script_res.scalar_one_or_none()
            if script:
                script.status = "FINAL_APPROVED"
                script.is_approved = True
                script.approved_at = now
                script.approved_by = approved_by
                script.updated_at = now

        await self.session.commit()
        await self.session.refresh(audit)
        return audit

    async def list_audits(self, limit: int = 50) -> List[QualityGateAudit]:
        stmt = select(QualityGateAudit).order_by(QualityGateAudit.updated_at.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
