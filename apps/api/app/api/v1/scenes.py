import base64
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.engines.scene_studio.adapters import LocalDeterministicVisualAdapter
from app.engines.scene_studio.contracts import (
    DecompositionRequest,
    SectionInput,
    StoryboardValidationResult,
)
from app.engines.scene_studio.engine import SceneStudioEngine
from app.models.asset_rights import AssetRightsRecord, AssetRightsStatus, CommercialUseStatus
from app.models.scene import MediaAsset, Scene, SceneStatus, TransitionType, VisualPriority
from app.models.script import ScriptDraft, ScriptSection
from app.repositories.scene_repository import MediaAssetRepository, SceneRepository

router = APIRouter(prefix="/scenes", tags=["Scene Studio Engine"])

engine = SceneStudioEngine()
visual_adapter = LocalDeterministicVisualAdapter()


# --- Pydantic Schemas ---

class SceneCreateRequest(BaseModel):
    script_id: str
    section_id: Optional[str] = None
    scene_order: int = 1
    narration: str = Field(..., min_length=1)
    timing_estimate: float = Field(3.0, ge=0.5, le=120.0)
    on_screen_text: Optional[str] = None
    visual_type: str = VisualPriority.REAL_SCREEN_RECORDING
    visual_source: Optional[str] = None
    evidence_reference: Optional[str] = None
    asset_rights_record_id: Optional[str] = None
    transition: str = TransitionType.CUT
    status: str = SceneStatus.DRAFT
    notes: Optional[str] = None


class SceneUpdateRequest(BaseModel):
    narration: Optional[str] = None
    timing_estimate: Optional[float] = None
    on_screen_text: Optional[str] = None
    visual_type: Optional[str] = None
    visual_source: Optional[str] = None
    evidence_reference: Optional[str] = None
    asset_rights_record_id: Optional[str] = None
    transition: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class SceneReorderRequest(BaseModel):
    scene_ids: List[str]


class MediaAssetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    file_path: Optional[str] = None
    file_content_base64: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    asset_type: str = "image"
    tags: List[str] = Field(default_factory=list)
    license_type: str = "Self-Created"


class SceneResponse(BaseModel):
    id: str
    script_id: str
    section_id: Optional[str] = None
    scene_order: int
    narration: str
    timing_estimate: float
    on_screen_text: Optional[str] = None
    visual_type: str
    visual_source: Optional[str] = None
    evidence_reference: Optional[str] = None
    asset_rights_record_id: Optional[str] = None
    transition: str
    status: str
    notes: Optional[str] = None
    asset_rights: Optional[Dict[str, Any]] = None
    created_at: Any
    updated_at: Any


class MediaAssetResponse(BaseModel):
    id: str
    name: str
    file_path: str
    file_size: int
    mime_type: str
    asset_type: str
    visual_priority: int
    tags: List[str]
    asset_rights_record_id: Optional[str] = None
    created_at: Any
    updated_at: Any


