import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import (
    BaseRepository,
    JobRepository,
    OpportunityRepository,
    ResearchRepository,
    EvidenceRepository,
    ProjectRepository,
    ContentRepository,
    AnalyticsRepository,
    AssetRepository,
    FeedbackRepository,
    AudienceRepository,
)
from app.engines.core.registry import engine_registry
from app.engines.core.base import EngineContext
from app.models.engine_run import EngineRunRecord
from sqlalchemy import select


@pytest.mark.asyncio
async def test_repository_boundaries_initialization(db_session: AsyncSession):
    """Verify all 8 storage repository boundaries can be instantiated and operated with SQLite."""
    job_repo = JobRepository(db_session)
    opp_repo = OpportunityRepository(db_session)
    res_repo = ResearchRepository(db_session)
    evi_repo = EvidenceRepository(db_session)
    proj_repo = ProjectRepository(db_session)
    cnt_repo = ContentRepository(db_session)
    ana_repo = AnalyticsRepository(db_session)
    ast_repo = AssetRepository(db_session)
    fbk_repo = FeedbackRepository(db_session)
    aud_repo = AudienceRepository(db_session)

    assert isinstance(job_repo, BaseRepository)
    assert isinstance(opp_repo, BaseRepository)
    assert isinstance(res_repo, BaseRepository)
    assert isinstance(evi_repo, BaseRepository)
    assert isinstance(proj_repo, BaseRepository)
    assert isinstance(cnt_repo, BaseRepository)
    assert isinstance(ana_repo, BaseRepository)
    assert isinstance(ast_repo, BaseRepository)
    assert isinstance(fbk_repo, BaseRepository)
    assert isinstance(aud_repo, BaseRepository)

    # Test basic boundary methods
    opps = await opp_repo.list_opportunities()
    assert isinstance(opps, list)

    rec = await evi_repo.record_citation({"url": "https://example.com", "fact": "verified"})
    assert rec["url"] == "https://example.com"

    proj = await proj_repo.create_project({"title": "Test Pipeline", "stage": "idea"})
    assert proj["stage"] == "idea"

    ana = await ana_repo.get_performance_summary(days=7)
    assert ana["days"] == 7

    assets = await ast_repo.list_assets_by_project("proj-1")
    assert isinstance(assets, list)


@pytest.mark.asyncio
async def test_engine_run_observability_fields(db_session: AsyncSession):
    """Verify rules_version and project_id are persisted to engine_runs table on execution."""
    import uuid
    from app.engines.catalog import register_all_catalog_engines
    register_all_catalog_engines()

    unique_run_id = f"obs-{uuid.uuid4()}"
    ctx = EngineContext(
        run_id=unique_run_id,
        project_id="project-alpha-99",
        dry_run=True,
    )

    result = await engine_registry.execute_engine(
        "reference",
        context=ctx,
        dry_run=True,
        session=db_session,
    )

    assert result.rules_version is not None
    assert result.project_id == "project-alpha-99"

    # Query from database to verify persistence
    stmt = select(EngineRunRecord).where(EngineRunRecord.run_id == unique_run_id)
    db_res = await db_session.execute(stmt)
    record = db_res.scalar_one_or_none()
    assert record is not None
    assert record.project_id == "project-alpha-99"
    assert record.rules_version == result.rules_version
