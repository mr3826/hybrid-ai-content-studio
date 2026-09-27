# Content Family Engine (Phase 11)

## 1. Purpose & Core Philosophy
In traditional content production workflows, the paradigm is often `Project = One Piece of Content`. When applying original empirical research, proprietary benchmarks, and real-world experiments to content production, that paradigm creates poor economics: spending $50 to $200 and hours of lab time to generate a single 60-second video or one static tweet is financially unsustainable.

The **Content Family Engine** replaces that paradigm with:
$$\text{Content Family} = \text{One Research / Evidence / Originality Investment}$$

A single Content Family amortizes the primary investment across multiple format- and platform-tailored child items:
- **Long-form Deep Dive (YouTube)**: Complete methodology, deep analysis, failure edge-cases, comprehensive benchmark tables.
- **Accuracy Short (YouTube Shorts / Reels)**: 45-second high-energy focus on the key accuracy victor.
- **Cost Short (TikTok / Reels)**: Focused ROI comparison, cost per million tokens, token throughput.
- **Surprising Failure Short**: Dramatic hook showcasing the most extreme edge-case failure mode.
- **Social Companion Post (X / LinkedIn / Facebook)**: High-density carousel breakdown, structured takeaways, community discussion prompt.
- **Technical Newsletter / Article**: Long-form editorial draft, archival documentation, reproducible setup code.

**Key Invariant**: Children do **not** duplicate identical content across platforms. Each child item is independently editable, adapted to its medium's hook dynamics and audience expectations, yet strictly anchored to the shared verified factual foundation.

---

## 2. Domain Model Architecture

```
Opportunity (Approved)
       │
       ▼
Research Packet (Verified Facts)
       │
       ▼
Evidence Graph (Primary Sources & Claims)
       │
       ▼
Originality Plan & Experiment (Novel Data & Measurements)
       │
       ▼
Content Family (Parent Economics & Strategy)
  ├── ContentItem (YouTube Long)      ── references claims [C1, C2, C3, C4]
  ├── ContentItem (Accuracy Short)    ── references claim  [C1]
  ├── ContentItem (Cost Short)        ── references claim  [C2]
  ├── ContentItem (Failure Short)     ── references claim  [C4]
  └── ContentItem (Social Post)       ── references claims [C1, C2]
```

### ContentFamily (Parent)
Represents the strategic umbrella and economic ledger for the content cluster:
- `id` (`UUID` / `cf_...`): Primary identifier.
- `title`: Working strategic title (e.g., "Gemini vs Qwen Invoice Processing Benchmark").
- `slug`: URL-friendly identifier.
- `topic_id`: Reference to the originating `Opportunity`.
- `research_packet_id`: Reference to the verified `ResearchPacket`.
- `originality_plan_id`: Reference to the approved `OriginalityPlan`.
- `primary_experiment_id`: Reference to the empirical `Experiment` or execution harness.
- `status`: Lifecycle state (`DRAFT`, `READY_FOR_CONTENT`, `ACTIVE`, `COMPLETED`, `ARCHIVED`).
- `content_pillar`: Strategic editorial pillar (e.g., `Hardware Benchmarks`, `Local AI Models`, `Cost Optimization`).
- `original_value_type`: Category of original contribution (e.g., `benchmark`, `failure_analysis`, `cost_comparison`).
- `summary`: High-level thesis and angle description.
- **Economics Ledger**:
  - `research_cost`: Direct research acquisition cost ($).
  - `experiment_cost`: Cloud tokens, compute instances, testing subscriptions ($).
  - `ai_cost`: LLM API calls spent during synthesis ($).
  - `media_cost`: Stock assets, voice clones, external licensing ($).
  - `manual_time_minutes`: Creator labor hours spent on the parent research.
  - `local_compute_seconds`: Local GPU/CPU runtime spent running benchmarks or models.

### ContentItem (Child)
Represents an individual, format-tailored publishing deliverable:
- `id` (`UUID` / `ci_...`): Primary identifier.
- `content_family_id`: Foreign key reference to parent `ContentFamily`.
- `format`: Format enum (`short_vertical`, `youtube_long`, `social_post`, `newsletter`, `article`).
- `platform_target`: Primary target network (`youtube`, `facebook`, `instagram`, `tiktok`, `cross_platform`, `none`).
- `working_title`: Child-specific hook title.
- `angle`: Unique storytelling focus (e.g., "The $0.001 vs $0.05 cost divergence").
- `hook_type`: Emotional / cognitive angle (`curiosity_gap`, `bold_contrarian`, `problem_agitation`, `data_revelation`, `story_loop`).
- `original_value_connection`: Explicit statement describing how this child communicates the family's novel value.
- `viewer_value`: Tangible utility promised to the viewer.
- `status`: Child lifecycle state (`PLANNED`, `DRAFT`, `SCRIPT_REVIEW`, `SCRIPT_APPROVED`, `READY_FOR_EXPORT`, `EXPORTED`, `READY_TO_PUBLISH`, `PUBLISHED`, `REJECTED`).
  - *Invariant*: In Phase 11, children **cannot** transition to `SCRIPT_APPROVED` (this gate is strictly reserved for Phase 12 Script Studio).
- **Incremental Economics**:
  - `incremental_cost`: Platform-specific costs (custom thumbnail design, licensed clip, target voice).
  - `manual_time_minutes`: Creator time spent editing this specific child.
  - `local_compute_seconds`: Local rendering or export time.

