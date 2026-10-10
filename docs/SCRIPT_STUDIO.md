# Script Studio — Evidence-Grounded Generation and Review

## Overview

The **Evidence-Driven Script Studio** is the core content production module of the Fresh Local AI Content Studio. It transforms verified research, evidence claims, original experiments, brand memory, and niche profile into structured, multi-format scripts ready for human approval.

## Current AI Provider and Release Behavior

- Google Gemini is the only live LLM provider. The selected model is stable `gemini-3.8-flash`, configurable with `GEMINI_MODEL`; credential setup and cost controls are documented in [AI Provider Configuration](AI_PROVIDER_CONFIGURATION.md).
- Generation receives the content format, platform, duration, brand guidance, originality contribution, verified research context, and selected evidence claims. It returns structured sections using Gemini's JSON response format.
- The server validates the complete response, section order, duration and pacing, brand rules, and evidence links before persisting a draft. A linked claim must be among the content item's selected verified claims; the provider schema does not replace this local check.
- Gemini failures are returned with typed recovery guidance. The application does not retry automatically or fall back to another paid provider, and a failed response does not create a draft.
- `AI_MOCK_MODE=true` uses deterministic local output. The UI labels mock or legacy output, mock drafts remain ineligible for script approval, and final media quality/export gates reject mock output.
- Every generated draft remains unapproved until a human completes Script Studio review; final media QC remains a separate approval gate.

## Architecture

```
ContentItem (Phase 11) ─────► Script Studio (Phase 12)
                                │
                                ├── ScriptDraft (1:1 per ContentItem)
                                │     ├── ScriptSection × N (structured sections)
                                │     └── ScriptRevision × N (audit trail)
                                │
                                ├── ContentEngine (decoupled engine)
                                │     ├── generate_draft()
                                │     ├── refine_section()
                                │     └── evaluate_quality()
                                │
                                └── Human Quality Gate (6 dimensions)
                                      └── Approve → SCRIPT_APPROVED
```

## Supported Formats

| Format | Sections | Duration |
|--------|----------|----------|
| `short_vertical` | 5 (Hook, Method, Evidence, Result, CTA) | 45-60s |
| `youtube_long` | 7 (all 7 standard sections) | 8-15min |
| `social_post` | 3 (Hook, Evidence, CTA) | N/A |
| `newsletter` | 4 (Hook, Evidence, Result, CTA) | N/A |
| `article` | 3 (Hook, Evidence, CTA) | N/A |

## 7 Standard Script Sections

1. **Hook** — Opening thesis or bold claim to capture attention
2. **Problem Context** — Why this topic matters, what existing info misses
3. **Method & Test** — Our originality plan, test harness, methodology
4. **Evidence** — Verified claims, benchmark data, measurements
5. **Result** — Empirical findings, synthesis, winner
6. **Interpretation** — Practical takeaways, limitations, caveats
7. **CTA** — Call to action aligned with brand CTA style

## Section-Level Refinement Tools

| Action | Effect |
|--------|--------|
| `shorten` | Trims phrasing for faster cadence |
| `expand` | Adds technical elaboration |
| `make_clearer` | Simplifies jargon, improves conversational clarity |
| `more_evidence` | Injects quantitative claim data directly |
| `regenerate` | Fresh phrasing while preserving factual references |

## 6 Quality Dimensions

The studio evaluates quality across 6 distinct dimensions — **no single opaque score**:

| Dimension | What It Checks | Blocking? |
|-----------|----------------|-----------|
| **Evidence** | Are verified claims linked to sections? | Yes — `unsupported_claim` |
| **Brand** | Are banned clichés absent? Tone compliance? | Yes — `critical_brand_failure` |
| **Originality** | Is there explicit original value contribution? | Yes — `missing_original_value` |
| **Viewer Value** | Are there actionable takeaways? | No |
| **Niche Fit** | Are blocked topics absent? | Yes — `off_niche` |
| **Repetition** | Do sections avoid identical opening words? | No |

## Hard Approval Blocks

The following quality gate failures **cannot** be approved without an explicit `override_reason`:

- `off_niche` — Script contains blocked niche topics
- `critical_brand_failure` — Banned clichés detected in narration
- `unsupported_claim` — No verified evidence linked when claims exist
- `missing_original_value` — No original value contribution declared

## Status Transitions

```
ContentItem: PLANNED → DRAFT → SCRIPT_REVIEW → SCRIPT_APPROVED
                                     ↑                ↑
                              generate_draft()   approve_script()
                                                 (Human Gate)
```

- `SCRIPT_REVIEW` — Set when a draft is generated
- `SCRIPT_APPROVED` — Set only via the Script Studio approval flow (NOT via direct PATCH)
- Upon approval, `ContentItem.script_version_id` is recorded

## Revision System

Every mutation creates an audit revision with a full snapshot:
- `initial_generation` — Draft creation
- `shorten`, `expand`, `make_clearer`, `more_evidence`, `regenerate` — Refinement
- `manual_edit` — Direct narration/visual cue editing
- `pre_restore_checkpoint` — Auto-saved before undo
- `restore` — After rollback
- `approval` — Milestone snapshot

Revisions can be restored at any time before approval.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/scripts/health` | Engine health check |
| `POST` | `/api/v1/scripts/generate` | Generate evidence-grounded draft |
| `GET` | `/api/v1/scripts/{id}` | Get script by ID |
| `GET` | `/api/v1/scripts/item/{itemId}` | Get script by content item ID |
| `PATCH` | `/api/v1/scripts/{id}/sections/{sectionId}` | Manual section edit |
| `POST` | `/api/v1/scripts/{id}/sections/{sectionId}/refine` | Section refinement |
| `POST` | `/api/v1/scripts/{id}/quality-check` | Run 6-dimension quality check |
| `POST` | `/api/v1/scripts/{id}/approve` | Human quality gate approval |
| `GET` | `/api/v1/scripts/{id}/revisions` | List revision audit trail |
| `POST` | `/api/v1/scripts/{id}/revisions/{revId}/restore` | Restore from revision |

## UI Pages

- **Script Studio** (`/script-studio/[itemId]`): Three-column editor
  - **Left**: Evidence reference drawer (parent family, claims, original value)
  - **Center**: Structured section editor with inline refinement actions
  - **Right**: Quality dimensions, revision history, human approval gate

- **Content Family Detail**: Each child item card now has a "Script Studio" button

## Database Tables

| Table | Purpose |
|-------|---------|
| `script_drafts` | Script metadata, status, quality scores |
| `script_sections` | Section narration, visual cues, word counts |
| `script_revisions` | Full snapshot audit trail |

## Banned Clichés Strategy

The engine always merges `DEFAULT_BANNED_CLICHES` with any brand-specific clichés configured in `BrandProfile.banned_cliches`. This ensures core anti-hype guardrails (e.g., "game-changer", "revolutionary", "unleash") always function regardless of brand configuration.
