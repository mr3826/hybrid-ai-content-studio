from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.asset_rights.contracts import (
    AssetInput,
    AssetRightsVerdict,
    AssetRightsBatchVerdict,
)
from app.engines.asset_rights.engine import AssetRightsEngine
from app.models.asset_rights import (
    AssetRightsRecord,
    AssetRightsStatus,
    CommercialUseStatus,
)
from app.repositories.asset_rights_repository import AssetRightsRepository

router = APIRouter(prefix="/asset-rights", tags=["Asset Rights Engine"])

engine = AssetRightsEngine()


# --- Pydantic Schemas ---

class AssetRightsCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=256)
    asset_type: str = Field("image", max_length=64)
    source: str = Field(..., max_length=256)
    creator_provider: Optional[str] = Field(None, max_length=256)
    license_type: str = Field("Unknown", max_length=128)
    commercial_use_status: Optional[str] = Field(None, max_length=32)
    attribution_required: Optional[bool] = Field(None)
    attribution_text: Optional[str] = None
    license_proof: Optional[str] = None
    expiry_date: Optional[str] = None
    is_ai_generated: bool = False
    ai_tool: Optional[str] = None
    content_item_id: Optional[str] = None
    uri: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class AssetRightsUpdateRequest(BaseModel):
    title: Optional[str] = None
    asset_type: Optional[str] = None
    source: Optional[str] = None
    creator_provider: Optional[str] = None
    license_type: Optional[str] = None
    commercial_use_status: Optional[str] = None
    attribution_required: Optional[bool] = None
    attribution_text: Optional[str] = None
    license_proof: Optional[str] = None
    expiry_date: Optional[str] = None
    is_ai_generated: Optional[bool] = None
    ai_tool: Optional[str] = None
    content_item_id: Optional[str] = None
    uri: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class AssetRightsResponse(BaseModel):
    id: str
    content_item_id: Optional[str] = None
    title: str
    asset_type: str
    uri: Optional[str] = None
    source: str
    creator_provider: Optional[str] = None
    license_type: str
    commercial_use_status: str
    attribution_required: bool
    attribution_text: Optional[str] = None
    license_proof: Optional[str] = None
    expiry_date: Optional[str] = None
    is_ai_generated: bool
    ai_tool: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: Any
    updated_at: Any


# --- Endpoints ---

