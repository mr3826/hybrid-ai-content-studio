# Phase 17 Verification Audit — Final Creator Quality Gate

## 1. Executive Summary
Phase 17 implements the **Final Creator Quality Gate** (`quality_gate`), the non-negotiable human quality verification audit that must be passed before content can be exported or published. It synthesizes and inspects 9 independent quality dimensions across factual research, brand DNA, originality contribution, viewer hook strength, single-niche compliance, semantic repetition, commercial asset rights clearance, technical media QC, and production economics.

All studio invariants were strictly preserved:
- **Single Niche & Single Brand:** Evaluates alignment against the active niche profile and brand DNA singleton.
- **Engine Independence:** Decoupled contracts (`contracts.py`), rulebook (`rules.yaml`), manifest (`manifest.yaml`), deterministic evaluator (`evaluator.py`), and test harness.
- **Human Quality Gate Invariant:** Automated auto-posting is forbidden. Explicit human approval (`FINAL_APPROVED`) is required before export generation.
- **Actionable Correction Routing:** Provides immediate direct links to rectify issues (Script Studio, Scene Studio, Asset Rights Registry, Evidence Provenance, Media Studio).
- **Bilingual Interface:** Fully localized in both English and Bangla.
- **Zero CI/CD & Zero n8n:** Local-first architecture on SQLite WAL mode.

---

## 2. The 9 Creator Quality Dimensions

The engine evaluates and presents the following 9 dimensions separately on a 0–100 scale:

| Dimension | Scope & Verification Criteria | Blocking Threshold |
|---|---|---|
| **1. Evidence Quality** | Verified factual citations, primary/secondary sources count, linked empirical tests | < 60% or 0 verified facts |
| **2. Brand Fit** | Voice adherence, preferred vocabulary, zero banned clichés detection | Banned clichés detected in narration |
| **3. Originality** | "What are WE adding?" angle differentiation, quarantine check for generic summaries | Flagged as generic summary |
| **4. Viewer Value** | Hook type (bold claim, curiosity gap), word count density, clear takeaway | 0 words or empty script narration |
| **5. Niche Fit** | Active niche alignment, addresses primary problems, zero blocked keywords | Contains blocked niche keywords |
| **6. Repetition Intelligence** | Novelty index vs recently published content, semantic overlap check | Repetition collision index > 30% |
| **7. Asset Rights** | Commercial rights clearance, license classification, attribution obligations | Any scene asset is `BLOCKED` / `RESTRICTED` |
| **8. Technical Media QC** | 44.1kHz PCM speech audio standard, sub-second caption sync, FFmpeg assembly | Media synthesis/render status is `FAILED` |
| **9. Production Economics** | Amortized family cost, incremental compute, AI tokens, human review time | Informational ROI & investment monitor |

---

## 3. Actionable Correction Routing System
When warnings or blocking issues are detected, the system provides one-click navigation routes:
1. `return_to_script`: Deep links to `/script-studio/{itemId}` for narration/word count revisions.
2. `return_to_scene`: Deep links to `/scene-studio?itemId={itemId}` for storyboard restructuring.
3. `replace_asset`: Deep links to `/asset-rights` or `/scene-studio` to swap non-commercial media.
4. `fix_unsupported_claim`: Deep links to `/evidence` to attach citations or verify claims.
5. `rerender_segment`: Deep links to `/media-studio` to re-synthesize audio or re-render video.

---

## 4. Database Schema & Migration
- **Alembic Revision:** `5e6f7a8b9c0d` (`create_quality_gate_audits_table`)
- **Table Created:**
  - `quality_gate_audits`: Persists overall score, status (`PENDING`, `PASSED`, `WARNING`, `BLOCKED`, `FINAL_APPROVED`), 9 dimension JSON objects, actionable recommendations JSON, and human approval metadata (`is_approved`, `approved_by`, `approved_at`, `override_reason`).
- **Foreign Keys & Indices:**
  - FK to `content_items(id)` with cascade deletion.
  - FK to `scripts(id)` on set null.
  - Indexed on `content_item_id`, `script_id`, `status`.

---

## 5. API Endpoints
All endpoints are registered under `/api/v1/quality-gate`:

- `GET /api/v1/quality-gate/item/{item_id}`: Retrieves or computes the 9-dimension quality gate audit.
- `POST /api/v1/quality-gate/evaluate/{item_id}`: Forces fresh re-evaluation of all 9 dimensions.
- `POST /api/v1/quality-gate/approve/{item_id}`: Final human approval gate. Requires override reason if blocked, updates audit record, and transitions `ContentItem.status` and `ScriptDraft.status` to `FINAL_APPROVED`.
- `GET /api/v1/quality-gate/summary`: Summary metrics (total items, final approved count, pending review count, approval rate).

---

## 6. Frontend & UI Verification
- **Route:** `/quality-gate`
- **Navigation:** Added to sidebar with `CheckSquare` icon.
- **Bilingual Support:** Complete Bangla (`bn`) and English (`en`) dictionary keys under `qualityGatePage`.
- **Features:**
  - Content item selector with format and platform tags.
  - Overall Readiness Score gauge (0–100%) and dynamic status badge.
  - 9 individual dimension cards with scores, icons, summaries, metrics, and bullet observations.
  - Actionable correction routing bar with direct deep links.
  - Final Approval modal with override reason requirement for blocked items.
  - Direct "Proceed to Export" launcher once approved.

---

## 7. Verification Test Results
- **Engine Unit Tests:** `apps/api/tests/test_quality_gate_engine.py` (5/5 passed)
- **API Integration Tests:** `apps/api/tests/test_quality_gate_api.py` (1/1 passed)
- **Full Backend Suite:** 86/86 passed (`.\.venv\Scripts\pytest`)
- **Frontend Production Build:** `apps/web` compiled with 0 TypeScript errors (`npm run build`).
