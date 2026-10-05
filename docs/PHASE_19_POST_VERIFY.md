# Phase 19: Human-Approved Feedback Engine — Verification & Signoff

## Executive Summary
Phase 19 delivers the **Human-Approved Feedback Engine**, implementing a creator-guided closed feedback loop that analyzes real-world publication performance signals (from Phase 18 snapshots) and synthesizes actionable editorial, hook pacing, and brand memory adjustments. In accordance with studio non-negotiable invariants, unvetted automated self-modification is strictly forbidden: all proposed rule and memory alterations generate `PENDING` lesson cards requiring explicit creator review, approval, and application before altering Brand DNA.

---

## 1. Engine Architecture & Decoupled Standard
The Feedback Engine is located in `apps/api/app/engines/feedback/`:
- **`manifest.yaml`**: Engine ID `feedback`, version `1.0.0`, dependencies: `analytics`, `brand`. Declares `dry_run`, `explain`, and `health_check` capabilities.
- **`rules.yaml`**: Version `1.0.0`, defines:
  - Critical hook drop threshold: `< 45.0%` (triggers hook optimization or banned phrase detection)
  - Viral hook threshold: `>= 75.0%` (triggers exemplar promotion into Brand Exemplars)
  - Critical engagement threshold: `< 2.0%` (triggers CTA refinement)
  - Strong engagement threshold: `>= 8.0%` (triggers topic reinforcement in Brand Memory)
  - `auto_apply: false` (non-negotiable studio invariant; automated self-modification is blocked)
- **`contracts.py`**: Typed Pydantic schemas:
  - `LessonType`, `ImpactLevel`, `LessonStatus`, `ProposedAdjustment`
  - `FeedbackLessonCreateRequest`, `FeedbackLessonResponse`, `FeedbackActionRequest`
  - `FeedbackSummaryResponse`, `FeedbackEvaluateRequest`, `FeedbackEvaluateResponse`, `FeedbackExplainResponse`
- **`synthesizer.py`**: `FeedbackSynthesizer` evaluating snapshot volume, retention, and engagement against thresholds, matching opening hook narration against opening clichés, and constructing concrete `ProposedAdjustment` payloads.
- **`engine.py`**: `FeedbackEngine` inheriting from `BaseEngine`, implementing `validate_config()`, `health()`, `run()`, `dry_run()`, and `explain()`.
- **Engine Catalog**: Registered in `apps/api/app/engines/catalog.py` and active in the central `engine_registry`.

---

## 2. Database Model & Migration
- **Model**: `FeedbackLesson` in `apps/api/app/models/feedback.py`:
  - `id`: String(36) UUID
  - `content_item_id`: ForeignKey(`content_items.id`, ondelete="SET NULL", nullable=True)
  - `lesson_type`: String(64) (`hook_optimization`, `pacing_adjustment`, `banned_phrase_addition`, `preferred_vocabulary_addition`, `format_recommendation`, `topic_reinforcement`, `angle_guidance`, `cta_refinement`)
  - `title`: String(255)
  - `observation`: Text
  - `impact_level`: String(32) (`HIGH`, `MEDIUM`, `LOW`)
  - `confidence_score`: Float
  - `evidence_data`: JSON
  - `proposed_adjustment`: JSON (`target`, `field`, `action`, `value`, `summary`)
  - `status`: String(32) (`PENDING`, `APPROVED`, `REJECTED`, `APPLIED`)
  - `creator_notes`: Text (nullable)
  - `reviewed_at`, `applied_at`: DateTime(timezone=True)
  - Relationship to `ContentItem`
- **Alembic Migration**: `2026_10_05_1300-7a8b9c0d1e2f_create_feedback_lessons_table.py`
  - Revision `7a8b9c0d1e2f` applied and verified with reversible downgrade and re-upgrade.

---

## 3. Storage Repository Boundary
- **Repository**: `FeedbackRepository` in `apps/api/app/repositories/feedback_repository.py`:
  - Inherits from `BaseRepository[FeedbackLesson]`.
  - Operations:
    - `create_lesson(data)`
    - `get_lesson(lesson_id)`
    - `list_lessons(status, lesson_type, limit, offset)`
    - `approve_lesson(lesson_id, creator_notes)`: Human approval gate.
    - `reject_lesson(lesson_id, creator_notes)`: Human rejection gate.
    - `apply_lesson(lesson_id)`: Applies approved adjustments directly to `BrandProfile` (e.g. appends to `avoid_vocabulary` or `banned_cliches`, or updates `cta_style`) or creates new `BrandMemoryItem` / `BrandExemplar` records.
    - `get_feedback_summary()`: Aggregated counts and breakdowns.
  - Exported in `apps/api/app/repositories/__init__.py`.

---

## 4. REST API Endpoints
All endpoints mounted at `/api/v1/feedback` in `apps/api/app/api/v1/feedback.py`:
- `GET /api/v1/feedback/summary`: High-level closed loop KPI summary.
- `GET /api/v1/feedback/lessons`: List lessons with status and type filters.
- `GET /api/v1/feedback/lessons/{id}`: Detailed view of single lesson.
- `POST /api/v1/feedback/lessons`: Manually log creator lesson / observation.
- `POST /api/v1/feedback/lessons/{id}/approve`: Creator approves a proposal.
- `POST /api/v1/feedback/lessons/{id}/reject`: Creator rejects a proposal.
- `POST /api/v1/feedback/lessons/{id}/apply`: Apply approved lesson to Brand DNA.
- `POST /api/v1/feedback/evaluate`: Evaluates publication snapshots and synthesizes candidate lessons.
- `GET /api/v1/feedback/explain/{id}`: Transparent algorithmic explanation and human gate requirement.

---

## 5. Web Studio & Bilingual Localization
- **UI Route**: `/feedback` (`apps/web/app/feedback/page.tsx`):
  - Executive KPIs: Pending Review, Approved, Applied to Brand DNA, Rejected.
  - Interactive Filter Tabs: All, Pending, Approved, Applied, Rejected.
  - "Evaluate Performance" button with live animation.
  - "Add Manual Lesson" modal for creator-initiated insights.
  - Lesson cards displaying observation text, metrics evidence pills, proposed adjustment diff viewer (target, field, value), and creator decision controls.
  - Algorithmic explanation modal with human quality gate confirmation.
- **Navigation**: Added to `NAV_CONFIG` with `Lightbulb` icon in `apps/web/components/Navigation.tsx`.
- **Localization**: Full English (`en`) and Bangla (`bn`) translations in `apps/web/lib/translations.ts`.
- **API Client**: Added typed helpers in `apps/web/lib/api.ts`.

---

## 6. Verification Results
1. **Engine & Synthesizer Tests**: `apps/api/tests/test_feedback_engine.py` (8/8 passed).
2. **API Lifecycle Test**: `apps/api/tests/test_feedback_api.py` (passed).
3. **Repository Boundaries**: `apps/api/tests/test_repositories.py` (passed).
4. **Full Test Suite**: **103/103 tests passing** via pytest in 49.9s.
5. **Web Build**: **22/22 static pages** compiled successfully in Next.js 15 (`npm run build`).
