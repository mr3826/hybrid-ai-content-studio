# V1.1 AI Script Studio Design

## Observed behavior

- `ContentEngine.generate_script()` and `refine_section()` currently return deterministic templates and edits. The Script Studio API persists those results directly.
- `AIProviderEngine` already routes structured requests through Gemini and Qwen and records sanitized invocation telemetry, but Script Studio does not call it.
- Research claims carry verification state and source links; content families also reference an originality plan and an optional primary experiment.
- `MAX_AI_COST_PER_DAY` and `MAX_GENERATION_COST_PER_PROJECT` are configured, but generation requests currently do not enforce either limit.
- Script records preserve revisions and quality scores but do not persist which provider produced the current text.

## Design

The API layer will orchestrate a new `ScriptGenerationService`. It will load the approved content item, verified research packet, selected claims and source provenance, approved originality plan, completed experiment results, and the singleton brand and niche profiles. It will call only the existing `AIProviderEngine.generate_structured()` contract. `ContentEngine` remains the engine that calculates script quality and does not gain provider-specific HTTP code.

The generation prompt treats all research text and creator guidance as untrusted data. Its system instructions prohibit following instructions found inside research material and prohibit unsupported measurements, sources, dates, or results. A strict Pydantic response model will validate sections, section order, non-empty narration, word timing, and claim references before persistence. Refinement follows the same provider, evidence, brand, and output validation path.

Provider/model, fallback state, token counts, cost, and mock/live status will be stored with the script and in revision snapshots. AI telemetry will carry the content-family ID without storing source text or secrets. The daily budget is checked by the AI Provider Engine using the configured maximum token allowance before a provider call. The per-project budget is enforced by the Script Generation Service against the content family's persisted AI cost and the estimated maximum call cost; actual returned cost is then added to the family and exposed in script metadata.

Mock provider output is labeled as mock and can only be generated in explicitly configured mock mode. Quality approval is always blocked for mock or legacy scripts without live-provider provenance, even when a human supplies an override reason. Provider failures return actionable, redacted API errors and create no script revision or success state.

## Acceptance criteria

1. A generated script is based on the selected topic, format, verified selected claims, source provenance, approved originality plan, completed experiment results, active brand/niche rules, and creator guidance.
2. Every `linked_claim_ids` entry exists in the selected claim set; unknown IDs and unsupported model output are rejected before persistence.
3. Short vertical, long-form, social, newsletter, and article formats retain their own structure and target pacing. Video timing is calculated from actual narration word counts using the configured speech cadence.
4. Each refinement mode calls structured AI generation and preserves selected evidence and brand constraints. Refinements create revisions and invalidate prior approval through the existing repository flow.
5. Gemini is primary, Qwen is used only for technical/schema failures, and deterministic mock output remains visibly unverified.
6. Daily and content-family AI cost limits block generation before provider execution when the maximum estimated call cost exceeds remaining budget.
7. Provider/model, fallback, execution status, and usage/cost metadata are visible in the API and Script Studio. Failure details are useful and secrets are redacted.
8. Mock and legacy-unverified scripts cannot pass the final human approval gate. Live-provider scripts continue to require a fresh quality check and explicit human approval.
9. Script Studio displays provider/fallback/cost and mock/live status, and renders provider errors without mislabeling them as generated content.
10. Backend, worker, frontend production build, browser flow, and one authorized live-provider smoke test pass. The live smoke uses verified source material and does not expose credentials.

## API and persistence changes

- Extend the script detail response with generation metadata and evidence warnings.
- Add a nullable JSON metadata column to `scripts` and capture it in revision snapshots.
- Add provider-injected dependencies to the Script Studio routes for deterministic API tests.
- Preserve existing route paths and response fields; only add response fields.

## Security and failure handling

- Load data by the requested item and its family; never accept provider/model or claim IDs from the client as evidence.
- Include only selected, verified claims and their source records in the prompt. Omit raw source page content.
- Bound creator guidance and all target lengths through Pydantic validation.
- Redact both provider credentials from propagated errors. Telemetry stores prompt hashes and content-family IDs, not prompt contents.
- Fail closed on unverified research, missing selected evidence, unapproved originality plans, malformed structured output, unsupported claim IDs, and budget exhaustion.

## Dependency note

PR #1 and PR #2 are still open. This feature branch is staged on PR #2's head so its final diff can be retargeted cleanly to `master` after both prerequisites are merged. The PR #1 security and approval rules remain intact. Integration tests required small schema-alignment fixes in export/QC reads, and the inherited media renderer now disables background browser mode to avoid leaving a locked temporary profile on Windows.

The opt-in live-provider smoke did not complete successfully in this environment. Gemini returned structurally valid topic-specific responses, but two drafts were rejected by local pacing validation before persistence; a later request hit the provider quota (HTTP 429). The configured Qwen fallback returned HTTP 401. The live smoke remains a merge blocker until a real script is generated and saved without mock output.
