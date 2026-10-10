# V1.1 Gemini Script Studio

## Provider design

`AIProviderEngine` exposes the stable `generate_text`, `generate_structured`, and `analyze` contracts to the other engines. Live requests use Gemini. Deterministic mock output is available for offline development and tests. The engine does not route, retry, or send a failed request to another provider. Existing provider and fallback fields remain in API and persistence models for compatibility with historical records.

The default model is `gemini-3.8-flash`, configurable through `GEMINI_MODEL`. Structured requests send the supported subset of the server-built schema through Gemini's JSON output mode and then validate the returned object against the full JSON Schema locally. The server remains responsible for semantic checks, evidence IDs, required section order, pacing, brand rules, and approval eligibility.

## Script generation flow

The API loads the approved content item and its singleton family, verified research packet, selected claims and source provenance, approved originality plan, completed experiment results, and singleton brand and niche profiles. It sends only selected evidence and bounded creator guidance to `ScriptGenerationService`; raw source pages are omitted.

The service sends one structured request through `AIProviderEngine`. Prompt instructions treat research and creator guidance as untrusted data. A response is checked against the requested format, section order, timing, linked claim IDs, source evidence, unsupported numbers and dates, and brand bans before persistence. Valid output is saved as an unapproved script with provider/model, usage and cost, research packet/version, originality plan, selected evidence, and input snapshot provenance. Mock output remains visibly unverified and cannot be approved or exported.

Provider errors are redacted and returned with actionable categories for missing credentials, authentication, authorization, quota/rate limits, network/timeouts, safety refusal, malformed output, schema validation, and budget limits. Failed generation creates no script draft or success revision. A human must still approve the generated script after quality checks.

## Acceptance criteria

1. Generated scripts use the selected topic and format, verified selected claims, source provenance, approved originality plan, completed experiment results, active brand/niche rules, and creator guidance.
2. Every linked claim ID belongs to the selected verified claim set; unsupported evidence and invalid model output fail before persistence.
3. Short vertical, long-form, social, newsletter, and article formats retain their own structures and pacing rules.
4. Each refinement mode uses structured generation, preserves selected evidence and brand constraints, creates a revision, and invalidates prior approval through the repository flow.
5. Gemini is the only live provider; Mock is deterministic and visibly unverified. No automatic retry or provider fallback is performed.
6. Daily and content-family cost limits block a generation before provider execution if the maximum estimated call cost exceeds the remaining budget.
7. Provider/model, execution status, usage/cost metadata, provenance, and redacted errors are visible in the API and Script Studio. Historical fallback metadata remains readable.
8. Mock and legacy-unverified scripts cannot pass the final human approval gate. Live scripts require a fresh quality check and explicit human approval.
9. Browser and API flows distinguish provider errors from generated content and do not expose credentials.
10. Offline tests, worker regressions, frontend build, browser smoke, and the separate one-request Gemini acceptance smoke are recorded independently. If model access, credentials, or quota prevent a successful live request, Phase 23 remains in progress and live certification is called out as blocked.

## API and persistence

- Existing script generation and refinement routes use injected `AIProviderEngine` dependencies.
- Script detail responses and revision snapshots include generation metadata and evidence warnings.
- Provider/model and fallback fields in existing SQLAlchemy tables are preserved to avoid rewriting historical records; new requests create Gemini or Mock records only.
- AI telemetry stores prompt hashes and safe identifiers such as content-family IDs, not prompt text or secrets.

## Security and failure handling

- The API resolves evidence and profile records server-side; clients cannot supply provider/model choice as proof or claim IDs as evidence.
- Only selected, verified claims and provenance are included in the prompt.
- Creator guidance, target duration, and generated lengths are bounded by request and service validation.
- `CONTENT_STUDIO_GEMINI` is the preferred Windows user/system credential variable; compatible Gemini aliases and `.env` `GEMINI_API_KEY` remain supported.
- The key is sent in Google's authorization header and never returned through status responses or persisted in telemetry.
- Test setup enables mock AI/TTS, uses in-memory SQLite, replaces provider credentials with sentinels, and blocks real requests to known AI-provider hosts. Only the explicitly opted-in `live_provider` test may send a Gemini request.

## Model and cost configuration

`GEMINI_MODEL` defaults to the stable `gemini-3.8-flash` identifier. The test smoke checks account model availability before generation. It performs one bounded script-generation call and does not retry on quota, auth, network, safety, or schema errors. The test can verify model access before it consumes generation quota, but the API has no quota reservation in this flow.

Current Gemini cost rates are stored in `apps/api/app/engines/ai/rules.yaml`. The [provider configuration guide](AI_PROVIDER_CONFIGURATION.md) records the current introductory price schedule and its effective date.

## Dependency and history

Phase 23 remains in the existing PR chain #1 → #2 → #3. PR #3 contains script generation and Gemini provider simplification; PR #1 contains process-wide test isolation. PR descriptions must state the current Gemini-only scope and must not claim live OpenAI or Qwen generation.

Earlier verification entries in `docs/PHASE_STATUS.md` record test and media results from previous revisions. They are historical evidence and do not establish live Gemini acceptance for this revision. The latest Phase 23 entry is authoritative for the current status.
