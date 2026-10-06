import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.engines.cleanup.contracts import FileCandidateInfo, StorageInspectionSummary


class StorageCleaner:
    """Core analytical and operational logic for reference-safe storage retention,
    recoverable bytes estimation, and safe disk cleanup.
    """

    def __init__(self, rules: Dict[str, Any], workspace_root: Optional[Path] = None):
        self.rules = rules or {}
        # Locate project root (containing tmp, cache, runtime, exports, data)
        if workspace_root is None:
            root = Path(__file__).resolve()
            for p in root.parents:
                if (p / "apps").exists() and ((p / "data").exists() or (p / "docs").exists()):
                    root = p
                    break
            self.workspace_root = root
        else:
            self.workspace_root = workspace_root

    def get_standard_directories(self) -> Dict[str, Path]:
        """Returns map of standard monitored storage directories."""
        return {
            "tmp": self.workspace_root / "tmp",
            "cache": self.workspace_root / "cache",
            "runtime": self.workspace_root / "runtime",
            "exports": self.workspace_root / "exports",
            "api_data": self.workspace_root / "apps" / "api" / "data",
        }

    def inspect_storage(
        self,
        target_directories: Optional[List[str]] = None,
        protected_filepaths: Optional[Set[str]] = None,
    ) -> StorageInspectionSummary:
        """Scans monitored storage directories, identifies candidates based on retention policies,
        and ensures active references are strictly protected.
        """
        protected_set = set(os.path.normpath(p).lower() for p in (protected_filepaths or set()))
        now_ts = datetime.now(timezone.utc).timestamp()

        retention = self.rules.get("retention_policies", {})
        tmp_retention_hrs = retention.get("tmp_retention_hours", 24)
        cache_retention_hrs = retention.get("cache_retention_hours", 24)
        failed_render_hrs = retention.get("failed_render_temp_days", 3) * 24
        exports_retention_hrs = retention.get("exports_retention_days", 30) * 24

        standard_dirs = self.get_standard_directories()
        dirs_to_scan = standard_dirs
        if target_directories:
            dirs_to_scan = {k: v for k, v in standard_dirs.items() if k in target_directories}

        total_files = 0
        total_bytes = 0
        candidates: List[FileCandidateInfo] = []
        directories_scanned: List[str] = []

        for dir_key, dir_path in dirs_to_scan.items():
            if not dir_path.exists():
                continue

            directories_scanned.append(str(dir_path))
            for root, _, files in os.walk(dir_path):
                for f in files:
                    file_path = Path(root) / f
                    # Skip .gitkeep
                    if f == ".gitkeep":
                        continue

                    try:
                        stat = file_path.stat()
                        size = stat.st_size
                        mtime = stat.st_mtime
                        age_hours = max(0.0, (now_ts - mtime) / 3600.0)
                    except OSError:
                        continue

                    total_files += 1
                    total_bytes += size

                    norm_path = os.path.normpath(str(file_path)).lower()
                    is_protected = False
                    protection_reason = None

                    # Invariant 1: Check database files and journal/wal
                    if any(norm_path.endswith(ext) for ext in (".sqlite", ".db", "-wal", "-shm", "-journal")):
                        is_protected = True
                        protection_reason = "Protected Database or Journal File"

                    # Invariant 2: Check active project and evidence references
                    elif norm_path in protected_set or any(p in norm_path for p in protected_set if len(p) > 5):
                        is_protected = True
                        protection_reason = "Active Studio Project Reference / Evidence Asset"

                    # Categorize and check retention
                    try:
                        rel_path = file_path.relative_to(self.workspace_root).as_posix().lower()
                    except ValueError:
                        rel_path = f.lower()

                    category = dir_key
                    threshold_hrs = tmp_retention_hrs
                    if dir_key == "cache":
                        threshold_hrs = cache_retention_hrs
                    elif dir_key == "exports":
                        threshold_hrs = exports_retention_hrs
                    elif dir_key == "runtime" or "render" in rel_path:
                        category = "failed_render"
                        threshold_hrs = failed_render_hrs

                    eligible = (age_hours >= threshold_hrs) and not is_protected

                    if age_hours >= threshold_hrs or is_protected:
                        candidates.append(
                            FileCandidateInfo(
                                path=str(file_path),
                                filename=f,
                                directory=str(Path(root)),
                                category=category,
                                size_bytes=size,
                                age_hours=round(age_hours, 1),
                                is_protected=is_protected,
                                protection_reason=protection_reason,
                                eligible_for_deletion=eligible,
                            )
                        )

        recoverable_bytes = sum(c.size_bytes for c in candidates if c.eligible_for_deletion)
        protected_count = sum(1 for c in candidates if c.is_protected)
        eligible_count = sum(1 for c in candidates if c.eligible_for_deletion)

        return StorageInspectionSummary(
            total_files_scanned=total_files,
            total_bytes_scanned=total_bytes,
            candidates_count=eligible_count,
            recoverable_bytes=recoverable_bytes,
            protected_files_count=protected_count,
            directories_scanned=directories_scanned,
            candidates=candidates,
        )

    def execute_cleanup(
        self,
        inspection: StorageInspectionSummary,
        dry_run: bool = True,
        max_files: int = 500,
    ) -> Dict[str, Any]:
        """Safely executes file unlinking for eligible non-protected candidates."""
        deleted_count = 0
        recovered_bytes = 0
        details: List[Dict[str, Any]] = []

        eligible_candidates = [c for c in inspection.candidates if c.eligible_for_deletion][:max_files]

        for cand in eligible_candidates:
            cand_dict = cand.model_dump()
            if dry_run:
                cand_dict["action"] = "SIMULATED_DELETE"
                cand_dict["success"] = True
                deleted_count += 1
                recovered_bytes += cand.size_bytes
            else:
                try:
                    p = Path(cand.path)
                    if p.exists() and p.is_file():
                        p.unlink()
                        cand_dict["action"] = "DELETED"
                        cand_dict["success"] = True
                        deleted_count += 1
                        recovered_bytes += cand.size_bytes
                    else:
                        cand_dict["action"] = "FILE_NOT_FOUND"
                        cand_dict["success"] = False
                except Exception as ex:
                    cand_dict["action"] = "ERROR"
                    cand_dict["error"] = str(ex)
                    cand_dict["success"] = False

            details.append(cand_dict)

        return {
            "mode": "DRY_RUN" if dry_run else "SAFE_DELETION",
            "scanned_files_count": inspection.total_files_scanned,
            "candidate_files_count": len(eligible_candidates),
            "deleted_files_count": deleted_count,
            "recovered_bytes": recovered_bytes,
            "details": details,
            "status": "SUCCESS",
        }
