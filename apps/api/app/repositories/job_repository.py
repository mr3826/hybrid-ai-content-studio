import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import StudioJob
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[StudioJob]):
    """Repository handling database-backed asynchronous studio jobs."""

    async def create_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        engine_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> StudioJob:
        job = StudioJob(
            id=str(uuid.uuid4()),
            job_type=job_type,
            engine_id=engine_id,
            project_id=project_id,
            payload=payload,
            status="pending",
            attempts=0,
            result={},
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> Optional[StudioJob]:
        stmt = select(StudioJob).where(StudioJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StudioJob]:
        stmt = select(StudioJob).order_by(StudioJob.created_at.desc())
        if status:
            stmt = stmt.where(StudioJob.status == status)
        if job_type:
            stmt = stmt.where(StudioJob.job_type == job_type)
        if project_id:
            stmt = stmt.where(StudioJob.project_id == project_id)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def claim_next_job(
        self,
        supported_types: Optional[List[str]] = None,
    ) -> Optional[StudioJob]:
        """Claim the next pending job atomically for worker execution."""
        stmt = (
            select(StudioJob)
            .where(StudioJob.status == "pending")
            .order_by(StudioJob.created_at.asc())
        )
        if supported_types:
            stmt = stmt.where(StudioJob.job_type.in_(supported_types))

        result = await self.session.execute(stmt)
        job = result.scalars().first()
        if not job:
            return None

        job.status = "running"
        job.attempts += 1
        job.started_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def complete_job(
        self,
        job_id: str,
        result_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[StudioJob]:
        job = await self.get_job(job_id)
        if not job:
            return None
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        job.result = result_data or {}
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def fail_job(
        self,
        job_id: str,
        error_message: str,
        result_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[StudioJob]:
        job = await self.get_job(job_id)
        if not job:
            return None
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc)
        job.error = error_message
        if result_data is not None:
            job.result = result_data
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def cancel_job(self, job_id: str) -> Optional[StudioJob]:
        job = await self.get_job(job_id)
        if not job:
            return None
        job.status = "cancelled"
        job.finished_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(job)
        return job
