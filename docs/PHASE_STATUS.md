# Phase Status Matrix

| Phase | Description | Status | Commit SHA | Tests Passing | Blockers / Notes |
|---|---|---|---|---|---|
| **Phase 0** | Greenfield Bootstrap | PASS | `fdbe69a` | 4 pytest passed, web build passed | Completed successfully |
| **Phase 1** | Single Brand/Niche Foundation (Retrofit) | PASS | `6950fee` | 42 pytest passed, web build passed | Brand Memory & Monetization added |
| **Phase 2** | Modular Engine Framework (Retrofit) | PASS | `62827cd` | 47 pytest passed, web build passed | SQLite Jobs & 8 Repositories added |
| **Phase 3** | Niche Guard + Brand Engines (Retrofit) | PASS | `c83c7aa` | 50 pytest passed, web build passed | Repetition Intelligence & 6 Dimensions |
| **Retrofit Gate** | Verification Gate (Phases 1–3) | PASS | `c83c7aa` | 50 pytest passed, web build passed | Verified against Audit Matrix |
| **Phase 4** | RSS Discovery Engine | PASS | `776dc22` | 60 pytest passed, web build passed | Canonicalization, grouping, feed isolation, zero AI calls |
| **Phase 5** | Independent Trends Engine | PASS | `af0dcb8` | 68 pytest passed, web build passed | Cross-source momentum, velocity tracking, zero paid APIs, explainability |
| **Phase 6** | Opportunity Engine + Creator Cockpit | PASS | `cab07fc` | 75 pytest passed, web build passed | 10 editable dimensions, original angles, Creator Cockpit & human gate |
| **Phase 7** | Evidence-Based Research Engine | PASS | `0105f36` | 84 pytest passed, web build passed | Traceable Research Packets with sources, claims, contradictions, and versioned revisions |
| **Phase 8** | Evidence / Provenance Engine | PASS | `8583cef` | 89 pytest passed, web build passed | Provenance graph, claims classification, coverage gate, and empirical experiments |
| **Phase 9** | Pluggable AI Provider Engine | PASS | `b436047` | 104 pytest passed, web build passed | Gemini primary, Qwen fallback, mock adapters, telemetry & token cost tracking |
| **Phase 10** | Originality & Experiment Workspace | PASS | `4ec72b5` | 116 pytest passed, web build passed | "What are WE adding?" gate, 12 originality formats, generic summary quarantine, experiment workspace & evidence link |
| **Phase 11** | Content Family Engine | PASS | `3a05052` | 127 pytest passed, web build passed | Parent-child Content Family architecture, evidence selection bridge, originality inheritance, amortized economics, and Creator Cockpit integration |
| **Phase 12** | Evidence-Driven Content & Script Studio | PASS | `54635535316a` | 137 pytest passed, web build passed | Evidence-grounded multi-format scripts, section-level refinement, 6 quality dimensions, human approval gate, revision restore |
| **Phase 13** | Export & Publishing Assistant | PASS | `a6f9d30` | 145 pytest passed, web build passed | Offline export packages, SHA-256 integrity, 7-point checklist, 4-platform browser launchers & copy metadata tools |
| **Validation Gate** | Real-World Content Validation Gate | PASS | `53a2f59` | Protocol defined | Established in docs/CONTENT_VALIDATION_PROTOCOL.md |
| **Phase 14** | Asset Rights Engine | PASS | `607fa39` | 68 pytest passed, web build passed | Provenance registry, license classifier, commercial status, attribution obligations, live evaluator & bilingual UI |
| **Phase 15** | Scene & Asset Studio | PASS | `f1aef53` | 74 pytest passed, web build passed | Evidence visual hierarchy, storyboard decomposition, local SVG generator, asset catalog & bilingual UI |
| **Phase 16** | Voice, Subtitle & Media Engine | PASS | `06f5262` | 241 backend/engine/worker tests passed twice; RSS API module: 2 passed | Local deterministic speech synthesis, sub-second SRT/VTT caption sync, local FFmpeg composition & bilingual UI. Windows SVG browser profiles use isolated workspaces and bounded lock-aware cleanup; media suite: 23 passed. RSS API fixtures now isolate and restore the singleton niche and clean up unique candidates and feeds. Full combined suites passed twice on separate fresh SQLite databases. |
| **Phase 17** | Final Creator Quality Gate | PASS | `35ccad6` | 86 pytest passed, web build passed | 9 creator quality dimensions, actionable correction routes, approval gate & bilingual UI |
| **Phase 18** | Creator Business Analytics Engine | PASS | `8b2543a` | 93 pytest passed, web build passed | Manual platform metrics, CSV import, 3s hook retention rankings, creator economics & ROI, bilingual UI |
| **Phase 19** | Human-Approved Feedback Engine | PASS | `c30bef3` | 103 pytest passed, web build passed | Closed-loop performance synthesizer, human approval gate, Brand DNA & memory updates, bilingual UI |
| **Phase 20** | Owned Audience Tracking | PASS | `abfc211` | 107 pytest passed, web build passed | Lead magnets, conversion snapshots, deterministic UTM builder, subscriber economics & valuation, bilingual UI |
| **Phase 21** | Cleanup, Backup & Reliability | PASS | `69be8a9` | 114 pytest passed, web build passed | 13th engine (cleanup), reference-safe file retention, SHA-256 backup archives, sandbox restore & SQLite PRAGMA validation, bilingual UI |
| **Phase 22** | Final E2E Certification | PASS | `ca0a5ec` | 117 pytest passed, web build passed | Complete 24-step creator journey certified, 10 invariants validated, 24 static pages verified |
| **Phase 23** | Evidence-Grounded AI Script Studio | PASS | `3826db8` | 295 backend/engine/worker tests passed, 1 live smoke skipped; TypeScript, 24-route production build, both browser smokes, and live Gemini smoke passed | Gemini-only release acceptance and integration are verified on `master`; PRs #1, #2, and #3 are merged. |
| **Phase 24** | Hybrid Category Sidebar & Action-Based Creator Workflow | PASS | `—` | 295 passed, 1 opt-in live smoke skipped; TypeScript, 24-route production build, creator workflow, Script Studio, and Gemini UI browser smokes passed | Persisted current-work summary and architecture map added. Human gates and manual publishing remain unchanged. |

