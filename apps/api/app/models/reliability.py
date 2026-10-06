import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CleanupAuditLog(Base, TimestampMixin):
    """Audit log tracking storage inspection and reference-safe cleanup executions."""
    __tablename__ = "cleanup_audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    
    # Mode: DRY_RUN, SAFE_DELETION
    mode: Mapped[str] = mapped_column(String(32), default="DRY_RUN", nullable=False)
    
    scanned_files_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_files_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deleted_files_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recovered_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    rules_applied: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    details: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    
    # Status: SUCCESS, FAILED, PARTIAL
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class StudioBackupRecord(Base, TimestampMixin):
    """Manifest of local studio backup snapshots with checksum integrity validation."""
    __tablename__ = "studio_backups"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    backup_name: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(512), nullable=False)
    
    # Type: FULL, SQLITE, CONFIG
    backup_type: Mapped[str] = mapped_column(String(32), default="FULL", nullable=False)
    
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    
    metadata_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    
    # Status: AVAILABLE, RESTORED, ARCHIVED
    status: Mapped[str] = mapped_column(String(32), default="AVAILABLE", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
