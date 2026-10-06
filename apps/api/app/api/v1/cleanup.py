import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engines.core.registry import engine_registry
from app.engines.cleanup.cleaner import StorageCleaner
from app.engines.cleanup.backup_manager import BackupManager
from app.engines.cleanup.contracts import (
    BackupCreateRequest,
    BackupRestoreRequest,
    BackupVerifyResponse,
    CleanupExecuteRequest,
    CleanupReport,
    FileCandidateInfo,
    ReliabilitySummaryResponse,
    StorageInspectionSummary,
    StudioBackupResponse,
)
from app.models.reliability import CleanupAuditLog, StudioBackupRecord
from app.repositories.cleanup_repository import CleanupRepository

router = APIRouter(prefix="/cleanup", tags=["Cleanup & Reliability"])


def _map_log_to_response(log: CleanupAuditLog) -> CleanupReport:
    return CleanupReport(
        id=log.id,
        run_id=log.run_id,
        mode=log.mode,
        scanned_files_count=log.scanned_files_count,
        candidate_files_count=log.candidate_files_count,
        deleted_files_count=log.deleted_files_count,
        recovered_bytes=log.recovered_bytes,
        status=log.status,
        created_at=log.created_at,
        details=log.details or [],
    )


def _map_backup_to_response(b: StudioBackupRecord) -> StudioBackupResponse:
    return StudioBackupResponse(
        id=b.id,
        backup_name=b.backup_name,
        filepath=b.filepath,
        backup_type=b.backup_type,
        size_bytes=b.size_bytes,
        checksum_sha256=b.checksum_sha256,
        metadata_snapshot=b.metadata_snapshot or {},
        status=b.status,
        created_at=b.created_at,
        notes=b.notes,
    )


@router.get("/summary", response_model=ReliabilitySummaryResponse)
async def get_reliability_summary(
    db: AsyncSession = Depends(get_db),
):
    """Returns studio-wide storage usage, database size, recoverable bytes, and reliability status."""
    repo = CleanupRepository(db)
    engine = engine_registry.get("cleanup")
    cleaner = engine.cleaner if engine else StorageCleaner(rules={})
    
    # Get active protected paths
    protected_paths = await repo.get_active_protected_paths()
    inspection = cleaner.inspect_storage(protected_filepaths=protected_paths)
    
    summary_data = await repo.get_reliability_summary(workspace_root=cleaner.workspace_root)
    summary_data["recoverable_bytes"] = inspection.recoverable_bytes
    summary_data["active_policies"] = engine.rules if engine else {}

    return ReliabilitySummaryResponse(**summary_data)


