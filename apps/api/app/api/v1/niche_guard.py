from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.engines.core.registry import engine_registry
from app.engines.niche_guard.contracts import NicheGuardInput, NicheGuardVerdict
from app.engines.niche_guard.engine import NicheGuardEngine

router = APIRouter(prefix="/niche-guard", tags=["Niche Guard"])


@router.post("/evaluate", response_model=NicheGuardVerdict)
async def evaluate_niche_alignment(
    payload: NicheGuardInput,
    session: AsyncSession = Depends(get_db),
):
    """Evaluate candidate text against the single active niche profile with deterministic scoring."""
    from app.engines.catalog import register_all_catalog_engines
    register_all_catalog_engines()
    engine = engine_registry.get("niche_guard")
    if not isinstance(engine, NicheGuardEngine):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Niche Guard Engine is not registered or unavailable.",
        )

    niche_data = await engine._get_active_niche_data()
    verdict = engine.evaluate_item(payload, niche_data)
    return verdict
