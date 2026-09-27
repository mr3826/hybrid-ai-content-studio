# Phase 1–3 Comprehensive Retrofit Audit
**Fresh Local AI Content Studio (`hybrid-ai-content-studio`)**  
**Date:** September 27, 2026  
**Auditor:** Antigravity (Jeff Allan Claude Skills Full-Stack Skillset)  

---

## 1. Executive Baseline & Repository State

| Metric | Current State |
|---|---|
| **Current Commit SHA** | `6dacb84..6aa2b82` (`6aa2b8276abe6597cfadfd5e6a9300f325a3a9aa`) |
| **Active Branch** | `master` (synchronized with `origin/master`) |
| **Working Tree** | Clean (untracked specification file `POST_PHASE_3_MASTER_EXECUTION_PROMPT.md`) |
| **Database Migrations** | 2 Alembic revisions applied; current head: `c4635f03662e` |
| **Test Baseline** | 39 pytest tests passing in 1.36s (backend, engines, worker) |
| **Frontend Build** | Next.js 15.5.26 production build passing (8/8 routes static) |
| **Zero Secrets** | Verified (no API keys, no tokens in repository or history) |
| **No CI/CD / No n8n** | Verified (local verification only, no workflow pipelines) |

---

## 2. Phase 1–3 Feature Inventory

### Phase 1: Single Brand / Niche Foundation
* **Niche Model (`NicheProfile`)**: Singleton entity (`id="primary"`). Stores `name`, `one_sentence_definition`, `audience`, `audience_regions`, `primary_problems`, `allowed_topics`, `adjacent_topics`, `blocked_topics`, `must_have_signals`, `negative_keywords`, `preferred_source_types`, `content_pillars`, `commercial_intent_topics`, `evergreen_topics`.
* **Brand Model (`BrandProfile`)**: Singleton entity (`id="primary"`). Stores `brand_name`, `brand_promise`, `audience`, `tone`, `voice_rules`, `preferred_vocabulary`, `avoid_vocabulary`, `banned_cliches`, `claim_rules`, `cta_style`, `humor_policy`, `controversy_policy`, `sponsor_policy`, `affiliate_disclosure_style`, `visual_identity`, `platform_adaptations`.
* **Brand Exemplar Model (`BrandExemplar`)**: Stores approved hooks, scripts, captions, do/don't examples with category, title, content, context note, platform.
* **Platform Model (`PlatformSetting`)**: Stores external browser launch URLs for YouTube, Facebook, Instagram, TikTok with strict HTTPS validation.
* **UI**: `/settings` with 5 configuration tabs (Niche, Brand, Exemplars, Platforms, Transfer). First-run setup gates active on Dashboard.

### Phase 2: Modular Engine Framework
* **Core Base Class (`BaseEngine`)**: Abstract contract defining `validate_config()`, `health()`, `run()`, `dry_run()`, and `explain()`. Loads `manifest.yaml` and `rules.yaml`.
* **Engine Registry (`engine_registry`)**: Central singleton registering engines, validating declared dependencies before execution, and recording audit records to SQLite WAL.
* **Audit Model (`EngineRunRecord`)**: Persists run ID, duration, input/output/rejected/error counts, cost, summary, parameters, and explainability factors.
* **Catalog Registration**: 13 studio catalog engines registered alongside canonical `ReferenceEngine`.
* **UI**: `/engines` dashboard with status badges, dependency lists, run/dry-run triggers, rule editor modal, and execution logs drawer.

### Phase 3: Niche Guard + Brand Engines
* **Niche Guard Engine (`niche_guard`)**: Deterministic taxonomy scoring without LLMs. Flags instant hard block on blocked topics (`score = 0.0`), matches content pillars, allowed topics, adjacent topics, must-have signals, and negative keyword penalties (`-25.0` per word).
* **Brand Engine (`brand`)**: Audits draft copy against brand DNA. Detects banned clichés (*"In today's fast-paced world..."*, *"Without further ado..."*, *"Let's dive right in!"*), blacklisted vocabulary (*"game-changer"*, *"mind-blowing"*, *"insane"*), tone calmness (exclamation point density, ALL-CAPS words), and flags unsupported empirical claims. Cross-references approved exemplars.
* **API Endpoints**: `POST /api/v1/niche-guard/evaluate` and `POST /api/v1/brand-qa/evaluate`.
* **Interactive UI**: `EngineTesterModal` integrated into `/engines` with sample presets and real-time visual score gauges.

---

## 3. Architecture Mismatches & Gap Analysis

Through the lens of the **Post-Phase-3 Master Architecture (Evidence-Driven AI Creator Studio)**, several structural and functional gaps must be retrofitted before proceeding to Phase 4 (RSS Engine):