def _serialize_scene(s: Scene) -> Dict[str, Any]:
    rights_data = None
    if s.asset_rights:
        rights_data = {
            "id": s.asset_rights.id,
            "title": s.asset_rights.title,
            "license_type": s.asset_rights.license_type,
            "status": s.asset_rights.status,
            "attribution_required": s.asset_rights.attribution_required,
            "attribution_text": s.asset_rights.attribution_text,
        }
    return {
        "id": s.id,
        "script_id": s.script_id,
        "section_id": s.section_id,
        "scene_order": s.scene_order,
        "narration": s.narration,
        "timing_estimate": s.timing_estimate,
        "on_screen_text": s.on_screen_text,
        "visual_type": s.visual_type,
        "visual_source": s.visual_source,
        "evidence_reference": s.evidence_reference,
        "asset_rights_record_id": s.asset_rights_record_id,
        "transition": s.transition,
        "status": s.status,
        "notes": s.notes,
        "asset_rights": rights_data,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


# --- Endpoints ---

@router.get("/script/{script_id}", response_model=List[SceneResponse])
async def list_script_scenes(script_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch all storyboard scenes for a script ordered by sequence."""
    repo = SceneRepository(db)
    scenes = await repo.list_scenes_by_script(script_id)
    return [_serialize_scene(s) for s in scenes]


@router.post("/decompose/{script_id}", response_model=List[SceneResponse])
async def decompose_script_into_scenes(
    script_id: str,
    replace_existing: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Decomposes an approved script's sections into an ordered storyboard with visual hierarchy."""
    # 1. Fetch script with sections
    stmt = (
        select(ScriptDraft)
        .options(selectinload(ScriptDraft.sections))
        .where(ScriptDraft.id == script_id)
    )
    res = await db.execute(stmt)
    script = res.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    sections_input = [
        SectionInput(
            id=sec.id,
            section_type=sec.section_type,
            heading=sec.heading,
            narration=sec.narration,
            visual_cue=sec.visual_cue,
            linked_claim_ids=sec.linked_claim_ids or [],
        )
        for sec in script.sections
    ]

    req = DecompositionRequest(
        script_id=script.id,
        format=script.format,
        title=script.title,
        sections=sections_input,
        target_duration_sec=script.target_duration_sec,
    )

    scene_drafts = engine.decompose_script(req)

    repo = SceneRepository(db)
    if replace_existing:
        await repo.delete_scenes_by_script(script_id)

    created_scenes: List[Scene] = []
    for idx, draft in enumerate(scene_drafts, start=1):
        scene = Scene(
            script_id=script_id,
            scene_order=idx,
            narration=draft.narration,
            timing_estimate=draft.timing_estimate or 3.0,
            on_screen_text=draft.on_screen_text,
            visual_type=draft.visual_type or VisualPriority.REAL_SCREEN_RECORDING,
            visual_source=draft.visual_source,
            evidence_reference=draft.evidence_reference,
            transition=draft.transition or TransitionType.CUT,
            status=draft.status or SceneStatus.DRAFT,
            notes=draft.notes,
        )
        created_scenes.append(scene)

    saved = await repo.create_batch(created_scenes)
    # Re-fetch with relationships
    refetched = await repo.list_scenes_by_script(script_id)
    return [_serialize_scene(s) for s in refetched]


@router.post("", response_model=SceneResponse, status_code=status.HTTP_201_CREATED)
async def create_scene(payload: SceneCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new manual scene in the storyboard."""
    repo = SceneRepository(db)
    scene = Scene(
        script_id=payload.script_id,
        section_id=payload.section_id,
        scene_order=payload.scene_order,
        narration=payload.narration,
        timing_estimate=payload.timing_estimate,
        on_screen_text=payload.on_screen_text,
        visual_type=payload.visual_type,
        visual_source=payload.visual_source,
        evidence_reference=payload.evidence_reference,
        asset_rights_record_id=payload.asset_rights_record_id,
        transition=payload.transition,
        status=payload.status,
        notes=payload.notes,
    )
    saved = await repo.create_scene(scene)
    refetched = await repo.get_scene_by_id(saved.id)
    return _serialize_scene(refetched or saved)


@router.post("/assets", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED)
async def register_media_asset(
    payload: MediaAssetCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Registers a media asset, saving uploaded base64 data or referencing local path."""
    upload_dir = Path("data/assets/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path_str = payload.file_path or ""
    file_size = 0
    mime = payload.mime_type or "image/png"

    if payload.file_content_base64:
        file_ext = Path(payload.file_name or "media.png").suffix or ".png"
        unique_filename = f"{uuid.uuid4().hex[:12]}{file_ext}"
        dest_path = upload_dir / unique_filename
        raw_bytes = base64.b64decode(payload.file_content_base64)
        with open(dest_path, "wb") as f:
            f.write(raw_bytes)
        file_size = len(raw_bytes)
        dest_path_str = str(dest_path).replace("\\", "/")
    elif payload.file_path and Path(payload.file_path).exists():
        file_size = Path(payload.file_path).stat().st_size
    elif not dest_path_str:
        dest_path_str = f"data/assets/placeholders/{payload.name.lower().replace(' ', '_')}.png"

    rank = VisualPriority.RANK_MAP.get(payload.asset_type, 5)

    rights_record = AssetRightsRecord(
        title=payload.name,
        asset_type=payload.asset_type,
        source=f"Catalog: {payload.name}",
        creator_provider="Channel Creator",
        license_type=payload.license_type,
        commercial_use_status=CommercialUseStatus.ALLOWED if payload.license_type == "Self-Created" else CommercialUseStatus.UNKNOWN,
        status=AssetRightsStatus.VERIFIED if payload.license_type == "Self-Created" else AssetRightsStatus.UNKNOWN,
        uri=dest_path_str,
    )
    db.add(rights_record)
    await db.commit()
    await db.refresh(rights_record)

    asset = MediaAsset(
        name=payload.name,
        file_path=dest_path_str,
        file_size=file_size,
        mime_type=mime,
        asset_type=payload.asset_type,
        visual_priority=rank,
        tags=payload.tags,
        asset_rights_record_id=rights_record.id,
    )
    asset_repo = MediaAssetRepository(db)
    saved = await asset_repo.create_asset(asset)
    return saved


@router.get("/assets", response_model=List[MediaAssetResponse])
async def list_media_assets(
    asset_type: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve catalog of local media assets with tags and visual priority."""
    repo = MediaAssetRepository(db)
    return await repo.list_assets(asset_type=asset_type, query=query, limit=limit)


@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(scene_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch single scene by ID."""
    repo = SceneRepository(db)
    scene = await repo.get_scene_by_id(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return _serialize_scene(scene)


@router.put("/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: str,
    payload: SceneUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update scene narration, timing, visual type, or asset link."""
    repo = SceneRepository(db)
    scene = await repo.get_scene_by_id(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    update_dict = payload.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(scene, k, v)

    # Automatically set status to READY if visual_source is provided and no rights block
    if scene.visual_source and scene.status == SceneStatus.MISSING_ASSET:
        scene.status = SceneStatus.READY

    updated = await repo.update_scene(scene)
    refetched = await repo.get_scene_by_id(updated.id)
    return _serialize_scene(refetched or updated)


@router.delete("/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scene(scene_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a scene."""
    repo = SceneRepository(db)
    success = await repo.delete_scene(scene_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scene not found")
    return None


@router.post("/reorder/{script_id}", response_model=List[SceneResponse])
async def reorder_scenes(
    script_id: str,
    payload: SceneReorderRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reorder scenes in a script storyboard."""
    repo = SceneRepository(db)
    reordered = await repo.reorder_scenes(script_id, payload.scene_ids)
    return [_serialize_scene(s) for s in reordered]


@router.post("/validate-storyboard/{script_id}", response_model=StoryboardValidationResult)
async def validate_storyboard(script_id: str, db: AsyncSession = Depends(get_db)):
    """Validates the full storyboard for timing, empirical visual priority, and asset rights."""
    stmt = select(ScriptDraft).where(ScriptDraft.id == script_id)
    res = await db.execute(stmt)
    script = res.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    repo = SceneRepository(db)
    scenes = await repo.list_scenes_by_script(script_id)

    raw_scenes = []
    for s in scenes:
        rights_status = s.asset_rights.status if s.asset_rights else None
        raw_scenes.append({
            "scene_order": s.scene_order,
            "visual_type": s.visual_type,
            "visual_source": s.visual_source,
            "timing_estimate": s.timing_estimate,
            "evidence_reference": s.evidence_reference,
            "narration": s.narration,
            "rights_status": rights_status,
        })

    return engine.validate_storyboard(raw_scenes, target_duration=float(script.target_duration_sec))


@router.post("/generate-placeholder/{scene_id}", response_model=SceneResponse)
async def generate_scene_placeholder(scene_id: str, db: AsyncSession = Depends(get_db)):
    """Generates a local offline visual SVG card for testing scenes without external paid APIs."""
    repo = SceneRepository(db)
    scene = await repo.get_scene_by_id(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    generated = visual_adapter.generate_visual(
        prompt=scene.on_screen_text or scene.narration[:60],
        visual_type=scene.visual_type,
        title=f"Scene {scene.scene_order}: {scene.visual_type}",
    )

    scene.visual_source = generated["file_path"]
    scene.status = SceneStatus.READY
    updated = await repo.update_scene(scene)
    return _serialize_scene(updated)