## Phase 23 certification — 2026-10-10

Phase 23 is **PASS** on `master` at integration merge commit `3826db8`. Live generation uses Gemini only; deterministic Mock remains offline and unapprovable. The selected stable model is `gemini-3.8-flash`, configurable through `GEMINI_MODEL`. There is no automatic retry, OpenAI dependency, or Qwen fallback. Structured output is checked against the complete local JSON Schema, selected evidence links, pacing, and brand rules before persistence; script approval and final QC remain separate human gates.

### Acceptance verification

- Final integrated `master` backend, engine, and worker suite: `uv run --locked pytest -p phase23_test_isolation apps/api/tests apps/api/app/engines worker/tests -q -ra --tb=short` — **295 passed, 1 skipped, 10 existing Starlette deprecation warnings in 122.33 s**. The skip is the explicit opt-in live smoke; the isolation plugin forced mock AI/TTS, in-memory SQLite, dummy credentials, and blocked unexpected provider HTTP calls. This run includes the deterministic 24-step creator lifecycle certification.
- Refreshed export gate regression: **8 passed**, including a script edit 500 ms after QC approval, which must make final export stale even when the script is reapproved.
- Focused Gemini adapter, isolation, and script-generation regressions — **29 passed**.
- Frontend TypeScript check: `node_modules/.bin/tsc.cmd --noEmit --incremental false` from `apps/web` — **passed**.
- Production build: `npm run build` from `apps/web` — **passed**, all **24 routes** generated.
- Browser `npm run smoke:ai-provider-ui` — **passed**, confirming only Gemini and Mock are selectable with API responses intercepted.
- Browser `npm run smoke:script-studio` — **passed** against a persisted, temporary mock script; the page labeled it as mock and kept approval disabled. The isolated temporary database and both local servers were removed/stopped after the check.
- `git diff --check` — **passed**.

### Live Gemini acceptance

- Command: `uv run --locked pytest --run-live-provider-smoke apps/api/tests/test_live_script_provider_smoke.py -q -s` — **1 passed in 25.21 s** after explicit user authorization.
- Gemini model preflight returned **HTTP 200** and confirmed `generateContent`; the single structured generation request returned **HTTP 200**. The test validated the structured response, evidence/pacing/brand requirements, persisted Gemini provider/model provenance, research packet/version and originality plan, selected evidence links, read-back, and `is_approved=false`.
- Reported usage was **1,703 total tokens** and estimated cost **$0.002777** (telemetry estimate, not an invoice). No secret was printed.
- Earlier bounded attempts against the prior configuration returned schema errors, `MAX_TOKENS`, and one temporary timeout/503; none persisted a draft. Google documents that Gemini 3 thought tokens count against `maxOutputTokens`; the adapter now explicitly sets `thinkingLevel: low` for Gemini 3 and uses the current structured-output request format. The final request passed without application retry or fallback.

The existing Windows SAPI5/FFmpeg real-media smoke and playback measurements remain recorded in the historical media verification below; they were not rerun because the Phase 23 changes are limited to AI generation and integration fixes. The full deterministic creator lifecycle passed in the final integrated suite. PR #1 merged as `57321a3`, PR #2 as `8c9bc87`, and PR #3 as `3826db8`. Final master verification passed: **295 passed, 1 opt-in live smoke skipped**, TypeScript passed, the 24-route production build passed, and both browser smokes passed. The separate hybrid category sidebar and action-based creator workflow is the next development phase.

