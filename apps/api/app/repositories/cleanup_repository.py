import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reliability import CleanupAuditLog, StudioBackupRecord
from app.models.scene import MediaAsset
from app.models.media import MediaPackage
from app.models.export import ExportPackage
from app.models.asset_rights import AssetRightsRecord
from app.repositories.base import BaseRepository


class CleanupRepository(BaseRepository[CleanupAuditLog]):
    """Storage repository boundary for cleanup audit logging, backup registry,
    and active entity reference protection.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_audit_log(self, data: Dict[str, Any]) -> CleanupAuditLog:
        """Persists a cleanup execution or inspection audit record."""
        log = CleanupAuditLog(
            id=data.get("id") or str(uuid.uuid4()),
            run_id=data.get("run_id") or str(uuid.uuid4()),
            mode=data.get("mode", "DRY_RUN"),
            scanned_files_count=data.get("scanned_files_count", 0),
            candidate_files_count=data.get("candidate_files_count", 0),
            deleted_files_count=data.get("deleted_files_count", 0),
            recovered_bytes=data.get("recovered_bytes", 0),
            rules_applied=data.get("rules_applied", {}),
            details=data.get("details", []),
            status=data.get("status", "SUCCESS"),
            error_message=data.get("error_message"),
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_audit_log(self, log_id: str) -> Optional[CleanupAuditLog]:
        """Fetch single audit log by ID."""
        stmt = select(CleanupAuditLog).where(CleanupAuditLog.id == log_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_audit_logs(self, limit: int = 50, offset: int = 0) -> List[CleanupAuditLog]:
        """List audit logs sorted by execution timestamp descending."""
        stmt = select(CleanupAuditLog).order_by(CleanupAuditLog.created_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_backup_record(self, data: Dict[str, Any]) -> StudioBackupRecord:
        """Persists a new verified backup record."""
        rec = StudioBackupRecord(
            id=data.get("id") or str(uuid.uuid4()),
            backup_name=data["backup_name"],
            filepath=data["filepath"],
            backup_type=data.get("backup_type", "FULL"),
            size_bytes=data.get("size_bytes", 0),
            checksum_sha256=data["checksum_sha256"],
            metadata_snapshot=data.get("metadata_snapshot", {}),
            status=data.get("status", "AVAILABLE"),
            notes=data.get("notes"),
        )
        self.session.add(rec)
        await self.session.commit()
        await self.session.refresh(rec)
        return rec

    async def get_backup_record(self, backup_id: str) -> Optional[StudioBackupRecord]:
        """Fetch single backup record by ID."""
        stmt = select(StudioBackupRecord).where(StudioBackupRecord.id == backup_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_backup_records(self, limit: int = 50, offset: int = 0) -> List[StudioBackupRecord]:
        """List backup records sorted by creation timestamp descending."""
        stmt = select(StudioBackupRecord).order_by(StudioBackupRecord.created_at.desc()).offset(offset).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_backup_status(self, backup_id: str, status: str) -> Optional[StudioBackupRecord]:
        """Updates status of a backup record."""
        rec = await self.get_backup_record(backup_id)
        if not rec:
            return None
        rec.status = status
        await self.session.commit()
        await self.session.refresh(rec)
        return rec

    async def get_active_protected_paths(self) -> Set[str]:
        """Queries database entities to gather all file paths that must NEVER be deleted."""
        protected: Set[str] = set()

        # 1. Media Assets
        try:
            m_res = await self.session.execute(select(MediaAsset.file_path))
            for path in m_res.scalars().all():
                if path:
                    protected.add(path)
        except Exception:
            pass

        # 2. Export Packages
        try:
            e_res = await self.session.execute(select(ExportPackage.archive_path))
            for path in e_res.scalars().all():
                if path:
                    protected.add(path)
        except Exception:
            pass

        # 3. Media Packages
        try:
            mp_res = await self.session.execute(
                select(MediaPackage.video_path, MediaPackage.audio_path, MediaPackage.subtitle_path, MediaPackage.timeline_path)
            )
            for row in mp_res.all():
                for item in row:
                    if item:
                        protected.add(item)
        except Exception:
            pass

        # 4. Asset Rights URIs
        try:
            ar_res = await self.session.execute(select(AssetRightsRecord.uri))
            for path in ar_res.scalars().all():
                if path:
                    protected.add(path)
        except Exception:
            pass

        return protected

    async def get_reliability_summary(self, workspace_root: Path) -> Dict[str, Any]:
        """Calculates storage usage, database size, and counts of backups and audit logs."""
        # 1. Database size
        db_path = workspace_root / "data" / "db" / "studio.sqlite"
        db_size = db_path.stat().st_size if db_path.exists() else 0

        # 2. Total storage usage in workspace
        storage_dirs = ["tmp", "cache", "runtime", "exports", "backups"]
        total_storage = 0
        for d in storage_dirs:
            dp = workspace_root / d
            if dp.exists():
                for root, _, files in os.walk(dp):
                    for f in files:
                        try:
                            total_storage += (Path(root) / f).stat().st_size
                        except OSError:
                            pass

        # 3. Counts and timestamps
        logs = await self.list_audit_logs(limit=1)
        last_cleanup = logs[0].created_at if logs else None
        log_count_res = await self.session.execute(select(func.count(CleanupAuditLog.id)))
        log_count = log_count_res.scalar() or 0

        backups = await self.list_backup_records(limit=1)
        last_backup = backups[0].created_at if backups else None
        backup_count_res = await self.session.execute(select(func.count(StudioBackupRecord.id)))
        backup_count = backup_count_res.scalar() or 0

        return {
            "storage_usage_bytes": total_storage,
            "database_size_bytes": db_size,
            "last_cleanup_timestamp": last_cleanup,
            "last_backup_timestamp": last_backup,
            "total_backups_count": backup_count,
            "audit_logs_count": log_count,
        }
