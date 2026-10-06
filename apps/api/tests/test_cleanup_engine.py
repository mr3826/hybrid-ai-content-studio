import os
import tempfile
import time
from pathlib import Path
import pytest
from app.engines.cleanup.cleaner import StorageCleaner
from app.engines.cleanup.engine import CleanupEngine
from app.engines.core.registry import engine_registry


@pytest.fixture
def mock_storage(tmp_path: Path):
    """Sets up a mock workspace with standard directories and mock files."""
    tmp_dir = tmp_path / "tmp"
    cache_dir = tmp_path / "cache"
    runtime_dir = tmp_path / "runtime"
    exports_dir = tmp_path / "exports"
    db_dir = tmp_path / "data" / "db"

    for d in (tmp_dir, cache_dir, runtime_dir, exports_dir, db_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Fresh file in tmp (1 hour old) -> should NOT be eligible for deletion
    fresh_tmp = tmp_dir / "fresh.txt"
    fresh_tmp.write_text("fresh content")

    # 2. Old file in tmp (48 hours old) -> should be eligible for deletion
    old_tmp = tmp_dir / "old_job.json"
    old_tmp.write_text("old job content")
    old_time = time.time() - (48 * 3600)
    os.utime(old_tmp, (old_time, old_time))

    # 3. Old cache file (30 hours old) -> eligible
    old_cache = cache_dir / "cached_model.bin"
    old_cache.write_bytes(b"x" * 1024)
    cache_time = time.time() - (30 * 3600)
    os.utime(old_cache, (cache_time, cache_time))

    # 4. Old file in runtime that is marked as protected project asset -> NOT eligible
    protected_file = runtime_dir / "protected_voice.wav"
    protected_file.write_bytes(b"audio" * 200)
    prot_time = time.time() - (72 * 3600)
    os.utime(protected_file, (prot_time, prot_time))

    # 5. Database file in data/db -> NEVER eligible regardless of age
    db_file = db_dir / "studio.sqlite"
    db_file.write_text("sqlite mock")
    os.utime(db_file, (prot_time, prot_time))

    return {
        "root": tmp_path,
        "fresh_tmp": fresh_tmp,
        "old_tmp": old_tmp,
        "old_cache": old_cache,
        "protected_file": protected_file,
        "db_file": db_file,
    }


def test_cleaner_inspect_storage(mock_storage):
    root = mock_storage["root"]
    protected_paths = {str(mock_storage["protected_file"])}

    rules = {
        "retention_policies": {
            "tmp_retention_hours": 24,
            "cache_retention_hours": 24,
        }
    }
    cleaner = StorageCleaner(rules=rules, workspace_root=root)
    summary = cleaner.inspect_storage(protected_filepaths=protected_paths)

    assert summary.total_files_scanned >= 4
    assert summary.candidates_count >= 2

    # Check that old_tmp and old_cache are candidates
    candidate_names = [c.filename for c in summary.candidates if c.eligible_for_deletion]
    assert "old_job.json" in candidate_names
    assert "cached_model.bin" in candidate_names

    # Check that fresh file is NOT in candidates list
    assert "fresh.txt" not in [c.filename for c in summary.candidates]

    # Check that protected file is recognized as protected
    prot_candidate = next((c for c in summary.candidates if c.filename == "protected_voice.wav"), None)
    assert prot_candidate is not None
    assert prot_candidate.is_protected
    assert not prot_candidate.eligible_for_deletion

    # Recoverable bytes must be > 0
    assert summary.recoverable_bytes > 0


def test_cleaner_dry_run_and_execution(mock_storage):
    root = mock_storage["root"]
    rules = {
        "retention_policies": {
            "tmp_retention_hours": 24,
            "cache_retention_hours": 24,
        }
    }
    cleaner = StorageCleaner(rules=rules, workspace_root=root)
    inspection = cleaner.inspect_storage(protected_filepaths={str(mock_storage["protected_file"])})

    # 1. Dry run should NOT unlink any file
    dry_result = cleaner.execute_cleanup(
        inspection=inspection,
        dry_run=True,
    )
    assert dry_result["mode"] == "DRY_RUN"
    assert dry_result["deleted_files_count"] >= 2
    assert dry_result["recovered_bytes"] > 0
    # Files must still exist after dry run
    assert mock_storage["old_tmp"].exists()
    assert mock_storage["old_cache"].exists()

    # 2. Live execution should unlink eligible files
    live_result = cleaner.execute_cleanup(
        inspection=inspection,
        dry_run=False,
    )
    assert live_result["mode"] == "SAFE_DELETION"
    assert live_result["deleted_files_count"] >= 2
    assert live_result["recovered_bytes"] > 0

    assert not mock_storage["old_tmp"].exists()
    assert not mock_storage["old_cache"].exists()
    assert mock_storage["fresh_tmp"].exists()
    assert mock_storage["protected_file"].exists()
    assert mock_storage["db_file"].exists()


def test_cleanup_engine_registered_and_contract():
    engine = engine_registry.get("cleanup")
    assert engine is not None
    assert engine.id == "cleanup"
    assert engine.manifest.id == "cleanup"
    assert engine.manifest.name == "Cleanup Engine"

