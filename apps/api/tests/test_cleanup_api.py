import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cleanup_and_backup_api_full_flow(client: AsyncClient):
    # 1. Get reliability summary
    summary_res = await client.get("/api/v1/cleanup/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "storage_usage_bytes" in summary
    assert "database_size_bytes" in summary
    assert "active_policies" in summary

    # 2. Inspect storage
    inspect_res = await client.get("/api/v1/cleanup/inspect")
    assert inspect_res.status_code == 200
    inspection = inspect_res.json()
    assert "total_files_scanned" in inspection
    assert "candidates_count" in inspection
    assert "directories_scanned" in inspection
    assert isinstance(inspection["candidates"], list)

    # 3. Execute dry-run cleanup
    dry_res = await client.post(
        "/api/v1/cleanup/execute",
        json={"dry_run": True, "max_files_to_delete": 50},
    )
    assert dry_res.status_code == 200
    dry_report = dry_res.json()
    assert dry_report["mode"] == "DRY_RUN"
    assert dry_report["status"] == "SUCCESS"
    log_id = dry_report["id"]

    # 4. Fetch audit log by ID
    log_res = await client.get(f"/api/v1/cleanup/logs/{log_id}")
    assert log_res.status_code == 200
    assert log_res.json()["id"] == log_id

    # 5. List audit logs
    logs_list_res = await client.get("/api/v1/cleanup/logs")
    assert logs_list_res.status_code == 200
    logs = logs_list_res.json()
    assert len(logs) >= 1
    assert any(l["id"] == log_id for l in logs)

    # 6. Create studio backup snapshot
    backup_name = f"test_backup_{uuid.uuid4().hex[:6]}"
    backup_create_res = await client.post(
        "/api/v1/cleanup/backups",
        json={
            "backup_name": backup_name,
            "backup_type": "FULL",
            "notes": "API Integration Verification Backup",
        },
    )
    assert backup_create_res.status_code == 201
    backup_record = backup_create_res.json()
    backup_id = backup_record["id"]
    assert backup_record["status"] == "AVAILABLE"
    assert len(backup_record["checksum_sha256"]) == 64

    # 7. List backups
    backups_list_res = await client.get("/api/v1/cleanup/backups")
    assert backups_list_res.status_code == 200
    backups = backups_list_res.json()
    assert len(backups) >= 1
    assert any(b["id"] == backup_id for b in backups)

    # 8. Get backup by ID
    single_backup_res = await client.get(f"/api/v1/cleanup/backups/{backup_id}")
    assert single_backup_res.status_code == 200
    assert single_backup_res.json()["id"] == backup_id

    # 9. Verify backup integrity
    verify_res = await client.post(f"/api/v1/cleanup/backups/{backup_id}/verify")
    assert verify_res.status_code == 200
    verification = verify_res.json()
    assert verification["is_valid"] is True
    assert verification["calculated_checksum"] == backup_record["checksum_sha256"]

    # 10. Test sandbox restore
    restore_res = await client.post(
        f"/api/v1/cleanup/backups/{backup_id}/test-restore",
        json={"dry_run": True},
    )
    assert restore_res.status_code == 200
    restore_data = restore_res.json()
    assert restore_data["status"] == "SUCCESS"
    assert restore_data["integrity_check"] == "ok"