### Gap 1: Brand Memory is Missing (Phase 1 Retrofit)
* **Current State**: We have static `BrandExemplar` records, but no dynamic **Brand Memory** tracking recent approved hooks, recent CTAs, recent topics, recent products/models tested, recent conclusions, recent visual patterns, frequently used phrases, and thumbnail wording.
* **Impact**: Without Brand Memory, the studio cannot detect repetition over time or maintain "same identity, different execution" across weekly content cycles.

### Gap 2: Monetization Metadata Incomplete (Phase 1 Retrofit)
* **Current State**: `affiliate_disclosure_style` and `sponsor_policy` exist on `BrandProfile`, but `default_lead_magnet`, `newsletter_cta`, and `digital_product_cta` are absent.
* **Impact**: Downstream Content and Publishing engines cannot automatically embed creator monetization assets.

### Gap 3: Local Job System Missing (Phase 2 Retrofit)
* **Current State**: `worker/worker.py` runs a heartbeat loop, but there is no database-backed job queue model (`JobRecord` / `StudioJob`).
* **Impact**: Long-running background operations (heavy scraping, FFmpeg, TTS, batch runs) cannot be dispatched asynchronously or safely retried with status tracking.

### Gap 4: Repository Interfaces Missing (Phase 2 Retrofit)
* **Current State**: Services access SQLAlchemy sessions directly.
* **Impact**: No formal domain repository abstraction (`OpportunityRepository`, `ResearchRepository`, `EvidenceRepository`, `ProjectRepository`, `ContentRepository`, `AnalyticsRepository`, `AssetRepository`).

### Gap 5: Engine Run Versioning & Project Context (Phase 2 Retrofit)
* **Current State**: `EngineRunRecord` stores `engine_version` and parameters, but lacks explicit columns for `rules_version` and `project_id`. Also, `BaseEngine` does not have a formal `rules_version` property or change audit tracking.

### Gap 6: Repetition & Multi-Dimensional Intelligence (Phase 3 Retrofit)
* **Current State**: `BrandEngine` evaluates clichés, avoid words, and simple exclamation count, but does not query historical Brand Memory to warn on:
  - same hook pattern too often
  - same topic covered too recently
  - same CTA repeatedly
  - same conclusion repeatedly
* **Impact**: Content risks sounding formulaic across weeks.
* **Current State**: `BrandEngine` outputs 5 sub-scores, but the master spec requires 6 clear dimensions:
  1. `Tone`
  2. `Vocabulary`
  3. `Repetition`
  4. `Audience Fit`
  5. `CTA Fit`
  6. `Platform Fit`
* **Current State**: `NicheGuardVerdict` should explicitly expose the primary identified content pillar and audience relevance score.

---

## 4. KEEP / MODIFY / REMOVE / ADD Matrix