### ContentItemEvidenceSelection (Reference Bridge)
Enforces evidence inheritance without data duplication:
- `content_item_id`: Reference to the child `ContentItem`.
- `claim_id`: Reference to the parent's `Claim` in the Evidence Graph.
- `relevance_note`: Context on how this claim is deployed in this specific format.
- `is_primary`: Boolean indicating whether this claim represents the central hook of the child item.

---

## 3. Evidence & Originality Inheritance

### Evidence Inheritance
- Claims are never cloned or duplicated into child records.
- The parent family links to `ResearchPacket` and `EvidenceGraph`.
- Children query available parent claims and register references through `ContentItemEvidenceSelection`.
- Any update or correction to a factual claim in the Evidence Engine immediately reflects across all children referencing that claim.

### Originality Inheritance
- To prevent children from degenerating into generic social media recaps, every child item undergoes validation:
  1. **Minimum Angle Depth**: `angle` must be descriptive (at least 10 characters).
  2. **Original Value Connection**: Child must specify its tie to the parent's `original_value_type` or "What are WE adding?".
  3. **Evidence Association**: High-priority child formats (like benchmark shorts or long-form videos) must reference at least one verified claim from the parent graph.

---

## 4. Brand Integration & Repetition Prevention
The Content Family Engine works with the Brand Engine to prevent content fatigue:
- **Hook Diversity**: The engine prevents identical hook types across siblings within the same format category.
- **Angle Separation**: Ensures that multiple shorts derived from the same benchmark cover complementary aspects (e.g., Short 1 covers Speed/Latency, Short 2 covers Cost, Short 3 covers Accuracy) rather than duplicating the same angle.
- **Platform Adaptation**: Pacing, aspect ratio, tone, and call-to-action (CTA) align with brand guidelines for each target channel.

---

## 5. Production Economics & Cost Allocation
The Content Family Engine calculates clear, granular production economics:

$$\text{Shared Family Cost} = \text{research\_cost} + \text{experiment\_cost} + \text{ai\_cost} + \text{media\_cost}$$
$$\text{Total Incremental Cost} = \sum_{i \in \text{children}} \text{incremental\_cost}_i$$
$$\text{Family Total Cost} = \text{Shared Family Cost} + \text{Total Incremental Cost}$$
$$\text{Effective Cost Per Child} = \frac{\text{Shared Family Cost}}{N_{\text{children}}} + \text{incremental\_cost}_i$$

Local compute duration (`local_compute_seconds`) is tracked across both family benchmarks and child renders, enabling creators to inspect compute utilization without permanently assuming cloud costs equal local compute costs.

---

## 6. Engine Operations (`ContentFamilyEngine`)
The engine is completely decoupled from UI and persistence, exposing:
- `suggest_children(request: SuggestChildrenRequest) -> EngineResult[ContentFamilyPlan]`: Analyzes evidence claims, originality plan, and brand rules to generate a multi-format publishing strategy.
- `validate_family(family: ContentFamilyInput) -> EngineResult[ValidationResult]`: Verifies topic, research link, evidence sufficiency, and single-niche compliance.
- `validate_child(child: ContentItemInput, parent_family: ContentFamilyInput) -> EngineResult[ValidationResult]`: Ensures format validity, angle depth, originality connection, and prevents state machine violations (`SCRIPT_APPROVED` restriction).
- `calculate_economics(family: ContentFamilyInput, children: list[ContentItemInput]) -> EngineResult[FamilyEconomicsResult]`: Aggregates shared and child incremental expenditures, compute time, and unit economics.
- `explain(result: EngineResult) -> dict[str, Any]`: Structured explanation of why child items were suggested or flagged.

---

## 7. REST API Endpoints
All routes reside under `/api/v1/content-families`:
- `GET /api/v1/content-families`: List all families with optional status and pillar filters.
- `POST /api/v1/content-families`: Create a new content family.
- `GET /api/v1/content-families/{id}`: Detailed family view including child items, economics, and linked context.
- `PATCH /api/v1/content-families/{id}`: Update family strategic metadata and costs.
- `POST /api/v1/content-families/{id}/approve`: Creator Quality Gate approval; transitions status to `READY_FOR_CONTENT`.
- `POST /api/v1/content-families/{id}/archive`: Soft-archive family.
- `POST /api/v1/content-families/{id}/suggest-items`: Engine child suggestions derived from verified evidence.
- `GET /api/v1/content-families/{id}/items`: List child items with optional format/status filtering.
- `POST /api/v1/content-families/{id}/items`: Add a child content item with evidence link references.
- `GET /api/v1/content-items/{id}`: Child item detail with linked claims.
- `PATCH /api/v1/content-items/{id}`: Update child item angle, title, or status.
- `DELETE /api/v1/content-items/{id}`: Remove child item.
- `POST /api/v1/content-items/{id}/evidence`: Link an evidence claim to a child item.
- `DELETE /api/v1/content-items/{id}/evidence/{claim_id}`: Unlink an evidence claim.

---

## 8. Extension Points for Phase 12
The Content Family and Content Item models provide the exact architecture needed for **Phase 12 — Evidence-Driven Content + Script Studio**:
- `ContentItem.script_version_id`: Will reference the approved multi-section script draft.
- `ContentItem.metadata_version_id`: Will reference platform-adapted titles, descriptions, hashtags, and thumbnail specs.
- `ContentItem.status`: Will transition through `SCRIPT_REVIEW` -> `SCRIPT_APPROVED` once Phase 12 human quality gates are satisfied.
