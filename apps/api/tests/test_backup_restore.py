import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.cleanup.backup_manager import BackupManager


@pytest.mark.asyncio
async def test_backup_creation_and_integrity(db_session: AsyncSession, tmp_path: Path):
    manager = BackupManager(workspace_root=tmp_path)

    # Create dummy database in mock workspace data/db/studio.sqlite
    db_dir = tmp_path / "data" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "studio.sqlite"

    # Initialize a valid sqlite database file
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, note TEXT);")
    cursor.execute("INSERT INTO test_tbl (note) VALUES ('fresh studio backup test');")
    conn.commit()
    conn.close()

    # 1. Create backup
    backup_meta = await manager.create_backup(
        session=db_session,
        backup_type="FULL",
        notes="Automated test backup run",
    )

    assert backup_meta is not None
    backup_file = Path(backup_meta["filepath"])
    assert backup_file.exists()
    assert backup_meta["size_bytes"] > 0
    assert len(backup_meta["checksum_sha256"]) == 64

    # 2. Inspect ZIP contents
    with zipfile.ZipFile(backup_file, "r") as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "studio.sqlite" in names

        # Check manifest contents
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["backup_type"] == "FULL"
        assert "niche" in manifest
        assert "brand" in manifest

    # 3. Verify backup checksum
    verify_res = manager.verify_backup(backup_file, backup_meta["checksum_sha256"])
    assert verify_res["is_valid"] is True
    assert verify_res["calculated_checksum"] == backup_meta["checksum_sha256"]

    # 4. Tampered checksum should fail verification
    bad_verify = manager.verify_backup(backup_file, "bad" * 16)
    assert bad_verify["is_valid"] is False


@pytest.mark.asyncio
async def test_sandbox_test_restore(db_session: AsyncSession, tmp_path: Path):
    manager = BackupManager(workspace_root=tmp_path)

    # Create dummy database
    db_dir = tmp_path / "data" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "studio.sqlite"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE items (id TEXT, name TEXT);")
    cursor.execute("INSERT INTO items VALUES ('1', 'Sandbox Validation');")
    conn.commit()
    conn.close()

    backup_meta = await manager.create_backup(
        session=db_session,
        backup_type="FULL",
    )
    backup_file = Path(backup_meta["filepath"])

    # Test sandbox restore
    restore_report = manager.test_restore_to_sandbox(backup_file)
    assert restore_report["status"] == "SUCCESS"
    assert restore_report["integrity_check"] == "ok"
    assert "studio.sqlite" in restore_report["extracted_files"]