| Component | Classification | Detailed Rationale & Action |
|---|---|---|
| `NicheProfile` (Model & Schemas) | **MODIFY** | **KEEP** all current fields; **MODIFY** content pillar schema to guarantee structured `{id, name, description, keywords, priority}` dicts; verify all fields are editable in UI. |
| `BrandProfile` (Model & Schemas) | **MODIFY** | **ADD** monetization metadata fields: `default_lead_magnet`, `newsletter_cta`, `digital_product_cta`. Keep existing voice, tone, visual identity. |
| `BrandExemplar` (Model) | **KEEP** | Preserves historical manual exemplars (approved hooks, scripts, captions, do/don't examples). |
| `BrandMemoryItem` (New Model) | **ADD** | New table `brand_memory` storing dynamic creator memory: memory type (hook, cta, topic, product_tested, conclusion, visual_pattern, frequent_phrase, thumbnail_wording), content, usage count, last used timestamp. |
| `PlatformSetting` (Model & UI) | **KEEP** | Strict HTTPS validation and one-click browser launch links are working as designed. |
| `BaseEngine` (`core/base.py`) | **MODIFY** | **ADD** `rules_version` property and ensure `EngineManifest` and execution context properly track version metadata. Avoid adding any generic DSL or runtime plugin marketplace. |
| `EngineRegistry` (`core/registry.py`) | **MODIFY** | **KEEP** registration, dependency validation, and audit dispatch; update `execute_engine` to pass `rules_version` and optional `project_id` to `EngineRunRecord`. |
| `EngineRunRecord` (Model) | **MODIFY** | **ADD** `rules_version` (String) and `project_id` (String, nullable) columns with an Alembic migration. |
| `StudioJob` / `JobRecord` (New Model) | **ADD** | Database-backed local job queue table in SQLite WAL: `id`, `job_type`, `engine_id`, `project_id`, `payload`, `status` (`pending`, `running`, `completed`, `failed`, `cancelled`), `attempts`, `created_at`, `started_at`, `finished_at`, `error`. |
| `StudioWorker` (`worker/worker.py`) | **MODIFY** | Wire polling loop to claim `pending` jobs from `StudioJob`, execute them, update status, and handle errors. |
| Storage Repositories (`app/repositories/`) | **ADD** | Clean repository interfaces and initial SQLite implementations: `OpportunityRepository`, `ResearchRepository`, `EvidenceRepository`, `ProjectRepository`, `ContentRepository`, `AnalyticsRepository`, `AssetRepository`. |
| `NicheGuardEngine` | **MODIFY** | Ensure output verdict includes primary matched `pillar`, `audience_relevance`, and explicit factor breakdown. |
| `BrandEngine` | **MODIFY** | Connect to `brand_memory` table; add repetition detection (hook frequency, topic recency, CTA reuse); compute the 6 standard dimensions (`Tone`, `Vocabulary`, `Repetition`, `Audience Fit`, `CTA Fit`, `Platform Fit`); provide intelligent warnings instead of hard-blocking all repetition. |
| Engine UI (`/engines`) | **MODIFY** | Keep existing cards, rules editor, logs, and tester modal; update tester to show the 6 Brand QA dimensions. |
| Settings UI (`/settings`) | **MODIFY** | Add Monetization CTA tab or section (lead magnet, newsletter, digital product) and Brand Memory viewer. |
| CI/CD & GitHub Actions | **REMOVE / FORBID** | Invariant enforced: No `.github/workflows` or remote deployment pipelines. |
| n8n / External Webhooks | **REMOVE / FORBID** | Invariant enforced: Pure local Python and Next.js. |

---

## 5. Retrofit Execution Plan (Safe, Phased Sequence)

To preserve working code, database integrity, and 100% test pass rates, the retrofit will be executed in three sequential atomic sub-phases, followed by the Retrofit Verification Gate:

```
Step 1: Audit Report Approval (docs/PHASE_1_3_RETROFIT_AUDIT.md) — CURRENT STEP
   │
   ▼
Step 2: Phase 1 Retrofit — Single Niche + Stronger Brand Foundation
   ├─ Models: BrandMemoryItem, BrandProfile monetization fields
   ├─ Alembic Migration: add brand_memory and monetization columns
   ├─ Services & Schemas: brand_memory_service, updated BrandProfileRead/Update
   ├─ UI: Add Monetization settings and Brand Memory view to /settings
   ├─ Tests: test_brand_memory.py, updated test_brand.py, test_niche.py
   └─ Commit: refactor: strengthen single-brand niche foundation
   │
   ▼
Step 3: Phase 2 Retrofit — Lightweight Engine Architecture
   ├─ Models: StudioJob (database-backed queue), rules_version/project_id on EngineRunRecord
   ├─ Alembic Migration: create jobs table and update engine_runs
   ├─ Engine Core: BaseEngine.rules_version, audit dispatching
   ├─ Repositories: app/repositories/ with clean storage boundaries
   ├─ Worker: worker/worker.py job polling and execution handler
   ├─ Tests: test_jobs.py, test_repositories.py, test_worker.py
   └─ Commit: refactor: harden lightweight engine architecture
   │
   ▼
Step 4: Phase 3 Retrofit — Niche Guard + Brand Intelligence
   ├─ Niche Guard: primary pillar extraction and audience relevance scoring
   ├─ Brand Engine: integrate Brand Memory lookup, repetition warnings, 6 QA dimensions
   ├─ UI: Update EngineTesterModal with 6 QA dimensions and repetition indicators
   ├─ Tests: test_brand_memory_repetition.py, updated test_niche_guard_and_brand.py
   └─ Commit: refactor: add persistent brand memory and repetition intelligence
   │
   ▼
Step 5: Retrofit Verification Gate
   ├─ Run full backend test suite (target: 50+ tests passing)
   ├─ Run Next.js production build validation
   ├─ Run Playwright / browser verification
   ├─ Generate docs/PHASE_1_3_RETROFIT_REPORT.md
   └─ Proceed to Phase 4 (RSS Discovery Engine)
```

---

## 6. Safe Parallel Execution Analysis

Per **Section 28 & 29** of the Master Prompt:
* **The initial audit is strictly sequential** (completed in this document).
* **Phase 1 Retrofit and Phase 2 Retrofit** touch distinct schema areas:
  * Phase 1 touches `brand_profiles` and creates `brand_memory`.
  * Phase 2 touches `engine_runs` and creates `studio_jobs`.
  * However, to ensure deterministic Alembic migration order without branching migration heads (`alembic merge`), we execute Step 2 (Phase 1 Retrofit migration) then Step 3 (Phase 2 Retrofit migration) in clean serial commits, or single coordinated migration steps.
* **Phase 3 Retrofit MUST be sequential** after Steps 2 and 3 because the repetition intelligence directly queries the `brand_memory` model introduced in Step 2.

---

## 7. Audit Conclusion & Readiness

The current implementation (Phase 0–3) provides a solid, working, regression-free foundation (39/39 tests passing, clean Next.js 15 build). The gaps identified above are architectural enhancements that align the system with the long-term vision of an **Evidence-Driven AI Creator Studio**.

We are now ready to execute **Phase 1 Retrofit**.
