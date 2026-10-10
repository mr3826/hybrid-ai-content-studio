# Fresh Local AI Content Studio (`hybrid-ai-content-studio`)

> **Local-first, single-niche, evidence-driven content production studio engineered to transform niche signals into original, verified, brand-consistent content packages with offline export and zero automated spam.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Local-First](https://img.shields.io/badge/Architecture-Local--First%20%28SQLite%20WAL%29-green.svg)]()
[![Single-Niche](https://img.shields.io/badge/Scope-Single--Niche%20%2F%20Single--Brand-orange.svg)]()
[![Status: V1 Certified](https://img.shields.io/badge/Status-V1%20100%25%20Certified-brightgreen.svg)](docs/FINAL_V1_CERTIFICATION.md)
[![Test Suite](https://img.shields.io/badge/Tests-117%20Passed%20%28100%25%29-success.svg)](apps/api/tests/test_e2e_studio_certification.py)
[![Web Routes](https://img.shields.io/badge/Web%20Routes-24%20Static%20Pages%20Verified-blueviolet.svg)](apps/web)

---

## Table of Contents

1. [Overview & Philosophy](#1-overview--philosophy)
2. [The 10 Non-Negotiable Invariants](#2-the-10-non-negotiable-invariants)
3. [Full Project Scope (13 Engines & Capabilities)](#3-full-project-scope-13-engines--capabilities)
4. [System Architecture & Stack](#4-system-architecture--stack)
5. [User Manual: The End-to-End Creator Workflow](#5-user-manual-the-end-to-end-creator-workflow)
6. [Installation & Setup](#6-installation--setup)
7. [Running the Application](#7-running-the-application)
8. [Testing & Verification](#8-testing--verification)
9. [Data Retention, Security & Backups](#9-data-retention-security--backups)
10. [Troubleshooting & FAQ](#10-troubleshooting--faq)
11. [License](#11-license)

---

## 1. Overview & Philosophy

Most automated AI content tools today suffer from fatal flaws: they generate generic summaries of trending topics, churn out cliché-ridden scripts, produce unverified claims, and upload low-quality slop directly to social APIs.

The **Fresh Local AI Content Studio** takes the opposite approach:
- **Quality over Quantity:** Focuses on proving, testing, benchmarking, and explaining rather than mass generation.
- **Evidence-Driven:** Every script and post links back to primary sources, verifiable benchmark runs, or clearly labeled opinions.
- **Human-in-the-Loop:** Automated publishing is explicitly forbidden. The creator approves topics, verifies research, reviews scripts, and signs off on final media QC.
- **Local-First & Private:** Runs entirely on localhost with SQLite WAL mode. No cloud databases, no remote orchestrator locks, no monthly SaaS subscriptions required.
- **Single Brand & Niche Mastery:** Deep, uncompromised focus on exactly one technical niche and one brand voice rather than shallow multi-tenant switching.

---

## 2. The 10 Non-Negotiable Invariants

| # | Invariant | Description |
|---|---|---|
| **1** | **Single Niche** | Exactly **one** active `NicheProfile` (`id: primary`). No multi-tenant workspace switchers. |
| **2** | **Single Brand** | Exactly **one** active `BrandProfile` (`id: primary`). All content inherits its tone, voice, and rules. |
| **3** | **Local-First** | SQLite with WAL mode (`sqlite+aiosqlite:///data/db/studio.sqlite`), local Python background worker, and localhost binding. |
| **4** | **Engine Independence** | All 13 engines are decoupled with stable contracts (`contracts.py`), manifests (`manifest.yaml`), rules, tests, and explainability. |
| **5** | **Human Quality Gates** | Auto-posting is forbidden. Explicit human approval is mandatory at Topic, Research, Script, QC, and Feedback gates. |
| **6** | **Manual Publishing First** | Direct social API uploads (YouTube Data API, Meta Graph API, TikTok Direct Post) are excluded. Publishing is executed by the creator via one-click browser launcher buttons with metadata copied to clipboard. |
| **7** | **Cost-Aware Operation** | Zero paid third-party APIs required. Local deterministic TTS, local SVG asset generation, compute tracking, and creator ROI models. |
| **8** | **Evidence-Driven Content** | Claims must be grounded in primary/supporting citations. Automated "What are WE adding?" originality validation quarantines generic summaries. |
| **9** | **Zero n8n Dependency** | Pure Python/FastAPI/SQLAlchemy async architecture. Zero legacy webhook workflows. |
| **10** | **Zero CI/CD Pipelines** | Zero GitHub Actions or remote deployment dependencies. All verification is conducted locally. |

---

## 3. Full Project Scope (13 Engines & Capabilities)

The Studio consists of **13 concrete, decoupled backend engines** and a modern **Next.js web studio** spanning 24 specialized routes:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              CREATOR COCKPIT (Next.js)                                 │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
  ┌───────────────────────┬─────────────────┴─────────────────┬───────────────────────┐
  ▼                       ▼                                   ▼                       ▼
01. RSS DISCOVERY     02. TRENDS INTELLIGENCE             03. NICHE GUARD        04. OPPORTUNITY
Feed ingestion,       Velocity tracking,                  Deterministic keyword  10-dimension matrix,
deduplication, zero   momentum detection,                 & category filtering,  original angle
AI calls required     explainable scoring                 repetition guard       suggestions, human gate
  │                       │                                   │                       │
  └───────────────────────┼───────────────────────────────────┴───────────────────────┘
                          │
  ┌───────────────────────┴───────────────────────────────────┬───────────────────────┐
  ▼                                                           ▼                       ▼
05. BRAND ENGINE & MEMORY                                 06. RESEARCH ENGINE     07. EVIDENCE ENGINE
Enforces voice rules, preferred/avoid vocabulary,         Extracts facts, claims, Provenance graph, source
banned clichés, visual identity, platform adaptations     dates, entities, flags  citation links, opinion
                                                          contradictions          labeling & lab experiments
  │                                                           │                       │
  └───────────────────────┬───────────────────────────────────┴───────────────────────┘
                          │
  ┌───────────────────────┴───────────────────────────────────┬───────────────────────┐
  ▼                                                           ▼                       ▼
08. AI PROVIDER ENGINE                                    09. ORIGINALITY ENGINE  10. CONTENT FAMILIES
Gemini live generation, offline mock,                     "What are WE adding?"   Parent-child structure,
token cost tracking & latency telemetry                   gate, 12 test formats,  shared research,
                                                          quarantine summaries    amortized economics
  │                                                           │                       │
  └───────────────────────┬───────────────────────────────────┴───────────────────────┘
                          │
  ┌───────────────────────┴───────────────────────────────────┬───────────────────────┐
  ▼                                                           ▼                       ▼
11. SCRIPT STUDIO & QA                                    12. SCENE & ASSET       13. VOICE & MEDIA
5-section evidence-grounded scripts, section refinement,  Storyboard scenes, SVG  Deterministic TTS,
revision restore, Brand QA cliché detection               generator, visual cues  sub-second SRT/VTT, FFmpeg
  │                                                           │                       │
  └───────────────────────┬───────────────────────────────────┴───────────────────────┘
                          │
  ┌───────────────────────┴───────────────────────────────────┬───────────────────────┐
  ▼                                                           ▼                       ▼
14. ASSET RIGHTS ENGINE                                   15. QUALITY GATE        16. EXPORT ASSISTANT
License classification (CC0, MIT, Apache vs Editorial),   9 quality dimensions,   Offline ZIP package,
commercial risk audit, attribution obligations            actionable corrections, SHA-256 manifest, browser
                                                          human export unlock     launchers, clipboard copy
  │                                                           │                       │
  └───────────────────────┬───────────────────────────────────┴───────────────────────┘
                          │
  ┌───────────────────────┴───────────────────────────────────┬───────────────────────┐
  ▼                                                           ▼                       ▼
17. BUSINESS ANALYTICS                                    18. FEEDBACK ENGINE     19. OWNED AUDIENCE
24h/7d metric snapshots, 3s/30s hook retention ranking,   Closed-loop learning,   Lead magnets, UTM builder,
view-through rates, creator ROI economics                 human gate to apply to  conversion attribution,
                                                          Brand DNA memory        subscriber valuation
  │                                                           │                       │
  └───────────────────────┬───────────────────────────────────┴───────────────────────┘
                          │
  ┌───────────────────────┴───────────────────────────────────────────────────────────┐
  ▼                                                                                   ▼
20. STORAGE RETENTION & CLEANUP                           21. BACKUP & RELIABILITY RECOVERY
Reference-safe media cleanup, cache expiration,           SHA-256 ZIP snapshots, sandbox restore test,
dry-run inspection mode, zero active content deletion     SQLite PRAGMA integrity_check verification
```

---

## 4. System Architecture & Stack

```text
d:\hexabyte_technologies\easy-content\
├─ apps/
│  ├─ api/                          # FastAPI REST API (Python 3.12+ / 3.14)
│  │  ├─ app/
│  │  │  ├─ api/v1/                 # 27 Modular sub-routers (/niche, /brand, /rss, /scripts, etc.)
│  │  │  ├─ core/                   # Database (SQLite WAL), config, settings
│  │  │  ├─ engines/                # 13 Decoupled engines with contracts, manifests & rules
│  │  │  ├─ models/                 # SQLAlchemy Async ORM models
│  │  │  ├─ repositories/           # Isolated data access repositories
│  │  │  └─ main.py                 # Application factory & lifespan handlers
│  │  └─ tests/                     # 117 Pytest automated unit and integration tests
│  └─ web/                          # Next.js 15+ Web Dashboard (React, Tailwind CSS, Lucide icons)
│     ├─ app/                       # 24 Specialized App Router pages
│     ├─ components/                # Reusable bilingual UI components
│     └─ lib/                       # API client and TypeScript interfaces
├─ worker/                          # Local Python background daemon for heavy media jobs
├─ config/                          # Niche, brand, and platform YAML definitions
├─ prompts/                         # Versioned prompt templates
├─ data/                            # Local SQLite database (studio.sqlite) and media assets
├─ docs/                            # Architecture specs, phase status, certification reports
└─ scripts/                         # Local development launchers, test runners, and backups
```

### Technology Highlights
- **Backend**: FastAPI, SQLAlchemy 2.0 (Async), SQLite with WAL mode, Alembic, Pydantic V2.
- **Frontend**: Next.js 15 (App Router), React 19, Vanilla Tailwind CSS, Lucide Icons.
- **Media**: Local FFmpeg, deterministic Speech Synthesis, sub-second SRT caption alignment, SVG diagram generation.
- **Testing**: Pytest, Pytest-Asyncio, HTTPX, SQLite PRAGMA test fixtures.

---

## 5. User Manual: The End-to-End Creator Workflow

Here is the complete step-by-step creator journey from day one to continuous publishing and learning:

```text
 [1. Settings]   ──> [2. Sources & Trends] ──> [3. Opportunities] ──> [4. Research Packet]
       │                                                                      │
       ▼                                                                      ▼
 [8. Script Studio] <── [7. Content Family] <── [6. Originality] <── [5. Evidence Graph]
       │
       ▼
 [9. Scene Studio]  ──> [10. Media Studio]  ──> [11. Quality Gate] ──> [12. Export & Launch]
                                                                              │
                                                                              ▼
 [16. Storage Clean]<── [15. Feedback DNA] <── [14. Analytics]   <── [13. Manual Publish]
```

### Step 1: Initial Studio Setup & Brand Identity (`/settings`)
1. Navigate to **Studio Settings** at `http://localhost:3000/settings`.
2. Configure your **Single Niche**: Define your core audience, allowed topics, blocked topics, negative keywords, and 3–5 Content Pillars (e.g., *Hardware Benchmarks*, *Agent Workflows*).
3. Configure your **Single Brand**: Define brand promise, tone (e.g., *calm, concise, evidence-driven*), voice rules, preferred vocabulary, banned clichés (e.g., *"In today's fast-paced world..."*, *"game-changer"*), and visual typography.
4. Set up platform channels and target URLs for **YouTube**, **Facebook**, **Instagram**, and **TikTok**.

### Step 2: Ingest Signals & Detect Trends (`/sources`, `/trends`)
1. In **RSS Sources** (`/sources`), register active engineering blogs, GitHub release feeds, or technical newsletters.
2. Click **Run Discovery** to parse, normalize, canonicalize, and deduplicate articles into candidate signals.
3. Open **Trends Intelligence** (`/trends`) to inspect velocity scores and cross-source momentum. Click **Explain** on any trend cluster to view transparency weights and source citations.

### Step 3: Opportunity Intelligence & Topic Approval (`/opportunities`)
1. Open the **Opportunities Feed** (`/opportunities`).
2. Review scored topics ranked by the 10-dimension matrix (freshness, originality potential, evidence accessibility, creator ROI).
3. Click **Explain** to see why a topic ranked high and check suggested original angles.
4. **Human Quality Gate 1**: Click **Approve for Research** to transition the candidate to `research_ready`, or **Reject** with a recorded reason.

### Step 4: Sourced Research & Contradiction Analysis (`/research`)
1. Open **Research Packets** (`/research`).
2. Add primary benchmark reports, documentation, or engineering articles.
3. The Research Engine parses the input into:
   - Primary vs. Supporting Sources
   - Verified Facts, Exact Numbers, Dates, and Named Entities
   - Contradiction warnings (e.g., *Vendor claims 14ms latency vs Independent lab measured 42ms*)
   - Things NOT to claim (defensive boundaries)
4. **Human Quality Gate 2**: The creator reviews and clicks **Verify Research Packet**.

### Step 5: Evidence Grounding & Claim Provenance (`/evidence`)
1. Open the **Evidence Studio** (`/evidence`).
2. View the Provenance Graph: every factual claim is classified into `external_fact`, `empirical_test`, or `opinion`.
3. Link claims to primary source URLs and quotes with confidence weights.
4. Any unverified claims block downstream script approval until verified or reclassified.

### Step 6: Originality Planning & Experiment Attachments (`/originality`)
1. Open the **Originality Workspace** (`/originality`).
2. Pass the **"What are WE adding?" Gate**: Select 1 of 12 originality formats (e.g., *Hardware Stress Test*, *Cost Amortization Calculator*, *Side-by-side Benchmark*).
3. The engine quarantines generic summaries that merely rehash external news without unique creator value.
4. Attach empirical lab measurements, terminal commands, or wattmeter logs.

### Step 7: Content Family Creation (`/content-families`)
1. Create a parent **Content Family** (`/content-families`) tied to a Content Pillar and your shared experiment.
2. Log the core research and compute costs once (e.g., *$2.00 API, 60 mins lab time*).
3. Click **Suggest Child Items** to generate tailored derivative formats:
   - Short Vertical (YouTube Shorts / TikTok / Reels)
   - Long Video breakdown (YouTube Long)
   - Visual Carousel (Instagram / LinkedIn)
   - Text Thread / Technical Notes (X / Threads)
4. The studio amortizes the core investment across all derivative child assets.

### Step 8: Evidence-Grounded Script Generation & Refinement (`/script-studio/[itemId]`)
1. Select a child item and open **Script Studio** (`/script-studio/[itemId]`).
2. Click **Generate Script Draft**. The engine generates a structured 5-section narrative:
   - `Hook`: Curiosity gap or bold empirical claim (< 3 seconds)
   - `Problem / Setup`: Real developer frustration
   - `Empirical Test / Breakdown`: Physical demonstration or terminal log
   - `Insight / Solution`: Actionable takeaways and config flags
   - `Call to Action`: Clear next step
3. Use section-level refinement buttons: **Shorten**, **Expand**, **Make Punchier**, or manually edit narration and visual cues.
4. Inspect full **Revision History** and restore earlier versions with one click.

### Step 9: Script Brand QA Audit & Human Approval Gate
1. Click **Run Quality Check**. The engine audits:
   - Evidence grounding (all claims backed)
   - Brand tone fit
   - Banned clichés detection
2. If any banned phrase (e.g., *"game changer"*) is detected, approval is blocked.
3. **Human Quality Gate 3**: The creator clicks **Approve Script** (or enters an explicit satirical override reason). Item transitions to `SCRIPT_APPROVED`.

### Step 10: Storyboard Scene Decomposition (`/scene-studio`)
1. Open **Scene Studio** (`/scene-studio`).
2. Click **Decompose into Scenes**: splits script sections into ordered storyboard visual cues.
3. Choose layout structures: `Split Screen`, `Terminal Highlight`, `Chart Diagram`, `Fullscreen Cam`.
4. Generate local SVG infographics or custom benchmark comparison cards without cloud dependencies.

### Step 11: Asset Rights Auditing (`/asset-rights`)
1. Open **Asset Rights Engine** (`/asset-rights`).
2. Verify visual and audio assets against the license classifier:
   - Verified Licenses: CC0, MIT, Apache 2.0, Public Domain, Self-Created.
   - Flagged Licenses: Commercial Use Prohibited, Editorial Only, Unknown.
3. Ensure required attribution obligations are satisfied.

### Step 12: Voice Synthesis, Subtitles & Media Preview (`/media-studio`)
1. Open **Media Studio** (`/media-studio`).
2. Select an installed Windows SAPI5 voice. The voice list reports the actual voices and languages available on this computer; unsupported languages such as Bangla fail clearly.
3. Attach a rights-cleared visual asset to every storyboard scene. Supported local image/video formats are read from `data/assets`; SVG scenes are rasterized with installed Edge or Chrome. Missing or invalid assets stop the render.
4. Generate **SRT/VTT subtitles**. Scene boundaries use measured narration durations; individual word cue times are proportional estimates because forced alignment is not available.
5. Run the local Python worker with FFmpeg and FFprobe installed. It creates and verifies the MP4 in the selected 9:16 or 16:9 dimensions. If captions are requested, a subtitle burn-in failure stops the render.
6. Mock harmonic audio is available only for isolated tests and is labeled `MOCK`; mock or failed media cannot pass final QC or export.

### Step 13: 9-Dimension Creator Quality Gate (`/quality-gate`)
1. Open **Quality Gate** (`/quality-gate`).
2. Review the 9 evaluation dimensions:
   1. Evidence Quality
   2. Brand Fit
   3. Originality Strength
   4. Viewer Practical Value
   5. Niche Alignment
   6. Repetition Intelligence
   7. Asset Rights Clearance
   8. Media QC (Audio/Subtitle sync)
   9. Estimated Compute Cost
3. **Human Quality Gate 4**: Click **Sign Off Quality Gate**. This unlocks the offline export package.

### Step 14: Export Platform Package (`/publishing/[itemId]`)
1. Navigate to **Publishing Assistant** (`/publishing/[itemId]`).
2. Click **Assemble Export Package**. The engine creates an offline folder and ZIP archive containing:
   - Final rendered MP4 video
   - SRT and VTT subtitles
   - Thumbnail images
   - Platform-optimized titles, descriptions, and hashtags
   - Sources & citations markdown file
   - `manifest.json` with SHA-256 integrity checksums
3. Click **Download ZIP Package**.

### Step 15: One-Click Launch & Manual Publishing Flow
1. Review the **7-point pre-publish checklist** (media checked, rights clear, thumbnail ready, citations verified).
2. Click **Open YouTube Studio** (or TikTok / Instagram / Facebook) to launch the authenticated web page in a new browser tab.
3. Click **Copy Metadata to Clipboard** to grab title, description, and tags formatted for that platform.
4. Upload the video manually. Paste the metadata.
5. In the studio, enter the live HTTPS URL (e.g., `https://youtube.com/watch?v=...`) and click **Mark Published**.

### Step 16: Business Analytics & Retention Rankings (`/analytics`)
1. At 24 hours, 7 days, and 30 days post-publish, record performance snapshots (views, watch time, 3s retention, revenue, leads).
2. Inspect the **Hook Retention Leaderboard**: compares 3s and 30s drop-off across different hook types (*bold claim* vs *curiosity gap*).
3. Review the **Creator Economics & ROI Breakdown**: calculates Net Creator Profit = Platform Revenue + Audience Asset Value - (Compute + Token + Labor Cost).

### Step 17: Closed-Loop Feedback & Brand DNA Evolution (`/feedback`)
1. Open the **Feedback Engine** (`/feedback`).
2. Click **Synthesize Feedback**: Analyzes low-retention drop points and high-converting hooks.
3. Review proposed Brand adjustments (e.g., *"Ban opening rhetorical questions on TikTok; increase terminal code time"*).
4. **Human Quality Gate 5**: The creator reviews and clicks **Apply to Brand DNA**. The BrandProfile and Brand Memory are automatically updated.

### Step 18: Owned Audience Growth & Lead Conversion Tracking (`/audience`)
1. Open **Owned Audience** (`/audience`).
2. Register **Lead Magnets** (e.g., *Benchmark Shell Rig*, *Architecture PDF Cheatsheet*).
3. Use the **Deterministic UTM Builder** to generate tracking URLs for video descriptions.
4. Track conversion events and calculate list valuation based on creator-defined subscriber value (e.g., *$25/subscriber*).

### Step 19: Storage Maintenance & Verified Backups (`/cleanup`)
1. Open **Storage Retention & Backups** (`/cleanup`).
2. Run **Storage Inspection** to see disk usage breakdown.
3. Execute **Dry-Run Cleanup**: identifies orphaned scratch files while strictly protecting referenced project assets.
4. Click **Create Verified Backup Snapshot**: creates a SHA-256 ZIP archive of database, manifests, and profiles.
5. Click **Test Sandbox Restore**: safely unpacks backup and executes SQLite `PRAGMA integrity_check;` to verify database health.

---

## 6. Installation & Setup

### Prerequisites
- **Python 3.12+** (Python 3.14 fully supported)
- **Node.js 20+** and `npm`
- **FFmpeg 6.0+** installed and available on system `PATH`
- **Git**
- Optional: `uv` (recommended for fast Python dependency management)

### 1. Clone the Repository
```bash
git clone https://github.com/mr3826/hybrid-ai-content-studio.git
cd hybrid-ai-content-studio
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Default `.env` settings are ready out of the box with zero paid API keys:
```ini
APP_ENV=development
LOG_LEVEL=INFO

API_HOST=127.0.0.1
API_PORT=8400
DATABASE_URL=sqlite+aiosqlite:///data/db/studio.sqlite
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

NEXT_PUBLIC_API_BASE_URL=http://localhost:8400

# Cost & Provider Controls (Mock mode active by default)
AI_MOCK_MODE=true
# Gemini is the only live provider. On Windows, set CONTENT_STUDIO_GEMINI
# in the user/system environment. GEMINI_KEY and GOOGLE_API_KEY remain supported.
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
TTS_MOCK_MODE=true
FFMPEG_BINARY=ffmpeg
```

### 3. Backend Setup (Python)
Using `uv` (recommended):
```bash
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv pip install -e .
```
Or standard `pip`:
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
pip install -e .
```

### 4. Frontend Setup (Next.js)
```bash
cd apps/web
npm install
cd ../..
```

---

## 7. Running the Application

### Option A: All-in-One Launcher (Recommended)
On **Windows PowerShell**:
```powershell
./scripts/dev.ps1
```
On **macOS / Linux**:
```bash
chmod +x ./scripts/dev.sh
./scripts/dev.sh
```

This single command starts:
- **FastAPI API Server**: `http://localhost:8400`
- **Next.js Web Studio**: `http://localhost:3000`
- **Background Worker**: Local Python queue poller

### Option B: Manual Process Execution

**Terminal 1 — API Server:**
```powershell
.venv\Scripts\uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8400 --reload
```

**Terminal 2 — Background Media Worker:**
```powershell
.venv\Scripts\python worker/worker.py
```

**Terminal 3 — Next.js Web Studio:**
```bash
npm --prefix apps/web run dev
```

### Access URLs
- **Web Studio**: [http://localhost:3000](http://localhost:3000)
- **API Documentation (Swagger UI)**: [http://localhost:8400/docs](http://localhost:8400/docs)
- **API Health Check**: [http://localhost:8400/health](http://localhost:8400/health)

---

## 8. Testing & Verification

The project enforces **100% automated test coverage** across all domain engines and a **clean static build** for all 24 web routes.

### Run Backend Pytest Suite
```powershell
# Run full suite
.venv\Scripts\pytest.exe -q

# Run with verbose output
.venv\Scripts\pytest.exe -v

# Run the 24-step End-to-End Creator Journey certification
.venv\Scripts\pytest.exe apps/api/tests/test_e2e_studio_certification.py -v
```
**Current Status**: **117 passed, 0 failed (100% pass rate)**.

### Run Frontend Production Build Check
```bash
cd apps/web
npm run build
```
**Current Status**: **24 / 24 static pages compiled cleanly with 0 TypeScript/lint errors**.

---

## 9. Data Retention, Security & Backups

### Zero Secrets Policy
- Zero API keys, OAuth tokens, browser session profiles, or passwords are ever committed to Git.
- `.gitignore` strictly protects `.env`, `data/db/studio.sqlite`, `data/exports/`, and media directories.

### Local-First Persistence & WAL Mode
- SQLite runs with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), ensuring crash-safe concurrent reads and writes between the API and background worker.

### Reference-Safe Retention
- Media and script assets linked to active content items, published packages, or analytics snapshots are **reference-protected**.
- The Cleanup Engine will never delete assets marked active or published.

### Automated Verified Backups
- The Backup Manager generates portable, timestamped ZIP archives containing database state, JSON manifests, and brand memory.
- Every archive embeds a SHA-256 checksum and can be verified via sandbox restore using SQLite `PRAGMA integrity_check;`.

---

## 10. Troubleshooting & FAQ

#### Q: Can I run AI and media generation offline?
**A:** Set `AI_MOCK_MODE=true` and `TTS_MOCK_MODE=true` to use the deterministic local AI and speech adapters. Live script generation requires `AI_MOCK_MODE=false`, a Gemini credential, and outbound HTTPS access to Google's Gemini API. Other studio features such as RSS discovery may also need internet access.

#### Q: How are AI providers configured?
**A:** `AI_MOCK_MODE=true` uses the deterministic local adapter and makes no Gemini request. Live mode uses Gemini only; set `AI_MOCK_MODE=false`, configure `GEMINI_MODEL` (default `gemini-3.8-flash`), and set the Windows user/system variable `CONTENT_STUDIO_GEMINI`, then restart the API and worker. Existing `GEMINI_API_KEY`, `GEMINI_KEY`, and `GOOGLE_API_KEY` environment aliases are also supported. The Gemini credential is sent in the provider authorization header and never returned through status or telemetry. There is no automatic provider retry or fallback. Script output must pass the server-side schema, evidence, pacing, and brand checks before it can be saved, and human approval remains required. See [Gemini provider configuration](docs/AI_PROVIDER_CONFIGURATION.md) for model, cost, and smoke-test details.

The normal test suite is offline and blocks unexpected requests to AI-provider hosts. The separate live smoke uses `uv run --locked pytest --run-live-provider-smoke apps/api/tests/test_live_script_provider_smoke.py -q -s`; it first checks the configured Gemini model, then makes one bounded script-generation request and verifies persisted provenance and unapproved status. Do not include secrets in `.env.example`, logs, or test output.

#### Q: Why are there no direct "Publish to YouTube" buttons that upload automatically?
**A:** Under **Invariant 6 (Manual-Publish-First)**, direct social API uploads are intentionally excluded in V1. Social platform APIs often break, revoke developer keys, restrict reach on API-uploaded content, or encourage unattended auto-posting. The studio uses one-click authenticated browser launchers and formatted clipboard copy tools, ensuring the creator always maintains full control.

#### Q: Can I manage multiple channels or niches in one studio?
**A:** Under **Invariant 1 & 2**, the studio is strictly single-niche and single-brand. To run a second brand or niche, clone the repository into a separate folder (e.g. `studio-brand-two`) with its own dedicated SQLite database.

---

## 11. License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

Developed with precision by **Hexabyte Technologies** for evidence-driven AI content creation.