@router.get("/inspect", response_model=StorageInspectionSummary)
@router.post("/inspect", response_model=StorageInspectionSummary)
async def inspect_storage(
    payload: Optional[CleanupExecuteRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Scans monitored storage directories to identify candidate files and recoverable bytes."""
    repo = CleanupRepository(db)
    engine = engine_registry.get("cleanup")
    cleaner = engine.cleaner if engine else StorageCleaner(rules={})

    protected_paths = await repo.get_active_protected_paths()
    target_dirs = payload.target_directories if payload else None
    inspection = cleaner.inspect_storage(
        target_directories=target_dirs,
        protected_filepaths=protected_paths,
    )
    return inspection


@router.post("/execute", response_model=CleanupReport)
async def execute_cleanup(
    payload: CleanupExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Executes reference-safe cleanup or simulation, logging cryptographic audit record."""
    repo = CleanupRepository(db)
    engine = engine_registry.get("cleanup")
    cleaner = engine.cleaner if engine else StorageCleaner(rules={})

    protected_paths = await repo.get_active_protected_paths()
    inspection = cleaner.inspect_storage(
        target_directories=payload.target_directories,
        protected_filepaths=protected_paths,
    )

    execution_res = cleaner.execute_cleanup(
        inspection=inspection,
        dry_run=payload.dry_run,
        max_files=payload.max_files_to_delete or 500,
    )

    run_id = f"cln-{uuid.uuid4().hex[:12]}"
    audit_data = {
        "run_id": run_id,
        "mode": execution_res["mode"],
        "scanned_files_count": execution_res["scanned_files_count"],
        "candidate_files_count": execution_res["candidate_files_count"],
        "deleted_files_count": execution_res["deleted_files_count"],
        "recovered_bytes": execution_res["recovered_bytes"],
        "rules_applied": engine.rules if engine else {},
        "details": execution_res["details"],
        "status": execution_res["status"],
    }

    log = await repo.create_audit_log(audit_data)
    return _map_log_to_response(log)


@router.get("/logs", response_model=List[CleanupReport])
async def list_cleanup_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List historical cleanup audit logs."""
    repo = CleanupRepository(db)
    logs = await repo.list_audit_logs(limit=limit, offset=offset)
    return [_map_log_to_response(l) for l in logs]


@router.get("/logs/{log_id}", response_model=CleanupReport)
async def get_cleanup_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch single cleanup audit log details."""
    repo = CleanupRepository(db)
    log = await repo.get_audit_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Cleanup audit log not found")
    return _map_log_to_response(log)


@router.post("/backups", response_model=StudioBackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    payload: BackupCreateRequest = BackupCreateRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Creates a local verified ZIP backup archive containing SQLite DB, configs, and metadata."""
    repo = CleanupRepository(db)
    engine = engine_registry.get("cleanup")
    manager = engine.backup_manager if engine else BackupManager()

    backup_data = await manager.create_backup(
        session=db,
        backup_type=payload.backup_type,
        notes=payload.notes,
    )

    record = await repo.create_backup_record(backup_data)
    return _map_backup_to_response(record)


@router.get("/backups", response_model=List[StudioBackupResponse])
async def list_backups(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List available local studio backup archives."""
    repo = CleanupRepository(db)
    records = await repo.list_backup_records(limit=limit, offset=offset)
    return [_map_backup_to_response(r) for r in records]


@router.get("/backups/{backup_id}", response_model=StudioBackupResponse)
async def get_backup(
    backup_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve single studio backup record by ID."""
    repo = CleanupRepository(db)
    record = await repo.get_backup_record(backup_id)
    if not record:
        raise HTTPException(status_code=404, detail="Backup record not found")
    return _map_backup_to_response(record)


@router.post("/backups/{backup_id}/verify", response_model=BackupVerifyResponse)
async def verify_backup(
    backup_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Audits SHA-256 checksum and zip integrity of a backup archive."""
    repo = CleanupRepository(db)
    record = await repo.get_backup_record(backup_id)
    if not record:
        raise HTTPException(status_code=404, detail="Backup record not found")

    engine = engine_registry.get("cleanup")
    manager = engine.backup_manager if engine else BackupManager()

    verify_res = manager.verify_backup_file(
        backup_filepath=Path(record.filepath),
        expected_checksum=record.checksum_sha256,
    )

    return BackupVerifyResponse(
        backup_id=backup_id,
        is_valid=verify_res["is_valid"],
        calculated_checksum=verify_res["calculated_checksum"],
        expected_checksum=verify_res["expected_checksum"],
        files_contained=verify_res["files_contained"],
        message=verify_res["message"],
    )


@router.post("/backups/{backup_id}/test-restore")
async def test_restore_backup(
    backup_id: str,
    payload: BackupRestoreRequest = BackupRestoreRequest(dry_run=True),
    db: AsyncSession = Depends(get_db),
):
    """Restores backup archive into an isolated sandbox directory and validates SQLite PRAGMA integrity."""
    repo = CleanupRepository(db)
    record = await repo.get_backup_record(backup_id)
    if not record:
        raise HTTPException(status_code=404, detail="Backup record not found")

    engine = engine_registry.get("cleanup")
    manager = engine.backup_manager if engine else BackupManager()

    sandbox_dir = Path(tempfile.mkdtemp(prefix="studio_restore_test_"))
    try:
        restore_res = manager.test_restore_to_sandbox(
            backup_filepath=Path(record.filepath),
            sandbox_dir=sandbox_dir,
        )
        return restore_res
    finally:
        # Clean up temporary sandbox directory if dry_run
        if payload.dry_run and sandbox_dir.exists():
            shutil.rmtree(sandbox_dir, ignore_errors=True)
