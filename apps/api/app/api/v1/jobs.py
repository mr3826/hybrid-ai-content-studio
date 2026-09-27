from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreate, JobRead, JobListResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    data: JobCreate,
    session: AsyncSession = Depends(get_db),
):
    """Enqueue a new asynchronous background job."""
    repo = JobRepository(session)
    job = await repo.create_job(
        job_type=data.job_type,
        payload=data.payload,
        engine_id=data.engine_id,
        project_id=data.project_id,
    )
    return job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status: pending, running, completed, failed, cancelled"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    project_id: Optional[str] = Query(None, description="Filter by target project ID"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    """List jobs in the queue with optional filters."""
    repo = JobRepository(session)
    jobs = await repo.list_jobs(
        status=status,
        job_type=job_type,
        project_id=project_id,
        limit=limit,
    )
    return JobListResponse(jobs=jobs, total=len(jobs))


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get single job status and results."""
    repo = JobRepository(session)
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job


@router.post("/{job_id}/cancel", response_model=JobRead)
async def cancel_job(
    job_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Cancel a pending or running job."""
    repo = JobRepository(session)
    job = await repo.cancel_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job
