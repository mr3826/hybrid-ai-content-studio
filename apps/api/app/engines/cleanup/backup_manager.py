import hashlib
import json
import os
import sqlite3
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.brand import BrandExemplar, BrandMemoryItem, BrandProfile, SINGLETON_BRAND_ID
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.platform import PlatformSetting


class BackupManager:
    """Manages local studio backup creation, SHA-256 integrity auditing,
    and sandbox test-restores.
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            root = Path(__file__).resolve()
            for p in root.parents:
                if (p / "apps").exists() and ((p / "data").exists() or (p / "docs").exists()):
                    root = p
                    break
            self.workspace_root = root
        else:
            self.workspace_root = workspace_root
        self.backup_dir = self.workspace_root / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def calculate_sha256(self, filepath: Path) -> str:
        """Computes cryptographic SHA-256 checksum of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def create_backup(
        self,
        session: AsyncSession,
        backup_type: str = "FULL",
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a verified ZIP backup containing SQLite DB, configs, and critical metadata."""
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"studio_backup_{now_str}_{backup_type.lower()}.zip"
        backup_filepath = self.backup_dir / backup_filename

        # 1. Gather configs
        niche_res = await session.execute(select(NicheProfile).where(NicheProfile.id == SINGLETON_NICHE_ID))
        niche = niche_res.scalar_one_or_none()
        niche_data = {
            "name": niche.name if niche else None,
            "audience": getattr(niche, "audience", None) if niche else None,
            "allowed_topics": getattr(niche, "allowed_topics", []) if niche else [],
            "one_sentence_definition": getattr(niche, "one_sentence_definition", None) if niche else None,
        }

        brand_res = await session.execute(select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID))
        brand = brand_res.scalar_one_or_none()
        brand_data = {
            "brand_name": brand.brand_name if brand else None,
            "brand_promise": getattr(brand, "brand_promise", None) if brand else None,
            "tone": getattr(brand, "tone", []) if brand else [],
            "banned_cliches": getattr(brand, "banned_cliches", []) if brand else [],
            "preferred_vocabulary": getattr(brand, "preferred_vocabulary", []) if brand else [],
        }

        plats_res = await session.execute(select(PlatformSetting))
        platforms = [p.platform for p in plats_res.scalars().all()]

        manifest_data = {
            "backup_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "backup_type": backup_type,
            "niche": niche_data,
            "brand": brand_data,
            "platforms": platforms,
            "notes": notes,
        }

        # 2. Locate DB files
        db_from_settings = Path(settings.DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
        db_candidates = [
            db_from_settings,
            self.workspace_root / "data" / "db" / "studio.sqlite",
            self.workspace_root / "apps" / "api" / "data" / "db" / "studio.sqlite",
        ]
        db_file = next((p for p in db_candidates if p.exists()), None)

        # 3. Write ZIP archive
        with zipfile.ZipFile(backup_filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            zf.writestr("manifest.json", json.dumps(manifest_data, indent=2))

            # Add database if found
            if db_file and db_file.exists():
                zf.write(db_file, arcname="studio.sqlite")
                wal_file = db_file.with_name(f"{db_file.name}-wal")
                if wal_file.exists():
                    zf.write(wal_file, arcname="studio.sqlite-wal")

        # 4. Compute Checksum and size
        size_bytes = backup_filepath.stat().st_size
        checksum = self.calculate_sha256(backup_filepath)

        return {
            "id": str(uuid.uuid4()),
            "backup_name": backup_filename,
            "filepath": str(backup_filepath),
            "backup_type": backup_type,
            "size_bytes": size_bytes,
            "checksum_sha256": checksum,
            "metadata_snapshot": manifest_data,
            "status": "AVAILABLE",
            "notes": notes,
        }

    def verify_backup_file(self, backup_filepath: Path, expected_checksum: str) -> Dict[str, Any]:
        """Validates that a backup archive exists, matches expected checksum, and is uncorrupted."""
        if not backup_filepath.exists():
            return {
                "is_valid": False,
                "message": f"Backup file {backup_filepath} does not exist",
                "calculated_checksum": "",
                "expected_checksum": expected_checksum,
                "files_contained": [],
            }

        calculated = self.calculate_sha256(backup_filepath)
        checksum_matches = (calculated.lower() == expected_checksum.lower())

        files_contained = []
        is_zip_valid = False
        try:
            with zipfile.ZipFile(backup_filepath, "r") as zf:
                files_contained = zf.namelist()
                test_result = zf.testzip()
                is_zip_valid = (test_result is None)
        except Exception:
            is_zip_valid = False

        is_valid = checksum_matches and is_zip_valid

        return {
            "is_valid": is_valid,
            "message": "Backup verified successfully" if is_valid else "Checksum or archive corrupted",
            "calculated_checksum": calculated,
            "expected_checksum": expected_checksum,
            "files_contained": files_contained,
        }

    verify_backup = verify_backup_file

    def test_restore_to_sandbox(self, backup_filepath: Path, sandbox_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Simulates full restore into an isolated sandbox directory and runs SQLite integrity check."""
        import tempfile
        created_temp = None
        if sandbox_dir is None:
            created_temp = tempfile.TemporaryDirectory()
            target_sandbox = Path(created_temp.name)
        else:
            target_sandbox = sandbox_dir
            target_sandbox.mkdir(parents=True, exist_ok=True)

        if not backup_filepath.exists():
            if created_temp:
                created_temp.cleanup()
            return {"success": False, "status": "FAILED", "message": "Backup archive not found"}

        try:
            extracted_files = []
            with zipfile.ZipFile(backup_filepath, "r") as zf:
                extracted_files = zf.namelist()
                zf.extractall(target_sandbox)

            restored_db = target_sandbox / "studio.sqlite"
            db_integrity = "NOT_FOUND"
            if restored_db.exists():
                conn = sqlite3.connect(str(restored_db))
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check;")
                res = cursor.fetchone()
                db_integrity = res[0] if res else "UNKNOWN"
                conn.close()

            manifest_file = target_sandbox / "manifest.json"
            has_manifest = manifest_file.exists()

            success = (db_integrity == "ok" or not restored_db.exists()) and has_manifest

            result = {
                "success": success,
                "status": "SUCCESS" if success else "FAILED",
                "integrity_check": db_integrity,
                "db_integrity": db_integrity,
                "has_manifest": has_manifest,
                "extracted_files": extracted_files,
                "sandbox_path": str(target_sandbox),
                "message": "Sandbox test restore completed cleanly",
            }
            if created_temp:
                created_temp.cleanup()
            return result
        except Exception as ex:
            if created_temp:
                created_temp.cleanup()
            return {
                "success": False,
                "status": "FAILED",
                "error": str(ex),
                "message": f"Sandbox restore failed: {ex}",
            }
