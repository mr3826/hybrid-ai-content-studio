import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evidence import Conclusion, Experiment, ExperimentRun, Measurement
from app.models.originality import ExperimentAttachment, OriginalityPlan
from app.repositories.base import BaseRepository

SUPPORTED_ORIGINALITY_TYPES = [
    "tool_test",
    "benchmark",
    "cost_comparison",
    "workflow_demonstration",
    "before_after",
    "implementation_attempt",
    "multi_source_synthesis",
    "original_framework",
    "original_chart_data_analysis",
    "practical_tutorial",
    "failure_analysis",
    "clearly_labeled_opinion",
]

GENERIC_SUMMARY_INDICATORS = [
    "summary of the article",
    "news summary",
    "general overview",
    "recap of news",
    "just summarizing",
    "generic summary",
]


class OriginalityRepository(BaseRepository[OriginalityPlan]):
    """Repository managing Originality Plans, human contribution gates, and Experiment Workspace."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^\w\s-]", "", text).strip().lower()
        return re.sub(r"[-\s]+", "-", s)[:200]

    async def create_plan(
        self,
        topic: str,
        originality_type: str,
        what_are_we_adding: str,
        why_it_matters: str = "",
        opportunity_id: Optional[str] = None,
        packet_id: Optional[str] = None,
        suggested_experiments: Optional[List[Dict[str, Any]]] = None,
        confidence_score: float = 85.0,
    ) -> OriginalityPlan:
        """Create an originality plan enforcing 'What are WE adding?' quality gates."""
        slug = f"{self._slugify(topic)}-{uuid.uuid4().hex[:6]}"

        # Evaluate generic summary quality gate
        is_generic = False
        lower_adding = what_are_we_adding.lower().strip()
        lower_type = originality_type.lower().strip()

        if lower_type not in SUPPORTED_ORIGINALITY_TYPES:
            is_generic = True
        elif len(lower_adding) < 15:
            is_generic = True
        elif any(ind in lower_adding for ind in GENERIC_SUMMARY_INDICATORS):
            is_generic = True

        status = "not_ready" if is_generic else "needs_review"

        plan = OriginalityPlan(
            id=str(uuid.uuid4()),
            opportunity_id=opportunity_id,
            packet_id=packet_id,
            topic=topic,
            slug=slug,
            originality_type=originality_type,
            what_are_we_adding=what_are_we_adding,
            why_it_matters=why_it_matters,
            status=status,
            is_generic_summary=is_generic,
            confidence_score=confidence_score,
            suggested_experiments=suggested_experiments or [],
        )

        self.session.add(plan)
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def get_plan(self, plan_id: str) -> Optional[OriginalityPlan]:
        query = (
            select(OriginalityPlan)
            .where(OriginalityPlan.id == plan_id)
            .options(
                selectinload(OriginalityPlan.experiments).selectinload(Experiment.attachments),
                selectinload(OriginalityPlan.experiments).selectinload(Experiment.conclusions),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_opportunity(self, opportunity_id: str) -> Optional[OriginalityPlan]:
        query = (
            select(OriginalityPlan)
            .where(OriginalityPlan.opportunity_id == opportunity_id)
            .options(
                selectinload(OriginalityPlan.experiments).selectinload(Experiment.attachments),
            )
            .order_by(desc(OriginalityPlan.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_plans(
        self,
        status: Optional[str] = None,
        originality_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[OriginalityPlan]:
        query = select(OriginalityPlan).order_by(desc(OriginalityPlan.created_at))
        if status:
            query = query.where(OriginalityPlan.status == status)
        if originality_type:
            query = query.where(OriginalityPlan.originality_type == originality_type)
        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def approve_plan(
        self, plan_id: str, reviewer: str = "creator", notes: Optional[str] = None
    ) -> OriginalityPlan:
        """Approve an originality plan; blocks generic summaries."""
        plan = await self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"OriginalityPlan {plan_id} not found.")

        if plan.is_generic_summary:
            raise ValueError(
                "Cannot approve generic summary. Topic must answer 'What are WE adding?' with an approved originality type."
            )

        plan.status = "approved"
        plan.reviewed_by = reviewer
        plan.review_notes = notes
        plan.reviewed_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def reject_plan(self, plan_id: str, reason: str) -> OriginalityPlan:
        plan = await self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"OriginalityPlan {plan_id} not found.")

        plan.status = "rejected"
        plan.review_notes = reason
        plan.reviewed_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    # -----------------------------------------------------------------------
    # Experiment Workspace Operations
    # -----------------------------------------------------------------------

    async def create_experiment(
        self,
        title: str,
        hypothesis: str,
        method: str,
        question: Optional[str] = None,
        dataset_sample: Optional[str] = None,
        tools_models: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        results: Optional[Dict[str, Any]] = None,
        failures: Optional[List[str]] = None,
        latency_ms: Optional[float] = 0.0,
        cost_usd: Optional[float] = 0.0,
        screenshots_files: Optional[List[Dict[str, Any]]] = None,
        notes: Optional[str] = None,
        conclusion: Optional[str] = None,
        status: str = "completed",
        opportunity_id: Optional[str] = None,
        originality_plan_id: Optional[str] = None,
    ) -> Experiment:
        """Store a full experimental test harness run in the workspace."""
        exp = Experiment(
            id=str(uuid.uuid4()),
            opportunity_id=opportunity_id,
            originality_plan_id=originality_plan_id,
            title=title,
            question=question or title,
            hypothesis=hypothesis,
            method=method,
            dataset_sample=dataset_sample or "",
            tools_models=tools_models or [],
            parameters=parameters or {},
            results=results or {},
            failures=failures or [],
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            screenshots_files=screenshots_files or [],
            notes=notes or "",
            conclusion=conclusion or "",
            status=status,
        )

        self.session.add(exp)
        await self.session.commit()
        await self.session.refresh(exp)
        return exp

    async def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        query = (
            select(Experiment)
            .where(Experiment.id == experiment_id)
            .options(
                selectinload(Experiment.attachments),
                selectinload(Experiment.runs).selectinload(ExperimentRun.measurements),
                selectinload(Experiment.conclusions),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_experiments(
        self,
        opportunity_id: Optional[str] = None,
        originality_plan_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Experiment]:
        query = (
            select(Experiment)
            .options(
                selectinload(Experiment.attachments),
                selectinload(Experiment.conclusions),
            )
            .order_by(desc(Experiment.created_at))
        )
        if opportunity_id:
            query = query.where(Experiment.opportunity_id == opportunity_id)
        if originality_plan_id:
            query = query.where(Experiment.originality_plan_id == originality_plan_id)
        if status:
            query = query.where(Experiment.status == status)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_attachment(
        self,
        experiment_id: str,
        attachment_type: str,
        filename: str,
        file_path: str,
        mime_type: str = "application/octet-stream",
        size_bytes: int = 0,
        content_snippet: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> ExperimentAttachment:
        """Attach evidence or benchmark files (JSON, CSV, screenshots, code snippets) to an experiment."""
        att = ExperimentAttachment(
            id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            attachment_type=attachment_type,
            filename=filename,
            file_path=file_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            content_snippet=content_snippet,
            caption=caption,
        )
        self.session.add(att)
        await self.session.commit()
        await self.session.refresh(att)
        return att

    async def link_to_evidence(
        self,
        experiment_id: str,
        claim_id: Optional[str],
        conclusion_text: str,
        confidence: float = 0.95,
    ) -> Conclusion:
        """Link experiment result to Evidence Engine claims."""
        conclusion = Conclusion(
            id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            claim_id=claim_id,
            summary=conclusion_text,
            confidence=confidence,
        )
        self.session.add(conclusion)
        await self.session.commit()
        await self.session.refresh(conclusion)
        return conclusion
