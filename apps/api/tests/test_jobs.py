import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.job_repository import JobRepository
from app.models.job import StudioJob
from worker.worker import StudioWorker


@pytest.mark.asyncio
async def test_job_repository_lifecycle(db_session: AsyncSession):
    repo = JobRepository(db_session)

    # 1. Create Job
    job = await repo.create_job(
        job_type="test_echo",
        payload={"message": "hello studio"},
        project_id="proj-123",
    )
    assert job.id is not None
    assert job.job_type == "test_echo"
    assert job.status == "pending"
    assert job.attempts == 0
    assert job.project_id == "proj-123"

    # 2. Claim Job
    claimed = await repo.claim_next_job(supported_types=["test_echo"])
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "running"
    assert claimed.attempts == 1
    assert claimed.started_at is not None

    # 3. Complete Job
    completed = await repo.complete_job(claimed.id, result_data={"echo": "done"})
    assert completed is not None
    assert completed.status == "completed"
    assert completed.finished_at is not None
    assert completed.result == {"echo": "done"}

    # 4. List Jobs
    jobs = await repo.list_jobs(status="completed", job_type="test_echo")
    assert len(jobs) >= 1
    assert any(j.id == job.id for j in jobs)


@pytest.mark.asyncio
async def test_job_repository_fail_and_cancel(db_session: AsyncSession):
    repo = JobRepository(db_session)

    # Test failure
    job1 = await repo.create_job(job_type="failing_task", payload={})
    failed = await repo.fail_job(job1.id, error_message="Simulated crash")
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error == "Simulated crash"

    # Test cancellation
    job2 = await repo.create_job(job_type="cancel_task", payload={})
    cancelled = await repo.cancel_job(job2.id)
    assert cancelled is not None
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_jobs_api_endpoints(client: AsyncClient):
    # 1. POST /api/v1/jobs
    create_res = await client.post(
        "/api/v1/jobs",
        json={
            "job_type": "engine_run",
            "engine_id": "reference",
            "project_id": "proj-abc",
            "payload": {"dry_run": True},
        },
    )
    assert create_res.status_code == 201
    job_data = create_res.json()
    job_id = job_data["id"]
    assert job_data["job_type"] == "engine_run"
    assert job_data["engine_id"] == "reference"
    assert job_data["status"] == "pending"

    # 2. GET /api/v1/jobs/{job_id}
    get_res = await client.get(f"/api/v1/jobs/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == job_id

    # 3. GET /api/v1/jobs
    list_res = await client.get("/api/v1/jobs?status=pending")
    assert list_res.status_code == 200
    assert any(j["id"] == job_id for j in list_res.json()["jobs"])

    # 4. POST /api/v1/jobs/{job_id}/cancel
    cancel_res = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_worker_polls_and_executes_job(client: AsyncClient, db_session: AsyncSession):
    # Enqueue an engine_run job for reference engine
    repo = JobRepository(db_session)
    job = await repo.create_job(
        job_type="engine_run",
        engine_id="reference",
        project_id="test-proj-worker",
        payload={"dry_run": True, "parameters": {}},
    )
    assert job.status == "pending"

    # Run one worker poll iteration
    worker = StudioWorker()
    from app.engines.catalog import register_all_catalog_engines
    register_all_catalog_engines()
    await worker.poll_and_execute()

    # Verify job completed
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as verify_session:
        verify_repo = JobRepository(verify_session)
        refreshed = await verify_repo.get_job(job.id)
        assert refreshed is not None
        assert refreshed.status == "completed"
        assert refreshed.finished_at is not None
        assert refreshed.result.get("success") is True
