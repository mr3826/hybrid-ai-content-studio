from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileCandidateInfo(BaseModel):
    path: str
    filename: str
    directory: str
    category: str
    size_bytes: int
    age_hours: float
    is_protected: bool
    protection_reason: Optional[str] = None
    eligible_for_deletion: bool


class StorageInspectionSummary(BaseModel):
    total_files_scanned: int
    total_bytes_scanned: int
    candidates_count: int
    recoverable_bytes: int
    protected_files_count: int
    directories_scanned: List[str]
    candidates: List[FileCandidateInfo] = Field(default_factory=list)


class CleanupExecuteRequest(BaseModel):
    dry_run: bool = True
    target_directories: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    max_files_to_delete: Optional[int] = 500


class CleanupReport(BaseModel):
    id: str
    run_id: str
    mode: str
    scanned_files_count: int
    candidate_files_count: int
    deleted_files_count: int
    recovered_bytes: int
    status: str
    created_at: Optional[datetime] = None
    details: List[Dict[str, Any]] = Field(default_factory=list)


class BackupCreateRequest(BaseModel):
    backup_name: Optional[str] = None
    backup_type: str = "FULL"  # FULL, SQLITE, CONFIG
    notes: Optional[str] = None


class BackupRestoreRequest(BaseModel):
    dry_run: bool = True
    target_dir: Optional[str] = None


class StudioBackupResponse(BaseModel):
    id: str
    backup_name: str
    filepath: str
    backup_type: str
    size_bytes: int
    checksum_sha256: str
    metadata_snapshot: Dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: Optional[datetime] = None
    notes: Optional[str] = None


class BackupVerifyResponse(BaseModel):
    backup_id: str
    is_valid: bool
    calculated_checksum: str
    expected_checksum: str
    files_contained: List[str] = Field(default_factory=list)
    message: str


class ReliabilitySummaryResponse(BaseModel):
    storage_usage_bytes: int
    database_size_bytes: int
    recoverable_bytes: int
    last_cleanup_timestamp: Optional[datetime] = None
    last_backup_timestamp: Optional[datetime] = None
    total_backups_count: int
    audit_logs_count: int
    active_policies: Dict[str, Any] = Field(default_factory=dict)