The previous Phase 23 reports below describe earlier OpenAI/Qwen routing revisions. They are retained as historical evidence only and do not describe the current Gemini-only implementation.

## Phase 24 implementation and verification — 2026-10-10

Phase 24 is **PASS** on `feat/v1-01-structural-backbone`, based on integrated `master` at `d8f35aebcb9f9eb1dd95391caedf4fc6833b1586`. The sidebar is organized as **Discover → Verify → Create → Produce → Publish → Learn**, with each stage expanding to its relevant engine pages. Studio settings, engine catalog, and cleanup remain grouped under Studio Tools. Desktop sidebar and mobile drawer share accessible, collapsible stage groups. The dashboard presents a next-action card based on existing setup and lifecycle counts, plus a current-work panel based on saved family and child-item state. The architecture boundary map is in `docs/V1_01_STRUCTURAL_BACKBONE.md`. All topic, research, script, final QC, and manual publishing decisions remain explicit creator actions. No backend or engine contract changed.

### Acceptance verification

- Isolated backend, engine, and worker suite: `uv run --locked pytest -p phase23_test_isolation apps/api/tests apps/api/app/engines worker/tests -q -ra --tb=short` — **295 passed, 1 skipped, 10 existing Starlette deprecation warnings in 76.88 s**. The skip is the explicit opt-in live Gemini smoke; test isolation blocked provider requests. This includes the deterministic creator lifecycle and script, QC, media, export, and publishing regressions.
- Frontend TypeScript check: `node_modules/.bin/tsc.cmd --noEmit --incremental false` from `apps/web` — **passed**.
- Production build: `npm run build` from `apps/web` — **passed**, all **24 routes** generated.
- Browser `npm run smoke:creator-workflow` against the production build — **passed** with API responses intercepted. It verified persisted current family/item status, checkpoint completion, a missing-research blocker and route, script action routing, active route after direct navigation and refresh, desktop/mobile category expansion, Escape handling, keyboard focus styling, English and Bangla labels, no browser/API errors, 44-pixel targets, and no horizontal overflow at 375, 768, and 1440 pixels.
- Browser `npm run smoke:script-studio` against the production build — **passed** with a deterministic Mock preview fixture and intercepted API responses; Mock remains unverified and script approval stays disabled.
- Browser `npm run smoke:ai-provider-ui` against the production build — **passed**, confirming Gemini and Mock remain the only selectable providers with API responses intercepted.
- `docs/V1_01_STRUCTURAL_BACKBONE.md` documents actual route/engine contracts, saved-state workflow semantics, stable boundaries, risks, and future work labeled as planned.
- `git diff --check` — **passed**.

No live Gemini or other provider request was made during Phase 24. The opt-in provider test remained skipped by the guarded suite. No provider, prompt, media engine, worker, or backend contract behavior changed.

## Historical Phase 23 verification update — 2026-10-10 (pre-Gemini-only revision)

Phase 23 remains **IN PROGRESS**. The following local evidence was collected on `feat/v1-1-ai-script-generation` at `d35503524334b5d045e1ed6b6566ddc436ddff88`:

