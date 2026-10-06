# Phase 21 Post-Verification Report — Cleanup, Backup & Reliability

## 1. Overview & Architectural Goals
Phase 21 implements the **13th Engine** of the Fresh Local AI Content Studio: the **Cleanup & Reliability Engine** (`id: cleanup`, category: `maintenance`), along with the studio-wide local backup and disaster recovery subsystem.

### Non-Negotiable Invariants Enforced
1. **Reference-Safe Cleanup Invariant**: Prior to any file unlinking, the engine queries SQLite relational models (`MediaAsset.file_path`, `ExportPackage.archive_path`, `MediaPackage` video/audio/subtitles/timelines, `AssetRightsRecord.uri`). No file that is actively referenced by a studio entity or project draft can ever be deleted.
2. **Absolute Invariant Protections**: SQLite database files (`studio.sqlite`, `-wal`, `-shm`, `-journal`) and research/evidence citations can never be deleted regardless of age.
3. **Tiered Retention Policies**:
   - `tmp`: 24 hours
   - `cache`: 24 hours
   - `failed_render_temp` (`runtime/`): 3 days (72 hours)
   - `unused_generated_asset`: 7 days
   - `final_media`: 30 days after publish
   - `exports`: 30 days
   - `metadata/evidence`: permanent retention
4. **Cryptographic Integrity & Audit Logging**:
   - Every cleanup inspection and execution creates an immutable `CleanupAuditLog` record with run ID, mode (`DRY_RUN` vs `SAFE_DELETION`), candidate counts, recoverable bytes, and detailed file manifest.
   - Every backup creates a `StudioBackupRecord` with a cryptographic SHA-256 checksum and a structured `manifest.json`.
   - Sandbox restore tests extract archives to an isolated sandbox and perform an automated `PRAGMA integrity_check;` on the restored SQLite database to guarantee corruption-free backups.
5. **No n8n / Zero Remote Dependencies / Single Niche & Single Brand**:
   - Backup manager packages singleton `NicheProfile` and `BrandProfile` configurations into `manifest.json` along with platform configurations.
   - All operations execute 100% locally on SQLite.

---

## 2. Database Schema & Migration
- **Alembic Migration**: `2026_10_06_0700-9c0d1e2f3a4b_create_cleanup_and_backup_tables.py`
- **Tables Created**:
  1. `cleanup_audit_logs`:
     - `id`, `run_id`, `mode`, `scanned_files_count`, `candidate_files_count`, `deleted_files_count`, `recovered_bytes`, `rules_applied` (JSON), `details` (JSON), `status`, `error_message`, `created_at`, `updated_at`.
  2. `studio_backups`:
     - `id`, `backup_name`, `filepath`, `backup_type`, `size_bytes`, `checksum_sha256`, `metadata_snapshot` (JSON), `status`, `notes`, `created_at`, `updated_at`.

---

## 3. Engine Implementation (`apps/api/app/engines/cleanup/`)
- `manifest.yaml`: Registered in engine catalog under id `cleanup`, version `1.0.0`, category `maintenance`.
- `rules.yaml`: Tiered retention policies, absolute invariant protections, and execution thresholds.
- `contracts.py`: Pydantic schemas (`FileCandidateInfo`, `StorageInspectionSummary`, `CleanupExecuteRequest`, `CleanupReport`, `BackupCreateRequest`, `StudioBackupResponse`, `BackupVerifyResponse`, `ReliabilitySummaryResponse`).
- `cleaner.py`: `StorageCleaner` class handling storage inspection, age thresholds, recoverable bytes estimation, reference checks against active database entities, and dry-run vs safe deletion unlinking.
- `backup_manager.py`: `BackupManager` class for creating verified ZIP archives (`manifest.json` + `studio.sqlite`), SHA-256 hashing, archive verification, and sandbox test-restore with SQLite PRAGMA integrity check.
- `engine.py`: `CleanupEngine` subclassing `BaseEngine`.
- `catalog.py`: Registered in `engine_registry`.

---

## 4. REST API Endpoints (`/api/v1/cleanup`)
- `GET /api/v1/cleanup/summary`: Returns storage usage, DB size, recoverable bytes, and backup/audit counts.
- `GET /api/v1/cleanup/inspect` & `POST /api/v1/cleanup/inspect`: Returns candidate files and recoverable bytes.
- `POST /api/v1/cleanup/execute`: Runs dry-run simulation or live deletion, writing audit records.
- `GET /api/v1/cleanup/logs`: Lists cryptographic cleanup audit records.
- `GET /api/v1/cleanup/logs/{id}`: Returns specific cleanup run details.
- `POST /api/v1/cleanup/backups`: Creates a new verified ZIP backup archive.
- `GET /api/v1/cleanup/backups`: Lists existing backups.
- `GET /api/v1/cleanup/backups/{id}`: Returns single backup details.
- `POST /api/v1/cleanup/backups/{id}/verify`: Audits SHA-256 checksum and zip integrity.
- `POST /api/v1/cleanup/backups/{id}/test-restore`: Extracts backup to isolated sandbox and runs SQLite PRAGMA integrity check.

---

## 5. Web Studio & Bilingual UI (`apps/web/app/cleanup/page.tsx`)
- **Storage KPIs**: Real-time display of storage tracked, SQLite DB size, recoverable space, protected files, and backup archives.
- **Interactive Tabs**:
  1. `Storage & Cleanup`: Target directory toggles (`tmp`, `cache`, `runtime`, `exports`), candidate files table with protection badges, "Simulate (Dry-Run)" button, and "Execute Safe Deletion" with confirmation modal.
  2. `Backups & Recovery`: Backup archive table, SHA-256 checksum with one-click copy, "Verify SHA-256" button, and "Sandbox Test-Restore" report modal.
  3. `Protection Policies & Invariants`: Explanations of tiered retention thresholds and strict non-negotiable invariants.
  4. `Audit History`: Tabular audit log of past cleanup runs.
- **Bilingual Support**: Full translations in English and Bengali (`translations.ts`).
- **Sidebar Integration**: Added `/cleanup` route with `HardDrive` icon in `Navigation.tsx`.

---

## 6. Verification Results
1. **Pytest Test Suite**:
   - `test_cleanup_engine.py`: 3/3 passed (inspection, dry-run vs execution, manifest contract).
   - `test_backup_restore.py`: 2/2 passed (backup creation, SHA-256 verification, sandbox restore with PRAGMA integrity check).
   - `test_cleanup_api.py`: 1/1 passed (end-to-end full flow across all REST endpoints).
   - **Total Test Suite**: 114/114 passed (0 failures).
2. **Next.js Web Build**:
   - `npm run build` compiled cleanly in 33.9s.
   - All 24 static routes generated with zero TypeScript or linting errors.