@router.get("", response_model=List[AssetRightsResponse])
async def list_asset_rights(
    content_item_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve catalog of tracked media assets with legal provenance status."""
    repo = AssetRightsRepository(db)
    records = await repo.list_records(
        content_item_id=content_item_id,
        status=status,
        asset_type=asset_type,
        limit=limit,
    )
    return records


@router.get("/summary/stats", response_model=Dict[str, Any])
async def get_asset_rights_summary(db: AsyncSession = Depends(get_db)):
    """Summary metrics of rights health, verified assets, and copyright risk percentage."""
    repo = AssetRightsRepository(db)
    return await repo.get_summary()


@router.post("", response_model=AssetRightsResponse, status_code=status.HTTP_201_CREATED)
async def register_asset_rights(
    payload: AssetRightsCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register and automatically verify the copyright provenance of a media asset."""
    # Convert to engine contract and evaluate
    asset_input = AssetInput(
        title=payload.title,
        asset_type=payload.asset_type,
        source=payload.source,
        creator_provider=payload.creator_provider,
        license_type=payload.license_type,
        commercial_use_status=payload.commercial_use_status,
        attribution_required=payload.attribution_required,
        attribution_text=payload.attribution_text,
        license_proof=payload.license_proof,
        expiry_date=payload.expiry_date,
        is_ai_generated=payload.is_ai_generated,
        ai_tool=payload.ai_tool,
        content_item_id=payload.content_item_id,
        uri=payload.uri,
        notes=payload.notes,
    )
    verdict = engine.evaluate_asset(asset_input)

    # Allow explicit override if user provided a specific status, otherwise use verdict
    final_status = payload.status or verdict.status

    repo = AssetRightsRepository(db)
    record = AssetRightsRecord(
        title=payload.title,
        asset_type=payload.asset_type,
        source=payload.source,
        creator_provider=payload.creator_provider,
        license_type=payload.license_type,
        commercial_use_status=payload.commercial_use_status or (CommercialUseStatus.ALLOWED if verdict.commercial_use_allowed else CommercialUseStatus.UNKNOWN),
        attribution_required=verdict.attribution_required,
        attribution_text=payload.attribution_text or verdict.attribution_text,
        license_proof=payload.license_proof,
        expiry_date=payload.expiry_date,
        is_ai_generated=payload.is_ai_generated,
        ai_tool=payload.ai_tool,
        content_item_id=payload.content_item_id,
        uri=payload.uri,
        status=final_status,
        notes=payload.notes or verdict.explanation,
    )
    saved = await repo.create(record)
    return saved


@router.post("/evaluate", response_model=AssetRightsVerdict)
async def evaluate_asset_rights_live(payload: AssetInput):
    """Dry-run rights check for an asset before adding it to a scene or project."""
    return engine.evaluate_asset(payload)


@router.post("/evaluate-batch", response_model=AssetRightsBatchVerdict)
async def evaluate_asset_rights_batch(payload: List[AssetInput]):
    """Batch evaluate all assets for a video scene or storyboard."""
    return engine.evaluate_batch(payload)


@router.get("/{record_id}", response_model=AssetRightsResponse)
async def get_asset_rights_record(record_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch single asset rights record by ID."""
    repo = AssetRightsRepository(db)
    record = await repo.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Asset rights record not found")
    return record


@router.put("/{record_id}", response_model=AssetRightsResponse)
async def update_asset_rights_record(
    record_id: str,
    payload: AssetRightsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update license proof, attribution text, or status of an existing asset record."""
    repo = AssetRightsRepository(db)
    record = await repo.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Asset rights record not found")

    update_dict = payload.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(record, field, val)

    # Re-evaluate status if license was updated and status not explicitly provided
    if "license_type" in update_dict and "status" not in update_dict:
        verdict = engine.evaluate_asset(
            AssetInput(
                title=record.title,
                asset_type=record.asset_type,
                source=record.source,
                license_type=record.license_type,
                commercial_use_status=record.commercial_use_status,
                attribution_required=record.attribution_required,
                attribution_text=record.attribution_text,
            )
        )
        record.status = verdict.status

    updated = await repo.update(record)
    return updated


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset_rights_record(record_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an asset rights record."""
    repo = AssetRightsRepository(db)
    success = await repo.delete(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset rights record not found")
    return None


@router.post("/seed-defaults", response_model=List[AssetRightsResponse])
async def seed_starter_asset_rights(db: AsyncSession = Depends(get_db)):
    """Seeds starter channel visual and audio assets with verified license provenance."""
    repo = AssetRightsRepository(db)
    existing = await repo.list_records(limit=10)
    if existing:
        return existing

    starter_assets = [
        AssetRightsRecord(
            title="Channel Brand Avatar & Icon",
            asset_type="image",
            source="Internal Design Studio",
            creator_provider="Brand Owner",
            license_type="Self-Created",
            commercial_use_status=CommercialUseStatus.ALLOWED,
            attribution_required=False,
            license_proof="Owned brand intellectual property",
            status=AssetRightsStatus.VERIFIED,
            notes="Primary logo and brand mark for all video watermarks and overlays.",
        ),
        AssetRightsRecord(
            title="Lofi Synth Coding Background Music",
            asset_type="bgm",
            source="Free Music Archive",
            creator_provider="Kevin MacLeod",
            license_type="CC-BY-4.0",
            commercial_use_status=CommercialUseStatus.ALLOWED,
            attribution_required=True,
            attribution_text="Music: 'Lofi Synth' by Kevin MacLeod (incompetech.com), licensed under CC-BY 4.0",
            license_proof="https://incompetech.com/music/royalty-free/licenses/",
            status=AssetRightsStatus.REQUIRES_ATTRIBUTION,
            notes="Standard background music for tutorial and breakdown scenes.",
        ),
        AssetRightsRecord(
            title="Clean Terminal UI Font (JetBrains Mono)",
            asset_type="font",
            source="JetBrains GitHub Repository",
            creator_provider="JetBrains",
            license_type="OFL-1.1",
            commercial_use_status=CommercialUseStatus.ALLOWED,
            attribution_required=False,
            license_proof="https://github.com/JetBrains/JetBrainsMono/blob/master/OFL.txt",
            status=AssetRightsStatus.VERIFIED,
            notes="Primary code and on-screen caption monospaced font.",
        ),
        AssetRightsRecord(
            title="Local AI Inference Benchmark Graph",
            asset_type="chart",
            source="Internal Lab Benchmark Run #14",
            creator_provider="Content Studio Lab",
            license_type="Self-Created",
            commercial_use_status=CommercialUseStatus.ALLOWED,
            attribution_required=False,
            license_proof="Lab test output in data/benchmarks/run_14.json",
            status=AssetRightsStatus.VERIFIED,
            notes="Empirical benchmark chart used in video comparison hooks.",
        ),
    ]

    results = []
    for a in starter_assets:
        saved = await repo.create(a)
        results.append(saved)

    return results