- Guarded combined backend, engine, and worker run: `uv run --locked pytest apps/api/tests apps/api/app/engines worker/tests -q -ra` — **282 passed, 1 skipped, 10 warnings**. The process used `AI_MOCK_MODE=true`, in-memory SQLite, blank provider-key environment variables, and left the live-smoke opt-in unset. The skipped test is `apps/api/tests/test_live_script_provider_smoke.py` because live opt-in and credentials were not supplied.
- A preceding run under the root `.env` defaults made real Gemini and Qwen requests from engine-local AI tests: **4 failed, 278 passed, 1 skipped, 10 warnings**. `apps/api/tests/conftest.py` does not guard `apps/api/app/engines/ai/tests`. This is a test-isolation defect for the combined runner and must be addressed before PR #1 integration; do not run that command with developer credentials until isolated.
- Windows media lifecycle smoke command: `uv run --locked pytest apps/api/tests/test_e2e_studio_certification.py::test_e2e_24_step_creator_lifecycle -q -s --basetemp <TEMP>\phase23-media-svg-hires-20261010\pytest-artifacts -p phase23_svg_hires_plugin` — **1 passed in 70.41 s**. The temporary pytest plugin outside the repository supplied six full-resolution SVG scenes. The installed SAPI5 voices, real FFmpeg encoding, and full API/QC/export flow ran. Artifact: `%TEMP%\phase23-media-svg-hires-20261010\pytest-artifacts\test_e2e_24_step_creator_lifec0\video\video_7cb73a72_630f0472.mp4` (H.264/AAC, 1080×1920, 30 fps, 37.266667 s video / 37.270113 s audio, 0.003 s stream-duration delta); full FFmpeg decode passed. Chromium playback check command: `node %TEMP%\phase23-media-svg-hires-20261010\pytest-artifacts\playback-check.js %TEMP%\phase23-media-svg-hires-20261010\pytest-artifacts\playback-check.html` with `NODE_PATH=apps/web/node_modules` — ready state 4, 1080×1920, playback advanced to 1.376584 s. Start, middle, and end frames showed the SVG scenes and burned captions. Windows speech recognition returned non-empty text for all six real SAPI5 tracks; one technical/numeric phrase was poorly recognized, so this does not replace human listening review.
- Browser-profile cleanup regression command: `uv run --locked pytest apps/api/tests/test_media_engine.py -q` — **23 passed**. This exercises Windows Edge SVG rasterization, repeated/concurrent browser renders, and profile cleanup.
- Focused regressions: media engine **23 passed**; OpenAI adapter **28 passed** (HTTP intercepted); media/QC/export gates **4 passed**; approval-message regression passed. The approval test uses mocked generation and verifies that mock output remains unapprovable.
- Frontend checks: `tsc --noEmit --project apps/web/tsconfig.json` passed; `npm --prefix apps/web run build` passed. `smoke:ai-provider-ui` passed with API responses intercepted. `smoke:script-studio` passed with a persisted mock script and approval disabled. These browser checks do not verify a live AI provider.
- Live OpenAI smoke: **NOT RUN**. The root-resolved configuration had no `OPENAI_API_KEY`; no OpenAI request was made. The live test now asserts provider/model/token provenance, research packet/version, originality plan, selected evidence, unapproved status, and persisted read-back, but those assertions remain unverified against the real provider.

The only Phase 23 source cleanup was changing the stale Gemini/Qwen-only approval message to refer to a configured live AI provider, with a targeted regression assertion. No Phase 23 completion claim is made; live OpenAI verification and the PR #1 test-isolation fix remain outstanding.

## Historical Gemini/OpenAI routing verification update — 2026-10-10 (superseded)

Phase 23 remains **IN PROGRESS** on `feat/v1-1-ai-script-generation` at base HEAD `d35503524334b5d045e1ed6b6566ddc436ddff88`. The four previously present local modifications were preserved. Provider routing, Gemini system-variable resolution, typed fallback classifications, attempt-level cost/provenance, API status, Script Studio metadata, and the provider UI defaults now use Gemini primary and OpenAI fallback; Qwen remains selectable but is no longer the default fallback.

- Guarded backend/engine/worker regression: `uv run --locked pytest -p test_isolation apps/api/tests apps/api/app/engines worker/tests -q -ra` — **329 passed, 2 skipped, 10 warnings** in 104.47 s. The test process used mock AI/TTS, in-memory SQLite, dummy-only provider credentials, and both live-smoke flags disabled. The skipped tests were the Gemini/OpenAI-primary script smoke and the separate one-request OpenAI-fallback smoke. All 10 warnings were existing Starlette deprecations. The isolation plugin and marker registration were loaded from the separate PR #1 worktree; they are not yet integrated in the Phase 23 checkout.
- Direct PR #1 isolation check from its worktree: `uv run --locked pytest apps/api/tests/test_ai_network_isolation.py apps/api/app/engines/ai/tests/test_ai_engine.py worker/tests/test_worker.py -q -ra` — **16 passed** without supplying credentials or changing `.env`; a mocked OpenAI allowlist check confirmed a Gemini host remains blocked.
- Provider/system checks: focused Gemini/OpenAI/routing/settings tests — **80 passed**; script/API/persistence regressions — **21 passed, 1 live smoke skipped**. API settings and worker startup imports each resolved a non-secret `CONTENT_STUDIO_GEMINI` process sentinel; its value was not printed.
- Frontend checks from `apps/web`: `node_modules/.bin/tsc.cmd --noEmit --incremental false` passed; `npm run build` passed and generated all 24 routes; `npm run smoke:ai-provider-ui` passed against the production build with AI API responses intercepted.
- Gemini live script smoke, OpenAI live smoke, and a real OpenAI fallback request were **not run**. No live-provider request was made in this verification. The current process has neither `CONTENT_STUDIO_GEMINI` nor any supported OpenAI process credential; live route acceptance also requires explicit authorization.

The API/engine/worker checks and mocked fallback integration pass, but the Definition of Done is not met while live-provider acceptance is unverified and the PR #1 isolation changes remain unintegrated. Keep the PR order #1 → #2 → #3. Do not begin the hybrid-navigation UX phase until authorized Gemini/OpenAI live checks pass and all three PRs have been refreshed, reviewed, and integrated in dependency order.
