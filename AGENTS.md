# AGENTS.md — Development Invariants & Guidelines

## Mission & Architecture
The **Fresh Local AI Content Studio** (`hybrid-ai-content-studio`) is a local-first, single-niche, single-brand content studio engineered to transform niche signals into original, verified, brand-consistent content packages.

### Non-Negotiable Invariants
1. **Single Niche:** There is exactly **one** active niche (`NicheProfile`). Do not build multi-niche switchers, workspace selectors, or multi-tenant channel managers.
2. **Single Brand:** There is exactly **one** active brand (`BrandProfile`). All content inherits its tone, voice, vocabulary, visual identity, and editorial policies.
3. **Engine Independence:** All 13 engines (RSS, Trends, Niche Guard, Opportunity, Brand, Research, Originality, AI Provider, Content, Media, Export, Analytics, Cleanup) must remain decoupled with stable contracts (`contracts.py`), independent manifests (`manifest.yaml`), rules, tests, logs, and explainability. UI orchestrates engines but never depends on their private implementations.
4. **Human Quality Gates:** Automated auto-posting is forbidden. Explicit human approval is required:
   - Topic approval (from Opportunity feed)
   - Research verification (facts and citations checked)
   - Script approval (Brand QA checked)
   - Final QC approval (before export)
5. **Manual Platform Publishing in V1:** Direct social API uploads (YouTube Data API, Meta Graph API, TikTok Direct Post) are out of scope for V1. Publishing is executed by the user via one-click browser launcher buttons (`target="_blank"`, `rel="noopener noreferrer"`) with metadata copied to clipboard.
6. **No n8n Dependency:** Under no circumstances should n8n, legacy webhook workflows, or legacy Milestone A code be reintroduced.
7. **No CI/CD Pipelines:** GitHub Actions and remote deployment workflows are explicitly forbidden. Verification is conducted locally.
8. **Local-First Infrastructure:** SQLite with WAL mode (`sqlite+aiosqlite:///data/db/studio.sqlite`), local Python worker for FFmpeg/TTS/heavy jobs, and localhost binding.
9. **Zero Secrets in Git:** Never commit API keys, `.env` files, browser profiles, SQLite databases, or generated media.

## Phase Execution Protocol
- Always refer to `docs/PHASE_STATUS.md` before starting any phase.
- Execute strictly one phase at a time.
- Verify all automated unit tests, build checks, and browser verifications before marking a phase complete.
- Every phase concludes with a single atomic, conventional commit.
