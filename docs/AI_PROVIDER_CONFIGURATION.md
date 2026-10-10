# AI Provider Configuration

## Supported providers

Live generation uses Google Gemini only. `AI_MOCK_MODE=true` routes generation to the deterministic local adapter and makes no Gemini request. Live mode sends one provider request per operation; errors are returned with a typed category and recovery guidance. There is no automatic retry or provider fallback.

The default model is `gemini-3.8-flash`, configured by `GEMINI_MODEL`. Google lists this as a stable Gemini 3 Flash model and documents structured JSON output for the Generate Content API. The adapter uses the existing `generateContent` REST contract. It sends only fields supported by Gemini's `responseSchema` object; the full local JSON Schema, including additional-property restrictions, is enforced again by the engine before script validation or persistence.

## Credential setup

Set `CONTENT_STUDIO_GEMINI` in the Windows user or system environment. Restart both the API and worker after changing environment variables. Existing installations can use `GEMINI_API_KEY`, `GEMINI_KEY`, or `GOOGLE_API_KEY`; the `.env` `GEMINI_API_KEY` value is the final fallback. `env_ignore_empty` prevents the blank `.env.example` placeholder from replacing a valid environment credential.

The API sends the key in Google's `x-goog-api-key` request header. Status endpoints, script metadata, and invocation telemetry do not return or store the credential. The repository must not contain real credentials or `.env` files.

Example `.env` values:

```dotenv
AI_MOCK_MODE=true
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
```

Set `AI_MOCK_MODE=false` only when a live Gemini credential is configured. Keep mock mode enabled for offline development and automated tests.

## Model and cost

The model name is configurable so a stable model can be changed without hardcoding provider names through the application. The default is selected provisionally from Google's current catalog; account-specific availability is confirmed by the live smoke's non-generation model lookup.

The AI engine's current Gemini estimates use the introductory Gemini 3.8 Flash standard rates documented for use through December 31, 2026: **$0.75 per million input tokens** and **$3.75 per million output tokens**. Google's published standard rates change to $1.50 / $7.50 per million tokens beginning January 1, 2027. Update `apps/api/app/engines/ai/rules.yaml` before that date so budget estimates and telemetry stay aligned with the active price schedule. These are estimates; the provider's actual account billing is authoritative.

Daily and per-content-family maximum cost estimates are checked before generation. A rate-limit response is returned as a quota/rate-limit error and the operation is not retried. The Gemini API model lookup confirms model access but does not reserve or guarantee generation quota.

## Live acceptance smoke

The live smoke is a separate, explicit opt-in and requires `Settings.GEMINI_API_KEY` to resolve a credential from `CONTENT_STUDIO_GEMINI`, `GEMINI_API_KEY`, `GEMINI_KEY`, `GOOGLE_API_KEY`, or `.env`. It checks the application setting rather than requiring a particular process-variable name, so a valid Windows alias is not mistaken for a missing credential.

Run:

```powershell
uv run --locked pytest --run-live-provider-smoke apps/api/tests/test_live_script_provider_smoke.py -q -s
```

The smoke first performs a model availability lookup. If it succeeds, the test makes one bounded `generateContent` request through the Script Studio endpoint and checks that the result uses verified evidence, carries research packet/version and originality plan provenance, is persisted with Gemini metadata, and remains unapproved. It performs no second generation request after authentication, quota, network, safety, or schema failure. The normal test suite does not run this smoke and blocks unexpected requests to known AI provider hosts.

## Current acceptance status — 2026-10-10

The configured model lookup returned HTTP 200, but the one authorized generation request returned HTTP 400 because Gemini's `responseSchema` rejected an `additionalProperties` field. The adapter now omits that unsupported provider-side field while retaining complete local JSON Schema validation. No second generation request has been sent, so live generation, persistence, provenance read-back, and unapproved status still need a successful acceptance smoke. See [Phase status](PHASE_STATUS.md) for the current verification record.

## Official Google references

- [Gemini 3.8 Flash model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
- [Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Generate Content API](https://ai.google.dev/gemini-api/docs/generate-content/latest-model)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
