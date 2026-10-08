import io
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.engines.export.contracts import ExportEngineInput
from app.engines.export.engine import ExportEngine
from app.models.brand import BrandProfile, SINGLETON_BRAND_ID
from app.models.content_family import ContentFamily, ContentItem
from app.models.evidence import Claim, EvidenceSource
from app.models.export import ExportPackage, PlatformPublication
from app.models.media import MediaPackage
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.platform import PlatformSetting
from app.models.research import ResearchPacket
from app.models.script import ScriptDraft, ScriptSection
from app.repositories.export_repository import ExportRepository
from app.repositories.publishing_repository import PublishingRepository
from app.repositories.quality_gate_repository import QualityGateRepository
from app.schemas.export import (
    ExportPackageRead,
    PlatformPublicationRead,
    PlatformPublicationUpdate,
    PublishingOverviewResponse,
)

logger = logging.getLogger("studio.api.export")

router = APIRouter(prefix="", tags=["Export & Publishing Assistant"])
engine = ExportEngine()


@router.get("/export/health")
async def get_export_engine_health():
    """Health check for the Export Engine."""
    health = engine.health()
    return {
        "status": health.status,
        "message": health.message,
        "checked_at": health.checked_at.isoformat(),
        "details": health.details,
    }


@router.post("/export/{item_id}", response_model=ExportPackageRead)
async def create_export_package(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generates a complete offline export package for an approved content item.
    
    Human Gate Enforcement:
    1. Content item MUST have an approved script (is_approved=True) before export package is generated.
    2. Content item MUST have a valid, approved Final Quality Gate audit (status='FINAL_APPROVED', is_approved=True).
    3. The quality gate audit MUST be fresh and match the active script version (not stale/superseded).
    """
    export_repo = ExportRepository(db)
    pub_repo = PublishingRepository(db)

    # 1. Fetch ContentItem with relations
    stmt = (
        select(ContentItem)
        .where(ContentItem.id == item_id)
        .options(
            selectinload(ContentItem.family).selectinload(ContentFamily.opportunity),
            selectinload(ContentItem.family).selectinload(ContentFamily.research_packet).selectinload(ResearchPacket.revisions),
            selectinload(ContentItem.family).selectinload(ContentFamily.primary_experiment),
            selectinload(ContentItem.evidence_selections),
        )
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content item '{item_id}' not found.",
        )

    # 2. Check Script and Human Approval Gate
    script_stmt = (
        select(ScriptDraft)
        .where(ScriptDraft.content_item_id == item_id)
        .options(selectinload(ScriptDraft.sections))
        .order_by(ScriptDraft.created_at.desc())
    )
    script_res = await db.execute(script_stmt)
    script = script_res.scalars().first()

    if not script:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot export item: No script draft exists. Generate and approve a script in Script Studio first.",
        )

    if not script.is_approved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Human Quality Gate Block: Cannot export unapproved script. "
                "Script must be reviewed and approved by the creator in Script Studio before export package generation."
            ),
        )

    # 3. Check Final Creator Quality Gate Audit & Freshness
    qg_repo = QualityGateRepository(db)
    audit = await qg_repo.get_audit_by_item(item.id)

    if not audit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Final Quality Gate Block: No final quality audit found for this content item. "
                "Run the 9-dimension quality gate evaluation and obtain final human approval before exporting."
            ),
        )

    if not audit.is_approved or audit.status != "FINAL_APPROVED":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Final Quality Gate Block: Quality audit status is '{audit.status}' (approved={audit.is_approved}). "
                "Export package generation requires an approved final quality gate (status=FINAL_APPROVED)."
            ),
        )

    # Stale Audit Check: Ensure the approved audit belongs to the current script version
    if audit.script_id and script.id and audit.script_id != script.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Final Quality Gate Stale Block: Quality audit was approved for script '{audit.script_id}', "
                f"but current active script is '{script.id}'. Re-run quality gate evaluation and re-approve."
            ),
        )

    # Stale Audit Check: Ensure script content was not modified after the quality gate audit was approved
    if audit.approved_at:
        audit_approved_at = (
            audit.approved_at if audit.approved_at.tzinfo else audit.approved_at.replace(tzinfo=timezone.utc)
        )
        if script.updated_at:
            script_updated_at = (
                script.updated_at if script.updated_at.tzinfo else script.updated_at.replace(tzinfo=timezone.utc)
            )
            if script_updated_at > audit_approved_at:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Final Quality Gate Stale Block: Script was modified after final quality gate approval. "
                        "Re-evaluate and re-approve the quality gate audit before exporting."
                    ),
                )
        if script.created_at:
            script_created_at = (
                script.created_at if script.created_at.tzinfo else script.created_at.replace(tzinfo=timezone.utc)
            )
            if script_created_at > audit_approved_at:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Final Quality Gate Stale Block: A new script draft was created after final quality gate approval. "
                        "Re-evaluate and re-approve the quality gate audit before exporting."
                    ),
                )

    # A prior audit cannot authorize an export after the current production media has failed or become mock.
    media_stmt = (
        select(MediaPackage)
        .where(MediaPackage.script_id == script.id)
        .order_by(MediaPackage.updated_at.desc())
    )
    media_res = await db.execute(media_stmt)
    media_package = media_res.scalars().first()
    if media_package:
        media_quality = media_package.quality_checks or {}
        production_media_ready = (
            media_package.status == "READY"
            and media_package.audio_path
            and media_package.video_path
            and media_quality.get("passed") is True
            and media_quality.get("production_eligible") is True
            and media_quality.get("ffprobe_verified") is True
            and media_quality.get("mock_audio") is not True
            and media_quality.get("mock_visual_assets") is not True
            and (
                media_quality.get("subtitles_requested") is not True
                or media_quality.get("subtitles_burned") is True
            )
        )
        if not production_media_ready:
            issues = "; ".join(media_quality.get("issues", []))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Export blocked: current media package is failed, mock, or lacks verified production audio/video. "
                    + (issues or "Re-render and pass Media QC before export.")
                ),
            )

    # 4. Fetch BrandProfile
    brand_res = await db.execute(select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID))
    brand = brand_res.scalar_one_or_none()
    brand_name = brand.brand_name if brand else "Fresh Local Content"
    brand_tone = ", ".join(brand.tone) if brand and brand.tone else "authoritative, practical"
    banned_cliches = brand.banned_cliches if brand and brand.banned_cliches else []

    # 4. Fetch Sources & Claims
    sources: List[Dict[str, Any]] = []
    if item.family and item.family.research_packet:
        sources_stmt = select(EvidenceSource).where(EvidenceSource.packet_id == item.family.research_packet_id)
        sources_res = await db.execute(sources_stmt)
        for s in sources_res.scalars().all():
            sources.append({
                "title": s.title,
                "url": s.url,
                "source_type": s.source_type,
                "author_or_org": s.author_or_org,
                "excerpt": s.key_excerpt,
            })

    claims: List[Dict[str, Any]] = []
    if item.evidence_selections:
        claim_ids = [sel.claim_id for sel in item.evidence_selections]
        claims_stmt = select(Claim).where(Claim.id.in_(claim_ids))
        claims_res = await db.execute(claims_stmt)
        for c in claims_res.scalars().all():
            claims.append({
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "verification_status": c.verification_status,
                "quote_or_metric": c.quote_or_metric,
            })

    experiments: List[Dict[str, Any]] = []
    if item.family and item.family.primary_experiment:
        exp = item.family.primary_experiment
        experiments.append({
            "name": exp.name,
            "hypothesis": exp.hypothesis,
            "outcome": exp.status,
        })

    # 5. Build section dictionaries
    sections_data: List[Dict[str, Any]] = []
    for sec in script.sections:
        sections_data.append({
            "section_type": sec.section_type,
            "heading": sec.heading,
            "narration": sec.narration,
            "visual_cue": sec.visual_cue,
            "estimated_seconds": sec.estimated_seconds,
            "word_count": sec.word_count,
            "linked_claim_ids": sec.linked_claim_ids or [],
        })

    # 6. Execute Export Engine
    input_payload = ExportEngineInput(
        content_item_id=item.id,
        working_title=item.working_title,
        slug=item.working_title.lower().replace(" ", "-"),
        format=item.format,
        platform_target=item.platform_target,
        script_id=script.id,
        script_version=script.version,
        script_title=script.title,
        sections=sections_data,
        brand_name=brand_name,
        brand_tone=brand_tone,
        banned_cliches=banned_cliches,
        sources=sources,
        claims=claims,
        originality_summary=item.family.summary if item.family else "",
        experiments=experiments,
        dry_run=False,
    )

    package_output = engine.generate_export_package(input_payload)

    # 7. Store or update ExportPackage in DB
    existing_package = await export_repo.get_latest_for_item(item.id)
    if existing_package:
        existing_package.package_slug = package_output.package_slug
        existing_package.export_dir = package_output.export_dir
        existing_package.manifest_data = package_output.manifest_data
        existing_package.files = package_output.files
        existing_package.checksum = package_output.checksum
        existing_package.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing_package)
        pkg = existing_package
    else:
        pkg = ExportPackage(
            content_item_id=item.id,
            package_slug=package_output.package_slug,
            export_dir=package_output.export_dir,
            manifest_data=package_output.manifest_data,
            files=package_output.files,
            checksum=package_output.checksum,
        )
        pkg = await export_repo.create(pkg)

    # 8. Create or update PlatformPublication records for YouTube, Facebook, Instagram, TikTok
    for platform_key, pdata in package_output.platform_packages.items():
        existing_pub = await pub_repo.get_by_item_and_platform(item.id, platform_key)
        if existing_pub:
            existing_pub.export_package_id = pkg.id
            existing_pub.title = pdata.title
            existing_pub.caption = pdata.caption
            existing_pub.hashtags = pdata.hashtags
            existing_pub.pinned_comment = pdata.pinned_comment
            if not existing_pub.checklist:
                existing_pub.checklist = pdata.checklist
            existing_pub.updated_at = datetime.now(timezone.utc)
        else:
            new_pub = PlatformPublication(
                content_item_id=item.id,
                export_package_id=pkg.id,
                platform=platform_key,
                status="NOT_READY",
                title=pdata.title,
                caption=pdata.caption,
                hashtags=pdata.hashtags,
                pinned_comment=pdata.pinned_comment,
                checklist=pdata.checklist,
            )
            db.add(new_pub)

    # 9. Update ContentItem status
    item.status = "EXPORTED"
    item.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pkg)

    return pkg


@router.get("/export/item/{item_id}", response_model=ExportPackageRead)
async def get_export_package_for_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the latest export package generated for a content item."""
    repo = ExportRepository(db)
    pkg = await repo.get_latest_for_item(item_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No export package found for item '{item_id}'.",
        )
    return pkg


@router.get("/export/package/{package_id}", response_model=ExportPackageRead)
async def get_export_package_by_id(
    package_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve export package by package ID."""
    repo = ExportRepository(db)
    pkg = await repo.get_by_id(package_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export package '{package_id}' not found.",
        )
    return pkg


@router.get("/export/item/{item_id}/download")
async def download_export_package_zip(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Streams a .zip archive of the complete export package for offline use."""
    repo = ExportRepository(db)
    pkg = await repo.get_latest_for_item(item_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No export package found for item '{item_id}'.",
        )

    export_path = Path(pkg.export_dir)
    if not export_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export package directory '{pkg.export_dir}' does not exist on disk.",
        )

    # Create zip archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(export_path):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(export_path)
                zf.write(file_path, arcname=str(rel_path))

    zip_buffer.seek(0)
    filename = f"{pkg.package_slug}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# -----------------------------------------------------------------------------
# Publishing Assistant API Endpoints
# -----------------------------------------------------------------------------

@router.get("/publishing/item/{item_id}", response_model=PublishingOverviewResponse)
async def get_publishing_overview(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves publishing overview, checklist status, platform tailored copy,
    and authenticated launcher URLs for a content item.
    """
    item_stmt = select(ContentItem).where(ContentItem.id == item_id)
    item_res = await db.execute(item_stmt)
    item = item_res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content item '{item_id}' not found.",
        )

    export_repo = ExportRepository(db)
    pub_repo = PublishingRepository(db)

    pkg = await export_repo.get_latest_for_item(item_id)
    publications = await pub_repo.get_by_item_id(item_id)

    # Fetch platform launcher URLs
    plat_stmt = select(PlatformSetting)
    plat_res = await db.execute(plat_stmt)
    plat_settings = plat_res.scalars().all()
    launch_urls: Dict[str, str] = {}
    for p in plat_settings:
        url = p.publishing_url or p.channel_url
        if url:
            launch_urls[p.platform] = url

    # Default platform fallback URLs if not configured
    default_fallbacks = {
        "youtube": "https://studio.youtube.com/",
        "facebook": "https://www.facebook.com/",
        "instagram": "https://www.instagram.com/",
        "tiktok": "https://www.tiktok.com/upload",
    }
    for k, v in default_fallbacks.items():
        if k not in launch_urls or not launch_urls[k]:
            launch_urls[k] = v

    item_dict = {
        "id": item.id,
        "content_family_id": item.content_family_id,
        "working_title": item.working_title,
        "format": item.format,
        "platform_target": item.platform_target,
        "status": item.status,
        "hook_type": item.hook_type,
        "angle": item.angle,
        "viewer_value": item.viewer_value,
    }

    return PublishingOverviewResponse(
        content_item=item_dict,
        export_package=pkg,
        publications=publications,
        platform_launch_urls=launch_urls,
    )


@router.patch("/publishing/{publication_id}", response_model=PlatformPublicationRead)
async def update_platform_publication(
    publication_id: str,
    payload: PlatformPublicationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Updates a platform publication's checklist, copy, or manual publication status.
    
    URL Validation Invariant:
    If status is marked as 'PUBLISHED', a valid HTTPS post_url MUST be provided.
    """
    pub_repo = PublishingRepository(db)
    pub = await pub_repo.get_by_id(publication_id)
    if not pub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform publication '{publication_id}' not found.",
        )

    updates: Dict[str, Any] = {}

    if payload.status is not None:
        target_status = payload.status.upper()
        if target_status not in ("NOT_READY", "READY", "PUBLISHED", "SKIPPED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{payload.status}'. Allowed: NOT_READY, READY, PUBLISHED, SKIPPED",
            )
        
        # When moving to PUBLISHED, require a valid HTTPS URL
        if target_status == "PUBLISHED":
            target_url = payload.post_url or pub.post_url
            if not target_url or not target_url.startswith("https://"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Cannot mark platform as PUBLISHED without a valid HTTPS post URL (e.g. 'https://youtube.com/watch?v=...').",
                )
            updates["published_at"] = payload.published_at or datetime.now(timezone.utc)

        updates["status"] = target_status

    if payload.checklist is not None:
        # Merge checklist with existing
        merged_checklist = dict(pub.checklist or {})
        merged_checklist.update(payload.checklist)
        updates["checklist"] = merged_checklist

        # If user did not explicitly supply a status, auto-calculate readiness:
        # If all 7 items are checked and status is NOT_READY, transition to READY
        if payload.status is None and pub.status == "NOT_READY":
            all_checked = all(merged_checklist.get(k, False) for k in [
                "media_ready", "thumbnail_ready", "title_caption_ready",
                "sources_checked", "asset_rights_verified",
            ])
            if all_checked:
                updates["status"] = "READY"

    if payload.title is not None:
        updates["title"] = payload.title
    if payload.caption is not None:
        updates["caption"] = payload.caption
    if payload.hashtags is not None:
        updates["hashtags"] = payload.hashtags
    if payload.pinned_comment is not None:
        updates["pinned_comment"] = payload.pinned_comment
    if payload.post_url is not None:
        if payload.post_url and not payload.post_url.startswith("https://"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post URL must be an HTTPS URL.",
            )
        updates["post_url"] = payload.post_url
    if payload.platform_post_id is not None:
        updates["platform_post_id"] = payload.platform_post_id
    if payload.notes is not None:
        updates["notes"] = payload.notes

    updated_pub = await pub_repo.update(publication_id, updates)
    return updated_pub


@router.get("/publishing/list")
async def list_publishable_items(
    status_filter: Optional[str] = Query(None, description="Filter by ContentItem.status"),
    db: AsyncSession = Depends(get_db),
):
    """Lists content items eligible for or undergoing manual publishing.
    Eligible statuses: SCRIPT_APPROVED, EXPORTED, READY_TO_PUBLISH, PARTIALLY_PUBLISHED, PUBLISHED.
    """
    eligible_statuses = [
        "SCRIPT_APPROVED",
        "EXPORTED",
        "READY_TO_PUBLISH",
        "PARTIALLY_PUBLISHED",
        "PUBLISHED",
    ]
    stmt = (
        select(ContentItem)
        .options(selectinload(ContentItem.family))
        .order_by(ContentItem.updated_at.desc())
    )
    if status_filter and status_filter != "all":
        stmt = stmt.where(ContentItem.status == status_filter)
    else:
        stmt = stmt.where(ContentItem.status.in_(eligible_statuses))

    res = await db.execute(stmt)
    items = res.scalars().all()

    # Enrich each item with publication summary
    pub_repo = PublishingRepository(db)
    export_repo = ExportRepository(db)

    results = []
    for it in items:
        pubs = await pub_repo.get_by_item_id(it.id)
        latest_pkg = await export_repo.get_latest_for_item(it.id)
        pub_summary = {p.platform: p.status for p in pubs}
        results.append({
            "id": it.id,
            "working_title": it.working_title,
            "format": it.format,
            "platform_target": it.platform_target,
            "status": it.status,
            "family_id": it.content_family_id,
            "family_title": it.family.title if it.family else "",
            "has_export": latest_pkg is not None,
            "export_slug": latest_pkg.package_slug if latest_pkg else None,
            "checksum": latest_pkg.checksum if latest_pkg else None,
            "platform_statuses": pub_summary,
            "updated_at": it.updated_at.isoformat(),
        })

    return results
