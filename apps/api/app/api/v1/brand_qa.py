from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.engines.brand.contracts import BrandQAInput, BrandQAVerdict
from app.engines.brand.engine import BrandEngine
from app.engines.core.registry import engine_registry

router = APIRouter(prefix="/brand-qa", tags=["Brand QA"])


@router.post("/evaluate", response_model=BrandQAVerdict)
async def evaluate_brand_consistency(
    payload: BrandQAInput,
    session: AsyncSession = Depends(get_db),
):
    """Evaluate draft or script against the single active BrandProfile guidelines."""
    from app.engines.catalog import register_all_catalog_engines
    register_all_catalog_engines()
    engine = engine_registry.get("brand")
    if not isinstance(engine, BrandEngine):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Brand Engine is not registered or unavailable.",
        )

    brand_data, exemplars = await engine._get_brand_data()
    verdict = engine.evaluate_item(payload, brand_data, exemplars)
    return verdict
