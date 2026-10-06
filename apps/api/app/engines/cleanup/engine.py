from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.cleanup.cleaner import StorageCleaner
from app.engines.cleanup.backup_manager import BackupManager


class CleanupEngine(BaseEngine):
    """Cleanup Engine.
    Executes reference-safe storage retention, cache pruning, recoverable bytes calculation,
    safe deletion, and local backup reliability auditing.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).parent
        super().__init__(engine_dir=engine_dir)
        self.cleaner = StorageCleaner(rules=self.rules)
        self.backup_manager = BackupManager()

    @property
    def version(self) -> str:
        return self.manifest.version

    def validate_config(self) -> None:
        """Validates that cleanup engine rules and invariant protections are present."""
        if not self.rules:
            raise ValueError(f"CleanupEngine rules could not be loaded from {self.engine_dir / 'rules.yaml'}")
        if "retention_policies" not in self.rules:
            raise ValueError("CleanupEngine rules must define 'retention_policies'")
        if "protected_invariants" not in self.rules:
            raise ValueError("CleanupEngine rules must define 'protected_invariants'")

    def health(self) -> EngineHealth:
        """Returns engine health status."""
        has_rules = self.rules is not None and len(self.rules) > 0
        healthy = has_rules and "retention_policies" in self.rules
        return EngineHealth(
            status="healthy" if healthy else "degraded",
            message="Cleanup Engine operational with reference-safe storage retention & backup manager.",
            details={
                "has_rules": has_rules,
                "engine_version": self.version,
                "retention_policies": self.rules.get("retention_policies", {}),
                "protected_invariants": self.rules.get("protected_invariants", {}),
            },
        )

    async def run(self, context: EngineContext, session=None) -> EngineResult:
        """Inspects storage directories and executes safe cleanup according to mode."""
        started_at = datetime.now(timezone.utc)
        params = context.parameters or {}
        dry_run = context.dry_run or params.get("dry_run", True)
        target_dirs = params.get("target_directories")
        protected_paths = set(params.get("protected_filepaths", []))

        # 1. Inspect storage
        inspection = self.cleaner.inspect_storage(
            target_directories=target_dirs,
            protected_filepaths=protected_paths,
        )

        # 2. Execute cleanup
        execution = self.cleaner.execute_cleanup(
            inspection=inspection,
            dry_run=dry_run,
            max_files=params.get("max_files_to_delete", 500),
        )

        ended_at = datetime.now(timezone.utc)
        mode_label = "Dry-Run" if dry_run else "Safe Deletion"
        recovered_mb = execution["recovered_bytes"] / (1024 * 1024)

        return EngineResult(
            engine_id=self.manifest.id,
            engine_version=self.manifest.version,
            run_id=context.run_id,
            success=True,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((ended_at - started_at).total_seconds() * 1000),
            summary=f"[{mode_label}] Scanned {inspection.total_files_scanned} files across {len(inspection.directories_scanned)} directories. Processed {execution['deleted_files_count']} files, recovered {recovered_mb:.2f} MB.",
            input_count=inspection.total_files_scanned,
            output_count=execution["deleted_files_count"],
            outputs=[{
                "inspection": inspection.model_dump(),
                "execution": execution,
            }],
            rules_version=self.rules.get("rules_version", "1.0.0"),
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Dry run: identifies eligible files and recoverable bytes without deleting anything."""
        context.dry_run = True
        return await self.run(context)

    def explain(self, result_id: str) -> EngineExplanation:
        """Explains reference-safe retention methodology and protected invariants."""
        return EngineExplanation(
            result_id=result_id,
            summary="Reference-Safe Retention & Pruning Model: Evaluates temporary, cache, and rendered assets against time-based retention thresholds while unconditionally protecting active project references, evidence proofs, and database files.",
            factors=[
                {
                    "factor": "Non-Negotiable Invariants",
                    "weight": 0.45,
                    "description": "Permanently protects database files, active scene/video references, and evidence source/license proofs from deletion.",
                },
                {
                    "factor": "Time-Decay Retention Tiers",
                    "weight": 0.35,
                    "description": "Applies tiered expiry thresholds: 24h for temp/cache, 3d for failed renders, 7d for unused generated assets, 30d for published final exports.",
                },
                {
                    "factor": "Recoverable Bytes Auditing",
                    "weight": 0.20,
                    "description": "Simulates exact candidate unlinking in dry-run mode and creates cryptographic audit logs for every operation.",
                },
            ],
        )
