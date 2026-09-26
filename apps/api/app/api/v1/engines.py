import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.catalog import register_all_catalog_engines
from app.engines.core.base import EngineContext, EngineExplanation, EngineHealth, EngineResult
from app.engines.core.registry import engine_registry
from app.models.engine_run import EngineRunRecord
from app.schemas.engine import (
    EngineDetailRead,
    EngineRulesUpdate,
    EngineRunRecordRead,
    EngineRunRequest,
    EngineSummaryRead,
)

router = APIRouter(prefix="/engines", tags=["Feature Engines"])


@router.get("", response_model=List[EngineSummaryRead])
async def list_engines(session: AsyncSession = Depends(get_db)):
    """List all 13 Studio Engines + Reference Engine with current health and last run stats."""
    # Ensure all catalog engines are registered
    register_all_catalog_engines()

    engines = engine_registry.list_all()
    summaries = []

    for eng in engines:
        # Query last run and total run count from DB
        stmt_last = (
            select(EngineRunRecord)
            .where(EngineRunRecord.engine_id == eng.id)
            .order_by(desc(EngineRunRecord.started_at))
            .limit(1)
        )
        last_res = await session.execute(stmt_last)
        last_run = last_res.scalar_one_or_none()

        stmt_count = select(func.count(EngineRunRecord.id)).where(
            EngineRunRecord.engine_id == eng.id
        )
        count_res = await session.execute(stmt_count)
        total_count = count_res.scalar() or 0

        summaries.append(
            EngineSummaryRead(
                id=eng.id,
                name=eng.name,
                version=eng.version,
                description=eng.manifest.description,
                enabled=eng.manifest.enabled,
                inputs=eng.manifest.inputs,
                outputs=eng.manifest.outputs,
                dependencies=eng.manifest.dependencies,
                triggers=eng.manifest.triggers,
                supports=eng.manifest.supports,
                health=eng.health(),
                last_run_at=last_run.started_at if last_run else None,
                last_run_status=last_run.status if last_run else None,
                total_runs_count=total_count,
            )
        )

    return summaries


@router.get("/{engine_id}", response_model=EngineDetailRead)
async def get_engine_detail(engine_id: str, session: AsyncSession = Depends(get_db)):
    """Fetch detailed metadata, rules, and execution statistics for an engine."""
    register_all_catalog_engines()
    eng = engine_registry.get(engine_id)
    if not eng:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine '{engine_id}' not found in registry.",
        )

    stmt_last = (
        select(EngineRunRecord)
        .where(EngineRunRecord.engine_id == eng.id)
        .order_by(desc(EngineRunRecord.started_at))
        .limit(1)
    )
    last_res = await session.execute(stmt_last)
    last_run = last_res.scalar_one_or_none()

    stmt_count = select(func.count(EngineRunRecord.id)).where(
        EngineRunRecord.engine_id == eng.id
    )
    count_res = await session.execute(stmt_count)
    total_count = count_res.scalar() or 0

    return EngineDetailRead(
        manifest=eng.manifest,
        health=eng.health(),
        rules=eng.get_rules(),
        total_runs_count=total_count,
        last_run={
            "run_id": last_run.run_id,
            "status": last_run.status,
            "started_at": last_run.started_at.isoformat(),
            "summary": last_run.summary,
            "duration_ms": last_run.duration_ms,
        }
        if last_run
        else None,
    )


@router.post("/{engine_id}/run", response_model=EngineResult)
async def run_engine(
    engine_id: str,
    payload: EngineRunRequest = EngineRunRequest(),
    session: AsyncSession = Depends(get_db),
):
    """Execute an engine in production mode and record an audit log in SQLite."""
    register_all_catalog_engines()
    context = EngineContext(
        run_id=str(uuid.uuid4())[:8],
        dry_run=False,
        trigger=payload.trigger,
        parameters=payload.parameters,
    )
    try:
        return await engine_registry.execute_engine(
            engine_id, context=context, dry_run=False, session=session
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{engine_id}/dry-run", response_model=EngineResult)
async def dry_run_engine(
    engine_id: str,
    payload: EngineRunRequest = EngineRunRequest(),
    session: AsyncSession = Depends(get_db),
):
    """Execute an engine in dry-run mode without persistent side effects."""
    register_all_catalog_engines()
    context = EngineContext(
        run_id=str(uuid.uuid4())[:8],
        dry_run=True,
        trigger=payload.trigger,
        parameters=payload.parameters,
    )
    try:
        return await engine_registry.execute_engine(
            engine_id, context=context, dry_run=True, session=session
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{engine_id}/health", response_model=EngineHealth)
async def get_engine_health(engine_id: str):
    """Check active health and configuration validity of an engine."""
    register_all_catalog_engines()
    eng = engine_registry.get(engine_id)
    if not eng:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine '{engine_id}' not found.",
        )
    return eng.health()


@router.get("/{engine_id}/rules", response_model=Dict[str, Any])
async def get_engine_rules(engine_id: str):
    """View current typed rules or configuration for an engine."""
    register_all_catalog_engines()
    eng = engine_registry.get(engine_id)
    if not eng:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine '{engine_id}' not found.",
        )
    return eng.get_rules()


@router.put("/{engine_id}/rules", response_model=Dict[str, Any])
async def update_engine_rules(engine_id: str, payload: EngineRulesUpdate):
    """Update engine rules."""
    register_all_catalog_engines()
    eng = engine_registry.get(engine_id)
    if not eng:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine '{engine_id}' not found.",
        )
    try:
        eng.update_rules(payload.rules)
        return eng.get_rules()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{engine_id}/runs", response_model=List[EngineRunRecordRead])
async def get_engine_runs(
    engine_id: str,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve execution history logs for an engine."""
    stmt = (
        select(EngineRunRecord)
        .where(EngineRunRecord.engine_id == engine_id)
        .order_by(desc(EngineRunRecord.started_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{engine_id}/explain/{result_id}", response_model=EngineExplanation)
async def explain_engine_result(engine_id: str, result_id: str):
    """Get human-readable breakdown and factor weights for an engine decision."""
    register_all_catalog_engines()
    eng = engine_registry.get(engine_id)
    if not eng:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine '{engine_id}' not found.",
        )
    return eng.explain(result_id)
