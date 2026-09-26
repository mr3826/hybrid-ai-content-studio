# Fresh Local AI Content Studio (`hybrid-ai-content-studio`)

> Greenfield local-first AI-assisted content studio engineered to transform niche-specific signals into original, verified, brand-consistent content packages.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Local-First](https://img.shields.io/badge/Architecture-Local--First-green.svg)]()
[![Single-Niche](https://img.shields.io/badge/Scope-Single--Niche%20%2F%20Single--Brand-orange.svg)]()

---

## Overview

The **Fresh Local AI Content Studio** replaces generic "summarize-and-auto-post" pipelines with an evidence-driven, human-in-the-loop production studio. It is engineered from scratch around strict architectural invariants:

- **One Niche Only:** Dedicated discovery and production tailored strictly to one domain.
- **One Brand Identity:** Consistent voice, vocabulary, visual rules, and platform adaptations across YouTube, Facebook, Instagram, and TikTok.
- **13 Independent Engines:** Feature engines with stable contracts, manifests, rules, logs, and explainability.
- **Human Quality Gate:** Explicit human review required before expensive generation, script approval, and final export.
- **Manual Publishing First:** One-click browser launchers open platform upload pages in authenticated tabs with one-click metadata copying.
- **Zero CI/CD / No n8n:** Local development and execution without external orchestrators or cloud pipeline dependencies.

---

## Architecture

```text
/
├─ apps/
│  ├─ web/          # Next.js (App Router, TypeScript, Tailwind CSS)
│  └─ api/          # FastAPI (Python 3.12, SQLAlchemy Async, SQLite WAL, Alembic)
├─ worker/          # Local Python background worker (FFmpeg, TTS, media rendering)
├─ config/          # Brand, niche, and platform YAML configurations
├─ prompts/         # Versioned prompt templates (research, originality, scripts)
├─ data/            # Local SQLite database and media storage (git-ignored)
├─ docs/            # Specifications, architecture, decisions, and phase status
└─ scripts/         # Local dev, test, backup, and cleanup scripts
```

---

## Quickstart

### Prerequisites
- **Python 3.12+** (with `uv` recommended)
- **Node.js 20+** / `npm`
- **FFmpeg 6.0+** on system PATH
- **Git**

### Installation & Run

1. **Clone & Configure:**
   ```bash
   git clone https://github.com/mr3826/hybrid-ai-content-studio.git
   cd hybrid-ai-content-studio
   cp .env.example .env
   ```

2. **Start Development Environment (Windows PowerShell):**
   ```powershell
   ./scripts/dev.ps1
   ```
   Or on Unix/macOS:
   ```bash
   ./scripts/dev.sh
   ```

3. **Open Studio:**
   - Web Studio: [http://localhost:3000](http://localhost:3000)
   - API Docs: [http://localhost:8400/docs](http://localhost:8400/docs)
   - API Health: [http://localhost:8400/health](http://localhost:8400/health)

---

## 13 Independent Engines Catalog

| # | Engine | Responsibility |
|---|---|---|
| 01 | **RSS Engine** | Discovers fresh candidates from configured feeds with zero AI calls |
| 02 | **Trends Engine** | Detects velocity and cross-source momentum inside the niche |
| 03 | **Niche Guard Engine** | Deterministic keyword and topic filtering against the single niche |
| 04 | **Opportunity Scoring Engine** | Ranks candidates based on business value, originality potential, and trend |
| 05 | **Brand Engine** | Enforces voice, tone, banned cliches, and visual identity |
| 06 | **Research Engine** | Extracts factual claims, numbers, dates, and citations |
| 07 | **Originality Engine** | Blocks generic summaries; designs original experiments and benchmarks |
| 08 | **AI Provider Engine** | Pluggable Gemini/Qwen adapters with technical fallbacks and cost tracking |
| 09 | **Content Engine** | Generates structured shorts, long-form scripts, and companion posts |
| 10 | **Media Engine** | Handles TTS, subtitle alignment, BGM, and FFmpeg video composition |
| 11 | **Export Engine** | Assembles final video, platform captions, hashtags, and manifest packages |
| 12 | **Analytics Engine** | Tracks manual publication metrics, hook performance, and content ROI |
| 13 | **Cleanup Engine** | Manages media retention, cache expiration, and reference-safe deletion |

---

## Development Status

See [`docs/PHASE_STATUS.md`](docs/PHASE_STATUS.md) for full phase-by-phase tracking.

- **Phase 0 (Greenfield Bootstrap):** Completed
- **Phase 1 (Single Brand/Niche Foundation):** Up Next

---

## License

[MIT](LICENSE) © 2026 Fresh Local AI Content Studio Contributors
