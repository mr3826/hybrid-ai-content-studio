# Phase 15 Verification Audit — Evidence-First Scene + Asset Studio

## 1. Executive Summary
Phase 15 delivers the **Scene + Asset Studio** (`scene_studio`), transforming approved script sections into paced, visually structured storyboard scenes governed by an evidence-first visual priority hierarchy. It guarantees that empirical proof (screen recordings, benchmark charts, terminal execution) is prioritized over generic motion graphics and generated visual placeholders.

All studio invariants were strictly preserved:
- **Single Niche & Single Brand:** Operates on the active niche and brand profile context.
- **Engine Independence:** Decoupled contracts (`contracts.py`), rulebook (`rules.yaml`), manifest (`manifest.yaml`), deterministic offline adapters (`adapters.py`), and test harness.
- **100% Usable Offline & Without Paid Visual APIs:** Bundled with a local deterministic SVG generator producing branded technical visual cards with zero external API calls.
- **Bilingual Interface:** Fully localized in both English and Bangla.
- **Zero CI/CD & Zero n8n:** Pure local-first architecture on SQLite WAL mode.

---

## 2. 7-Level Visual Priority Hierarchy Implementation
The engine enforces the following hierarchy in both auto-decomposition and manual storyboard editing:

| Rank | Visual Priority Type | Description & Matching Criteria | Empirical? |
|:---:|:---|:---|:---:|
| **1** | `real_screen_recording` | Live UI demonstrations, interactive demos, hooks showing the working app | **Yes** |
| **2** | `benchmark_chart` | Empirical measurements, speed comparisons, test metrics, claim numbers | **Yes** |
| **3** | `code_terminal` | Terminal execution, CLI commands, bash scripts, configuration | **Yes** |
| **4** | `workflow_diagram` | Architecture diagrams, pipelines, system schematics | No |
| **5** | `product_screenshot` | Static UI captures, documentation, dashboard overviews | No |
| **6** | `original_motion_graphic` | Animated title cards, kinetic typography, CTA outros | No |
| **7** | `generated_visual` | Fallback visual placeholder when no empirical asset is yet available | No |

---

## 3. Database Schema & Migration
- **Alembic Revision:** `3c4d5e6f7a8b` (`create_scenes_and_media_assets_tables`)
- **Tables Created:**
  - `scenes`: Storyboard units linking script sections, sequence order, narration, timing, visual type, evidence reference, and rights record.
  - `media_assets`: Local media asset catalog storing file path, file size, mime type, visual priority rank, tags, and rights record reference.
- **Foreign Keys & Indices:**
  - Foreign key to `scripts(id)` with cascade deletion.
  - Foreign key to `script_sections(id)` on set null.
  - Foreign key to `asset_rights_records(id)` on set null.
  - Indexed on `script_id`, `scene_order`, `visual_type`, `status`.

---

## 4. API Endpoints
All endpoints are registered under `/api/v1/scenes`:

- `GET /api/v1/scenes/script/{script_id}`: List all scenes in sequence order for a script.
- `POST /api/v1/scenes/decompose/{script_id}`: Auto-decompose script sections into storyboard scenes.
- `POST /api/v1/scenes`: Create a manual scene.
- `POST /api/v1/scenes/assets`: Register a media asset (JSON / base64 / path reference).
- `GET /api/v1/scenes/assets`: List and filter media assets by type or query.
- `GET /api/v1/scenes/{scene_id}`: Fetch single scene details with asset rights summary.
- `PUT /api/v1/scenes/{scene_id}`: Update narration, timing, visual type, or asset attachment.
- `DELETE /api/v1/scenes/{scene_id}`: Remove scene from storyboard.
- `POST /api/v1/scenes/reorder/{script_id}`: Reorder scenes in batch.
- `POST /api/v1/scenes/validate-storyboard/{script_id}`: Quality gate checking pacing, duration, empirical ratio, and rights clearance.
- `POST /api/v1/scenes/generate-placeholder/{scene_id}`: Generate offline dark-mode SVG visual card.

---

## 5. Frontend & UI Verification
- **Route:** `/scene-studio` (with navigation item in `Navigation.tsx`)
- **Features:**
  - Script selector linking to approved content items.
  - One-click Auto-Decompose button.
  - Quality verification metric strip (total duration vs target, empirical visual ratio %, storyboard gate status).
  - Sequence list view and visual grid cards view with interactive reordering (up/down).
  - Local media asset catalog drawer and local file / base64 asset registration modal.
  - Inline placeholder SVG generator.
  - Manual scene creation and edit modal.
  - Full bilingual support (Bangla & English).

---

## 6. Automated Test Results
- **Engine Tests:** `apps/api/tests/test_scene_studio.py` (5/5 passed)
- **API Tests:** `apps/api/tests/test_scene_studio_api.py` (1/1 passed)
- **Full Backend Suite:** 74/74 passed across all 15 phases.
- **Frontend Build:** Clean compilation without TypeScript errors.
