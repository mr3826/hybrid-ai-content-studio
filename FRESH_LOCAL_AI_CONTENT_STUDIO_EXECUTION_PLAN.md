# Fresh Local AI Content Studio
## Master Coding-Agent Execution Prompt — Phase-by-Phase

**Project:** Greenfield local-first AI-assisted content studio  
**Repository:** Brand-new public GitHub repository  
**CI/CD:** Out of scope  
**Publishing:** Manual in V1  
**Channel model:** One niche, one brand, one channel identity across YouTube/Facebook/Instagram/TikTok  
**Architecture:** Independent feature engines with stable contracts  
**Previous Milestone A:** Do not reuse it.

---

# 1. Mission

Build a local web application that converts niche-specific signals into original, brand-consistent content packages.

The application must:

1. Work with **one niche only**.
2. Maintain **one brand voice, audience, tone, vocabulary, visual identity, and editorial policy** across daily content.
3. Treat RSS, Trends, Niche Guard, Brand, Research, Originality, AI, Content, Media, Export, Analytics, and Cleanup as independent Engines.
4. Give each Engine its own:
   - manifest/version;
   - rules;
   - configuration;
   - adapters;
   - input/output contracts;
   - tests;
   - logs;
   - health checks;
   - explainability.
5. Allow one Engine to be improved without rewriting unrelated Engines.
6. Use AI to assist research/production, not to produce generic source summaries.
7. Require human approval before expensive production and before export.
8. Produce scripts, scenes, voice, subtitles, media, metadata, and export packages.
9. Provide one-click buttons that open the configured YouTube, Facebook, Instagram, and TikTok channel/upload pages in the normal browser.
10. Keep platform uploads manual in V1.
11. Track manual publication state/URLs.
12. Track performance manually/CSV before adding analytics APIs.
13. Track AI/media costs from day one.
14. Include storage cleanup, retention, backup, and recovery.
15. Never depend on n8n.
16. Never reuse the previous infrastructure/codebase or Git history.

---

# 2. Product Philosophy

Do not build:

```text
RSS → summarize → AI voice → generic video → auto-post at scale
```

Build:

```text
Niche Sources
    ↓
Independent Discovery Engines
    ↓
Opportunity Ranking
    ↓
Research / Evidence
    ↓
Original Test / Insight / Comparison
    ↓
Human Editorial Decision
    ↓
Brand-Constrained AI Production
    ↓
Preview + QC
    ↓
Export Package
    ↓
Open Platform in Browser
    ↓
Manual Upload
    ↓
Performance Feedback
```

Every publishable piece should add original value such as:

```text
test
benchmark
comparison
workflow
before/after result
implementation attempt
multi-source synthesis
original framework
chart/data analysis
practical tutorial
failure analysis
```

---

# 3. Mandatory Coding-Agent Skills

Use the **Jeff Allan Claude Skills full-stack skill set** while implementing this project.

Reference:

https://jeffallan.github.io/claude-skills/skills-guide/

The guide's full-feature workflow combines feature definition, architecture, full-stack/framework implementation, testing, code review, and security review.

Use these skills when available and relevant:

```text
Feature Forge
Architecture Designer
Fullstack Guardian
Next.js Developer
TypeScript Pro
FastAPI Expert
Python Pro
API Designer
Prompt Engineer
Test Master
Playwright Expert
Code Reviewer
Security Reviewer
Debugging Wizard
The Fool
Common Ground
Code Documenter
```

For new features:

```text
Feature Forge
→ Architecture Designer
→ Fullstack Guardian + framework/language skills
→ Test Master + Playwright Expert where applicable
→ Code Reviewer
→ Security Reviewer
```

For important decisions:

```text
Common Ground
→ The Fool
→ Architecture Designer
```

For bugs:

```text
Debugging Wizard
→ Fullstack Guardian + relevant framework skill
→ Test Master
→ Code Reviewer
```

Do not invoke every skill mechanically for tiny tasks. Use the appropriate subset.

No CI/CD skill output should create GitHub Actions because CI/CD is explicitly out of scope.

---

# 4. Greenfield Rule

Start from zero.

Do not:

```text
copy previous n8n repository
import old migrations
reuse old Docker/AWS setup
reuse old workflow JSON
reuse old Milestone A reports
continue old Git history
```

Reimplement useful concepts only after designing them for this product.

---

# 5. Brand-New Public Git Repository

Preferred repository name:

```text
hybrid-ai-content-studio
```

If unavailable:

```text
hybrid-ai-content-studio-2026
```

Use GitHub CLI if authenticated:

```bash
gh auth status
git init
gh repo create hybrid-ai-content-studio --public --source=. --remote=origin
```

Required initial files:

```text
README.md
LICENSE
.gitignore
.env.example
AGENTS.md
docs/PRODUCT_SPEC.md
docs/ARCHITECTURE.md
docs/ENGINE_SYSTEM.md
docs/BRAND_SYSTEM.md
docs/DATA_RETENTION.md
docs/PHASE_STATUS.md
docs/DECISIONS.md
```

Recommended license:

```text
MIT
```

Never commit:

```text
.env
.env.local
API keys
cookies/browser profiles
OAuth tokens
SQLite runtime database
videos/audio
temporary media
cache
model files
exports
backups
```

Suggested `.gitignore`:

```gitignore
.env
.env.*
!.env.example

data/
runtime/
cache/
tmp/
exports/
backups/

*.db
*.sqlite
*.sqlite3
*.mp4
*.mov
*.wav
*.mp3

node_modules/
.next/
.venv/
__pycache__/
playwright/.auth/
```

Do not create:

```text
.github/workflows/*
GitHub Actions
deployment/release pipelines
```

Each implementation phase ends with one coherent commit.

---

# 6. Technology Stack

## Frontend

```text
Next.js
TypeScript
App Router
React
```

## Backend

```text
FastAPI
Python
Pydantic
SQLAlchemy
Alembic
```

## Database

```text
SQLite
```

This is initially a single-user local application. Do not introduce PostgreSQL until there is a real multi-user/remote need.

Use SQLite WAL mode where appropriate.

Keep repository/data-access interfaces clean enough to migrate to PostgreSQL later.

## Worker

Separate local Python worker for:

```text
AI requests
source extraction
TTS
subtitle alignment
FFmpeg
media processing
long-running Engine jobs
```

Never run long FFmpeg renders synchronously inside an HTTP request.

## Testing

```text
pytest
frontend unit tests
Playwright
```

Bind frontend/backend to localhost by default.

---

# 7. Repository Structure

```text
/
├─ README.md
├─ LICENSE
├─ AGENTS.md
├─ .env.example
├─ .gitignore
│
├─ apps/
│  ├─ web/
│  │  ├─ app/
│  │  ├─ components/
│  │  ├─ lib/
│  │  └─ tests/
│  │
│  └─ api/
│     ├─ app/
│     │  ├─ api/
│     │  ├─ core/
│     │  ├─ domain/
│     │  ├─ models/
│     │  ├─ repositories/
│     │  ├─ services/
│     │  ├─ jobs/
│     │  └─ engines/
│     │     ├─ core/
│     │     ├─ rss/
│     │     ├─ trends/
│     │     ├─ niche_guard/
│     │     ├─ opportunity/
│     │     ├─ brand/
│     │     ├─ research/
│     │     ├─ originality/
│     │     ├─ ai/
│     │     ├─ content/
│     │     ├─ media/
│     │     ├─ export/
│     │     ├─ analytics/
│     │     └─ cleanup/
│     └─ tests/
│
├─ worker/
│  ├─ worker.py
│  ├─ jobs/
│  └─ tests/
│
├─ config/
│  ├─ brand.example.yaml
│  ├─ niche.example.yaml
│  ├─ platforms.example.yaml
│  └─ engines/
│
├─ prompts/
│  ├─ research/
│  ├─ originality/
│  ├─ script/
│  ├─ metadata/
│  └─ brand-review/
│
├─ data/
│  └─ .gitkeep
│
├─ docs/
│  ├─ PRODUCT_SPEC.md
│  ├─ ARCHITECTURE.md
│  ├─ ENGINE_SYSTEM.md
│  ├─ BRAND_SYSTEM.md
│  ├─ DATA_RETENTION.md
│  ├─ PHASE_STATUS.md
│  ├─ DECISIONS.md
│  ├─ MANUAL_PUBLISHING.md
│  └─ TESTING.md
│
└─ scripts/
   ├─ dev.ps1
   ├─ dev.sh
   ├─ test.ps1
   ├─ test.sh
   ├─ backup.ps1
   └─ cleanup.ps1
```

Windows is a first-class development environment.

---

# 8. Single-Niche Contract

There is exactly **one active niche**.

Do not create:

```text
multi-niche switcher
workspace selector
multi-tenant channel manager
per-project niche override
```

First-run setup defines the niche.

Suggested default direction, if not changed by the owner:

```text
AI automation, AI workflows, coding agents, and practical AI tools
tested on real problems
```

Do not hardcode that into business logic.

Store one `NicheProfile`:

```yaml
id: primary
name: ""
one_sentence_definition: ""
audience: ""
audience_regions: []
primary_problems: []
allowed_topics: []
adjacent_topics: []
blocked_topics: []
must_have_signals: []
negative_keywords: []
preferred_source_types: []
content_pillars: []
commercial_intent_topics: []
evergreen_topics: []
```

Every discovery result must pass the Niche Guard Engine.

Output:

```json
{
  "in_niche": true,
  "relevance_score": 0,
  "pillar": "",
  "matched_rules": [],
  "rejection_reasons": []
}
```

Trending but off-niche items cannot proceed automatically.

---

# 9. Brand DNA

There is exactly one `BrandProfile`.

All daily content inherits it.

```yaml
brand_name: ""
brand_promise: ""
audience: ""

tone:
  - evidence-driven
  - concise
  - practical

voice_rules: []
preferred_vocabulary: []
avoid_vocabulary: []
banned_cliches: []
claim_rules: []
cta_style: ""
humor_policy: ""
controversy_policy: ""
sponsor_policy: ""
affiliate_disclosure_style: ""

visual_identity:
  primary_font: ""
  secondary_font: ""
  caption_style: ""
  logo_path: ""
  intro_rule: ""
  outro_rule: ""
  thumbnail_rules: []

platform_adaptations:
  youtube: {}
  facebook: {}
  instagram: {}
  tiktok: {}
```

Support Brand Exemplars:

```text
approved hooks
approved scripts
approved captions
do examples
don't examples
```

Store recent approved/published content so the system can detect:

```text
repeated hooks
repeated topics
repeated angles
repeated CTAs
tone drift
```

Every script/metadata package must receive:

```json
{
  "on_brand": true,
  "tone_score": 0,
  "niche_score": 0,
  "repetition_score": 0,
  "violations": [],
  "suggested_fixes": []
}
```

A failed Brand QA cannot move to final approval without explicit user override.

---

# 10. Engine Architecture — Critical Requirement

An Engine is an independently testable subsystem with a stable contract.

The UI may orchestrate Engines but must not depend on their private implementation.

Every Engine must include:

```text
manifest.yaml
README.md
engine.py
contracts.py
rules.yaml or typed config
tests/
adapters/ where applicable
prompts/ where applicable
```

Example:

```text
apps/api/app/engines/rss/
├─ manifest.yaml
├─ README.md
├─ engine.py
├─ contracts.py
├─ rules.yaml
├─ adapters/
│  ├─ generic_rss.py
│  └─ atom.py
└─ tests/
```

Example manifest:

```yaml
id: rss
name: RSS Discovery Engine
version: 1.0.0
enabled: true

inputs:
  - SourceFeed

outputs:
  - DiscoveryCandidate

dependencies:
  - niche_guard

triggers:
  - manual
  - local_schedule_optional

supports:
  dry_run: true
  explain: true
  health_check: true
```

Base interface concept:

```python
class Engine:
    id: str
    version: str

    def validate_config(self) -> None: ...
    def health(self) -> EngineHealth: ...
    async def run(self, context: EngineContext) -> EngineResult: ...
    async def dry_run(self, context: EngineContext) -> EngineResult: ...
    def explain(self, result_id: str) -> EngineExplanation: ...
```

Rules must live with the Engine.

Example:

```text
RSS freshness threshold → rss/rules.yaml
Trend weights → trends/rules.yaml
Brand vocabulary → brand configuration
```

Every Engine run stores:

```text
engine_id
engine_version
run_id
started_at
ended_at
status
input_count
output_count
rejected_count
error_count
cost
summary
```

Create `/engines` UI:

```text
RSS Engine
Enabled
Healthy
Last run: ...
Candidates: ...
Rejected: ...

[Run]
[Dry Run]
[Configure]
[View Rules]
[Logs]
```

---

# 11. Required Engine Catalog

```text
01 RSS Engine
02 Trends Engine
03 Niche Guard Engine
04 Opportunity Scoring Engine
05 Brand Engine
06 Research Engine
07 Originality Engine
08 AI Provider Engine
09 Content Engine
10 Media Engine
11 Export Engine
12 Analytics Engine
13 Cleanup Engine
```

Never collapse them into one giant workflow.

---

# 12. RSS Engine

Purpose: discover fresh niche-specific candidates from configured RSS/Atom feeds.

Source fields:

```text
name
feed URL
source category
trust weight
enabled
language
last success
last failure
average item rate
```

Workflow:

```text
Feeds
 ↓
Fetch independently
 ↓
Parse
 ↓
Normalize
 ↓
Canonical URL
 ↓
Hash
 ↓
Deduplicate
 ↓
Freshness rules
 ↓
Niche Guard
 ↓
Source trust
 ↓
DiscoveryCandidate
```

RSS must work with **zero AI calls**.

Rules include:

```text
max age
minimum title quality
negative keywords
language
canonical URL handling
duplicate hash
source trust
niche keyword pre-filter
per-source failure isolation
```

Deduplicate using:

```text
exact URL
canonical URL
normalized title hash
content fingerprint
near-title similarity
```

If multiple feeds report the same story, preserve:

```text
source_count
source_list
first_seen_at
last_seen_at
```

Output:

```json
{
  "candidate_id": "",
  "source_type": "rss",
  "title": "",
  "url": "",
  "summary": "",
  "published_at": "",
  "first_seen_at": "",
  "source_count": 1,
  "sources": [],
  "niche_pre_score": 0,
  "signals": {}
}
```

---

# 13. Trends Engine

Purpose: identify what is gaining attention **inside the configured niche**.

Do not depend on one fragile external provider.

Architecture:

```text
Trends Engine
├─ RSS velocity adapter
├─ cross-source frequency adapter
├─ configured-source momentum adapter
├─ manual signal adapter
└─ future external adapters
```

V1 must work without a paid Trends API.

Use:

```text
independent source count
mention velocity
first-seen recency
entity/topic frequency
keyword momentum
source-authority mix
historical baseline
manual boost
manual suppress
```

Future adapter contract may support:

```text
search trends
Reddit
Hacker News
GitHub
YouTube discovery
news search
social listening
```

Do not implement unstable scraping merely to tick a feature box.

Output:

```json
{
  "topic_key": "",
  "trend_score": 0,
  "velocity_score": 0,
  "cross_source_score": 0,
  "freshness_score": 0,
  "authority_score": 0,
  "signals": [],
  "explanation": ""
}
```

Explainability example:

```text
5 independent sources in 2 hours
3 high-trust sources
mentions +220% versus baseline
first detected 47 minutes ago
```

No unexplained magic score.

---

# 14. Opportunity Engine

Rank for business/content value, not only virality.

Initial editable weights:

```text
Niche fit                       20
Original test/value potential  20
Audience/search usefulness     15
Trend strength                  15
Evergreen value                 10
Commercial/affiliate fit        10
Story/video potential            5
Production effort/cost           5
```

Output:

```json
{
  "total_score": 0,
  "components": {},
  "recommended_action": "review|watch|skip",
  "explanation": []
}
```

User approval remains mandatory.

---

# 15. Opportunity Feed UI

Route:

```text
/opportunities
```

Card:

```text
Title
Sources
Age
Niche pillar

Opportunity score
Trend score
Originality potential
Evergreen value
Commercial relevance

Why selected
Why trending
Suggested original angle

[Research]
[Watch]
[Reject]
```

Filters:

```text
Today
Last 24h
High opportunity
Trending
Evergreen
Research ready
Rejected
```

Optimize for reviewing 10–30 candidates quickly.

---

# 16. Research Engine

Workflow:

```text
Approved candidate
 ↓
Acquire source
 ↓
Clean content
 ↓
Claims/facts
 ↓
Dates/numbers/entities
 ↓
Supporting sources
 ↓
Contradictions
 ↓
Uncertainty
 ↓
Research Packet
```

Packet:

```json
{
  "topic": "",
  "summary": "",
  "primary_sources": [],
  "supporting_sources": [],
  "facts": [],
  "numbers": [],
  "dates": [],
  "entities": [],
  "claims": [],
  "contradictions": [],
  "uncertain_claims": [],
  "things_not_to_claim": []
}
```

Every factual claim should be traceable to a source.

Current claims must not rely only on model memory.

---

# 17. Originality Engine

Mandatory.

Question:

```text
What can this channel add that the source itself did not?
```

Allowed outputs:

```text
Original experiment
Tool test
Benchmark
Cost comparison
Workflow demonstration
Before/after
Implementation attempt
Multi-source synthesis
Original framework
Original chart
Practical tutorial
Failure analysis
Clearly labeled opinion
```

Output:

```json
{
  "originality_score": 0,
  "recommended_original_value_type": "",
  "test_plan": [],
  "evidence_needed": [],
  "expected_cost": 0,
  "expected_time": "",
  "publish_without_original_work": false
}
```

Generic source summary defaults to:

```text
publish_without_original_work = false
```

---

# 18. Experiment Workspace

Route:

```text
/projects/:id/experiment
```

Fields:

```text
Question
Hypothesis
Method
Dataset/sample
Tools/models tested
Parameters
Results
Failures
Latency
Cost
Screenshots
Files
Notes
Conclusion
```

Allow attachments:

```text
screenshots
JSON
CSV
images
screen recordings
terminal output
code snippets
```

Original evidence feeds Content Engine.

---

# 19. AI Provider Engine

No scattered Gemini/Qwen calls.

Adapters:

```text
Gemini
Qwen
```

Contract:

```python
generate_text(...)
generate_structured(...)
analyze(...)
```

Configuration:

```text
primary provider
fallback provider
model per task
temperature per task
max output
retry rules
cost metadata
```

Fallback only for technical/provider/schema failure, not to manufacture unsupported facts.

Store per call:

```text
provider
model
purpose
input/output usage
reported/estimated cost
latency
success
prompt version
```

---

# 20. Content Engine

Inputs:

```text
Research Packet
Original Evidence
Brand Profile
Niche Profile
Brand Exemplars
Recent Content Memory
Content Format
```

Formats:

```text
Short Vertical Video
Long-form YouTube Script
Social Companion Post
```

Same niche and brand only.

MasterContent:

```json
{
  "project_id": "",
  "topic": "",
  "content_pillar": "",
  "original_value": "",
  "format": "short",
  "hook": "",
  "narration": "",
  "sections": [],
  "scenes": [],
  "cta": "",
  "sources_used": [],
  "claims_used": [],
  "brand_review": {},
  "platform_metadata": {
    "youtube": {},
    "facebook": {},
    "instagram": {},
    "tiktok": {}
  }
}
```

---

# 21. Script Studio

Route:

```text
/projects/:id/script
```

Editable blocks:

```text
Hook
Context
Test/Method
Evidence
Result
Interpretation
CTA
```

Actions:

```text
Regenerate selected section
Shorten
Expand
Make clearer
Make more evidence-driven
Restore revision
```

Store revisions.

Do not regenerate whole content because one block needs correction.

---

# 22. Daily Brand Consistency

Every generated content object runs through:

```text
Niche Guard
+ Brand Engine
+ Content Memory
```

Checks:

```text
in niche?
target audience?
tone?
banned wording?
unsupported hype?
repeated hook?
repeated topic too soon?
CTA consistent?
platform caption consistent?
visual rules consistent?
```

Approved content becomes future brand/context memory.

---

# 23. Scene Studio

Route:

```text
/projects/:id/scenes
```

Each scene:

```text
index
start/end estimate
narration
on-screen text
visual type
visual source
visual prompt
transition
evidence reference
status
```

Visual sources:

```text
screen recording
user media
generated image
generated video
source screenshot where appropriate
chart
diagram
motion graphic
text card
B-roll
```

Prefer real demonstrations/evidence where possible.

---

# 24. Media Engine

Own:

```text
TTS
audio normalization
subtitle alignment
BGM
scene composition
FFmpeg
ffprobe validation
preview render
final render
```

Provider adapters must be replaceable.

No provider should be required for unrelated app features.

---

# 25. Voice Studio

Support:

```text
voice
speed
pauses
pronunciation overrides
sentence/segment regeneration
```

Avoid regenerating entire narration for one sentence.

---

# 26. Subtitle Studio

Support:

```text
word/sentence timestamps
line breaks
caption preview
Brand Profile caption styling
manual fixes
re-alignment
```

Do not let an LLM guess timestamps if actual alignment is available.

---

# 27. BGM

Use only licensed/pre-approved tracks.

Store:

```text
track
license/source
mood
energy
vocals
approved
```

No arbitrary copyrighted music downloading.

---

# 28. Preview + QC

Route:

```text
/projects/:id/preview
```

Show:

```text
video
duration
resolution
audio/subtitle state
source/evidence coverage
brand score
niche score
originality score
estimated cost
```

Mechanical checks:

```text
valid media
correct orientation
audio exists
no missing scene
duration bounds
black-frame checks
subtitle timing
```

Editorial checks:

```text
brand
niche
evidence
originality
repetition
CTA
```

Require explicit:

```text
Approve Final
```

before export.

---

# 29. Export Engine

No platform publishing API in V1.

Example export:

```text
exports/
└─ 2026-09-27-topic-slug/
   ├─ video/
   │  ├─ final-short.mp4
   │  └─ thumbnail.png
   ├─ youtube/
   │  ├─ title.txt
   │  ├─ description.txt
   │  ├─ hashtags.txt
   │  └─ pinned-comment.txt
   ├─ facebook/
   │  └─ caption.txt
   ├─ instagram/
   │  └─ caption.txt
   ├─ tiktok/
   │  └─ caption.txt
   ├─ sources.md
   └─ manifest.json
```

Manifest includes:

```text
project ID
content hash
generation time
brand version
Engine versions
source list
render checksum
```

---

# 30. Platform Launcher — Mandatory

Visible from:

```text
Dashboard
Ready to Publish
Export page
```

Settings:

```text
Settings → Platforms
```

Store:

```yaml
youtube:
  channel_url: ""
  studio_url: "https://studio.youtube.com/"

facebook:
  channel_url: ""
  publishing_url: ""

instagram:
  channel_url: ""
  publishing_url: ""

tiktok:
  channel_url: ""
  publishing_url: ""
```

UI example:

```text
YouTube
[Copy Title]
[Copy Description]
[Open YouTube Studio]

Facebook
[Copy Caption]
[Open Facebook Page]

Instagram
[Copy Caption]
[Open Instagram]

TikTok
[Copy Caption]
[Open TikTok Upload]
```

Open normal browser/new tab.

Use:

```html
target="_blank"
rel="noopener noreferrer"
```

Do not iframe/embed platform sites by default.

Reasons:

```text
CSP/frame restrictions
authentication complexity
security
existing browser sessions already authenticated
lower maintenance
```

Validate URLs and allow only HTTPS.

---

# 31. Manual Publish Tracking

After upload:

```text
[Mark Published]
```

Store:

```text
platform
published_at
post URL
platform post ID optional
notes
```

Per-platform states:

```text
NOT_READY
READY
PUBLISHED
SKIPPED
```

Do not mark all platforms published together.

---

# 32. Dashboard

Route:

```text
/
```

Display:

```text
Discovery Today
High Opportunity
Researching
In Production
Ready to Publish
Published This Week
Engine Health
AI Spend
Storage Usage
```

Example:

```text
New opportunities       18
Needs review              6
Approved                  3
In production             2
Ready to publish          1
Published today           1

AI spend today          $0.31
Storage                 4.8 GB
```

---

# 33. Analytics Engine

No platform analytics APIs in V1.

Support manual entry and optional CSV-import abstraction.

Per post:

```text
views
likes
comments
shares
saves
watch time
average watch time
completion rate
followers/subscribers gained
link clicks
affiliate clicks
affiliate revenue
platform revenue
capture timestamp
```

Compute:

```text
performance by content pillar
source
hook type
format
duration
original-value type
posting time
cost/content
revenue/content
```

Engine may suggest rule changes but never apply them without approval.

---

# 34. Data Model

Minimum domains:

```text
app_settings
niche_profile
brand_profile
brand_exemplars

engine_manifests
engine_configs
engine_runs

sources
source_items
discovery_candidates
topics
topic_signals
opportunity_scores

research_packets
research_sources
claims

experiments
experiment_results

projects
project_revisions
content_versions
scene_versions

ai_calls
assets
voice_segments
subtitle_segments
render_jobs

export_packages
platform_publications
analytics_snapshots

cleanup_runs
audit_events
```

Preserve Engine/domain boundaries.

---

# 35. Project State Machine

```text
DISCOVERED
WATCHING
APPROVED_FOR_RESEARCH
RESEARCHING
RESEARCH_READY
ORIGINALITY_PLANNED
CONTENT_DRAFT
SCRIPT_REVIEW
SCRIPT_APPROVED
MEDIA_BUILDING
PREVIEW_READY
QC_FAILED
FINAL_APPROVED
EXPORTED
READY_TO_PUBLISH
PARTIALLY_PUBLISHED
PUBLISHED
ARCHIVED
REJECTED
```

Validate transitions.

---

# 36. Local Storage

```text
data/
├─ db/studio.sqlite
├─ sources/
├─ projects/
├─ assets/
├─ voice/
├─ subtitles/
├─ renders/
├─ exports/
├─ cache/
├─ tmp/
└─ backups/
```

Prefer relative paths in DB.

---

# 37. Retention and Deletion

Implement from the beginning.

Defaults:

```text
tmp                         24 hours
cache                       24 hours
failed render temp          3 days
downloaded source media     7 days
unused generated assets     7 days
active-project media        retain
final render                30 days after selected platforms published
exports                     30 days default
SQLite metadata             retain
analytics                   retain
research citations          retain
```

Do not delete referenced files.

Never delete when:

```text
active project references asset
render job needs it
export references it
project is READY_TO_PUBLISH
any platform remains READY
```

Cleanup Engine must support:

```text
dry run
bytes recoverable
exact file preview
cleanup
audit log
```

Deletion is idempotent.

---

# 38. Backup

Create `backup.ps1`.

Back up:

```text
SQLite DB
brand config
niche config
platform URLs
important metadata
```

Do not automatically copy all large media.

Future optional adapters:

```text
S3
Google Drive
external disk
```

No cloud dependency in V1.

---

# 39. Settings

Route:

```text
/settings
```

Sections:

```text
Brand
Niche
Platforms
AI Providers
Media Providers
Engines
Storage & Retention
Backups
Cost Limits
```

Normal operation must not require editing YAML.

---

# 40. Cost Controls

Support:

```text
max AI cost/day
max generation cost/project
max generated video seconds/project
warn before expensive provider call
```

Show estimated project cost before expensive generation.

---

# 41. Explicitly Out of Scope in V1

```text
n8n
AWS deployment
RDS
Redis/Celery cluster
Kubernetes
multi-user auth
multi-niche/channel workspaces
YouTube API uploads
Meta publishing APIs
TikTok Direct Post
social OAuth
business verification workflows
CI/CD
GitHub Actions
mobile app
desktop wrapper
100-post/day publishing
```

---

# 42. Phase Execution Rules

Execute **one phase at a time**.

For every phase:

1. Read `docs/PHASE_STATUS.md`.
2. Review relevant decisions.
3. Use relevant Jeff Allan skills.
4. Implement only the current phase plus unavoidable prerequisites.
5. Add tests.
6. Run tests.
7. Start app when UI is involved.
8. Use Playwright/browser verification for UI workflows.
9. Perform security review.
10. Perform code review.
11. Update docs.
12. Update `PHASE_STATUS.md`.
13. Commit.
14. Move on only when acceptance criteria pass.

Do not report completion when required verification was skipped.

---

# 43. Phase 0 — Greenfield Bootstrap

Tasks:

- [ ] Confirm directory is not old project repo.
- [ ] Create new project.
- [ ] `git init`.
- [ ] Create new public GitHub repo.
- [ ] Add remote.
- [ ] Add MIT license.
- [ ] Add `.gitignore`.
- [ ] Add `.env.example`.
- [ ] Scaffold Next.js/TypeScript.
- [ ] Scaffold FastAPI/Python.
- [ ] Configure SQLite/Alembic.
- [ ] Add health endpoint.
- [ ] Add local start/test scripts.
- [ ] Add docs.
- [ ] Confirm no GitHub Actions.
- [ ] Scan tracked files for secrets.
- [ ] Push first commit.

Acceptance:

```text
fresh Git history
public repository exists
frontend starts
backend starts
GET /health passes
SQLite initializes
no secrets tracked
no CI/CD
```

Commit:

```text
chore: initialize greenfield content studio
```

---

# 44. Phase 1 — Single Brand/Niche Foundation

Tasks:

- [ ] NicheProfile.
- [ ] BrandProfile.
- [ ] Brand Exemplars.
- [ ] AppSettings.
- [ ] PlatformSettings.
- [ ] migrations.
- [ ] first-run setup.
- [ ] niche required before discovery.
- [ ] brand required before generation.
- [ ] Settings UI.
- [ ] channel/upload URLs.
- [ ] URL validation.
- [ ] persistence tests.
- [ ] brand/niche config export/import.

Acceptance:

```text
one niche
one brand
four platform URLs
survive restart
no second workspace/niche can be created
```

Commit:

```text
feat: add single-niche brand foundation
```

---

# 45. Phase 2 — Engine Framework

Tasks:

- [ ] Engine base contract.
- [ ] EngineContext.
- [ ] EngineResult.
- [ ] EngineHealth.
- [ ] manifest schema.
- [ ] rules/config loader.
- [ ] run logs.
- [ ] registry.
- [ ] dependency validation.
- [ ] dry run.
- [ ] explainability.
- [ ] `/engines` UI.
- [ ] Engine run/detail UI.
- [ ] reference Engine.
- [ ] lifecycle unit tests.

Acceptance:

```text
register
configure
run
dry-run
health-check
log
explain
```

without page-specific coupling.

Commit:

```text
feat: add modular engine framework
```

---

# 46. Phase 3 — Niche Guard + Brand Engines

Niche Guard:

- [ ] keyword rules.
- [ ] topic taxonomy.
- [ ] adjacent topics.
- [ ] blocked topics.
- [ ] negative signals.
- [ ] deterministic relevance.
- [ ] explain rejection.

Brand Engine:

- [ ] rule loader.
- [ ] exemplar retrieval.
- [ ] tone evaluation.
- [ ] repetition checks.
- [ ] CTA rules.
- [ ] vocabulary.
- [ ] banned clichés.
- [ ] claim style.
- [ ] Brand QA output.

Acceptance test cases must cover:

```text
in niche
off niche
on brand
brand violation
```

Commit:

```text
feat: add niche guard and brand engines
```

---

# 47. Phase 4 — RSS Engine

Tasks:

- [ ] Source CRUD.
- [ ] RSS/Atom adapters.
- [ ] timeout/retry.
- [ ] feed failure isolation.
- [ ] normalization.
- [ ] canonical URLs.
- [ ] exact dedupe.
- [ ] near-title dedupe.
- [ ] first/last seen.
- [ ] cross-source grouping.
- [ ] freshness.
- [ ] Niche Guard integration.
- [ ] trust score.
- [ ] logs.
- [ ] rules editor.
- [ ] health.
- [ ] dry run.
- [ ] source UI.
- [ ] manual Refresh.
- [ ] 100+ fixture-item test.
- [ ] real-feed smoke test.

Acceptance:

```text
re-run produces no duplicate candidates
bad feed isolated
old content rejected
off-niche rejected
cross-source copies grouped
reasons explainable
```

Commit:

```text
feat: add rss discovery engine
```

---

# 48. Phase 5 — Trends Engine

Tasks:

- [ ] TopicKey normalization.
- [ ] mention frequency.
- [ ] velocity.
- [ ] source diversity.
- [ ] authority mix.
- [ ] baseline comparison.
- [ ] manual boost/suppress.
- [ ] explainable score.
- [ ] history.
- [ ] adapter interface.
- [ ] RSS-derived adapter.
- [ ] no RSS internal coupling.
- [ ] rules editor.
- [ ] Trends UI.
- [ ] regression fixtures.

Acceptance:

The Engine ranks niche topics without a paid trend API and explains every score.

Commit:

```text
feat: add independent trends engine
```

---

# 49. Phase 6 — Opportunity Engine + Feed

Tasks:

- [ ] weighted scoring.
- [ ] editable weights.
- [ ] combine niche/trend/source/originality potential.
- [ ] manual review states.
- [ ] `/opportunities`.
- [ ] sorting/filtering.
- [ ] Watch.
- [ ] Reject reason.
- [ ] Approve for research.
- [ ] decision history.
- [ ] repeated-topic warning.

Commit:

```text
feat: add opportunity ranking and review feed
```

---

# 50. Phase 7 — Research Engine

Tasks:

- [ ] selected-source fetch.
- [ ] HTML cleanup.
- [ ] source metadata preservation.
- [ ] claim/fact schema.
- [ ] supporting-source input.
- [ ] uncertainty tags.
- [ ] claim/source links.
- [ ] Research UI.
- [ ] manual fact corrections.
- [ ] revisions.

Acceptance:

Every factual claim can point to a source or is explicitly uncertain/manual.

Commit:

```text
feat: add evidence-based research engine
```

---

# 51. Phase 8 — AI Provider Engine

Tasks:

- [ ] Gemini adapter.
- [ ] Qwen adapter.
- [ ] config UI.
- [ ] structured output validation.
- [ ] bounded retry.
- [ ] technical fallback.
- [ ] usage/cost.
- [ ] prompt versions.
- [ ] secret redaction.
- [ ] mock providers.

Acceptance:

Switching provider requires no Research/Content Engine code change.

Commit:

```text
feat: add pluggable ai provider engine
```

---

# 52. Phase 9 — Originality Engine + Experiment Workspace

Tasks:

- [ ] originality scoring.
- [ ] original-value suggestion.
- [ ] experiment plan.
- [ ] experiment records.
- [ ] result entry.
- [ ] attachments.
- [ ] cost/result tables.
- [ ] screenshot/evidence attachments.
- [ ] generic-summary guard.
- [ ] explicit override with reason.

Acceptance:

Generic source summary is blocked until original value is defined or the user records an override.

Commit:

```text
feat: add originality engine and experiment workspace
```

---

# 53. Phase 10 — Content + Script Studio

Tasks:

- [ ] MasterContent schema.
- [ ] Short generator.
- [ ] Long-form generator.
- [ ] platform metadata.
- [ ] section-level generation.
- [ ] section regeneration.
- [ ] version history.
- [ ] recent-content memory.
- [ ] Brand QA.
- [ ] Niche Guard.
- [ ] unsupported-claim check.
- [ ] Script UI.
- [ ] script approval.

Cannot approve script if:

```text
off niche
Brand QA fails
unsupported facts exist
```

unless explicit override is logged.

Commit:

```text
feat: add brand-constrained content studio
```

---

# 54. Phase 11 — Scene + Asset Studio

Tasks:

- [ ] scene schema/editor.
- [ ] uploads.
- [ ] asset library.
- [ ] tags/search.
- [ ] screen recordings.
- [ ] charts/images.
- [ ] generated-media adapter contract.
- [ ] evidence references.
- [ ] scene preview states.

Acceptance:

A project can be fully storyboarded with user/real assets even when no paid generator is configured.

Commit:

```text
feat: add scene and asset studio
```

---

# 55. Phase 12 — Voice, Subtitle + Media Engine

Tasks:

- [ ] TTS adapter.
- [ ] one working TTS provider.
- [ ] voice segments.
- [ ] segment regeneration.
- [ ] subtitle alignment.
- [ ] subtitle editor.
- [ ] BGM library.
- [ ] FFmpeg worker.
- [ ] render states.
- [ ] ffprobe QC.
- [ ] preview render.
- [ ] final render.
- [ ] retry/crash handling.
- [ ] temp cleanup.

Acceptance:

A script becomes a valid local MP4 without cloud infrastructure.

Commit:

```text
feat: add local media production engine
```

---

# 56. Phase 13 — Preview + Final QC

Tasks:

- [ ] player.
- [ ] media health.
- [ ] Brand score.
- [ ] Niche score.
- [ ] Originality score.
- [ ] evidence coverage.
- [ ] repetition warnings.
- [ ] cost.
- [ ] final approval.
- [ ] selective re-render.

No export without:

```text
FINAL_APPROVED
```

Commit:

```text
feat: add preview and final quality gate
```

---

# 57. Phase 14 — Export + Platform Launcher

Tasks:

- [ ] export package.
- [ ] platform text files.
- [ ] source manifest.
- [ ] checksums.
- [ ] Copy buttons.
- [ ] Open YouTube.
- [ ] Open Facebook.
- [ ] Open Instagram.
- [ ] Open TikTok.
- [ ] configured URLs.
- [ ] HTTPS validation.
- [ ] new-tab behavior.
- [ ] publish checklist.
- [ ] manual publication records.

Acceptance:

From one screen the user can:

```text
copy YT title/description → open YouTube Studio
copy FB caption → open Facebook
copy IG caption → open Instagram
copy TikTok caption → open TikTok upload
```

and record each platform independently.

Commit:

```text
feat: add export packages and platform launcher
```

---

# 58. Phase 15 — Analytics + Feedback

Tasks:

- [ ] manual metrics.
- [ ] snapshots.
- [ ] CSV adapter abstraction.
- [ ] performance dashboard.
- [ ] pillar/hook/source/originality analysis.
- [ ] cost/content.
- [ ] revenue/content.
- [ ] suggestions.
- [ ] approval before rule change.

Commit:

```text
feat: add manual analytics and feedback engine
```

---

# 59. Phase 16 — Cleanup + Backup + Reliability

Tasks:

- [ ] Cleanup Engine.
- [ ] dry run.
- [ ] retention.
- [ ] reference-safe deletion.
- [ ] storage dashboard.
- [ ] backup.
- [ ] restore procedure.
- [ ] DB integrity.
- [ ] job recovery.
- [ ] orphan worker cleanup.
- [ ] log rotation.
- [ ] error UI.

Acceptance:

```text
active content cannot be deleted
test backup restores correctly
worker crash does not corrupt state
disk use remains bounded
```

Commit:

```text
feat: add local retention backup and recovery
```

---

# 60. Phase 17 — Full Product Verification

Use integration tests and Playwright.

E2E:

```text
first run
→ niche
→ brand
→ platform URLs
→ RSS sources
→ RSS Engine
→ Trends Engine
→ opportunity
→ research
→ originality/experiment
→ script
→ approval
→ scenes
→ voice/subtitles
→ render
→ final approval
→ export
→ platform launcher
→ manual publication record
→ analytics
→ feedback
```

Verify:

```text
restart persistence
brand consistency
niche guard
dedupe
Engine isolation
provider fallback
no secrets in logs
safe cleanup
backup/restore
```

Create:

```text
FINAL_VERIFICATION_REPORT.md
```

Commit:

```text
test: certify local content studio workflow
```

---

# 61. Engine Isolation Tests

Mandatory:

## RSS isolation

Breaking RSS adapter must not break:

```text
Trends historical data
existing Research projects
Media
Export
```

## Trends isolation

Changing Trend weights must not change:

```text
RSS parsing
Brand rules
Media
```

## Brand isolation

Changing Brand tone must not change:

```text
RSS storage
Trend calculation
```

## AI provider isolation

Switch Gemini/Qwen without editing:

```text
Research Engine
Content Engine UI
DB schema
```

## Media provider isolation

Changing TTS must not affect:

```text
research
opportunity scoring
platform launcher
```

Document unavoidable coupling.

---

# 62. Engine Rule Versioning

Every ruleset:

```text
version
updated_at
reason
```

Preserve history.

Export manifest includes relevant:

```text
RSS Engine version
Trends Engine version
Opportunity Engine version
Brand version
Content Engine version
```

---

# 63. Local Observability

No enterprise stack.

Track:

```text
run ID
Engine
project
duration
status
cost
error
```

Dashboard:

```text
Engine Health
Recent Failures
Pending Jobs
AI Spend
Disk Usage
```

Never log secrets.

---

# 64. Local Security

Requirements:

```text
localhost bind
restricted CORS
path traversal prevention
upload type validation
safe subprocess list arguments
FFmpeg/ffprobe timeout
safe temp directories
upload limits
secrets not returned to frontend after save
```

Run Security Reviewer on media/file features.

---

# 65. UX Principle

User time belongs on:

```text
topic choice
original value
conclusion correctness
final quality
```

Not:

```text
file moving
prompt JSON
manual subtitle rebuilds
finding captions
renaming generated assets
```

Prefer actions:

```text
Approve
Reject
Regenerate Section
Open Source
Attach Result
Render Preview
Copy
Open Platform
Mark Published
```

---

# 66. Required Documentation

Maintain `docs/PHASE_STATUS.md`:

```markdown
| Phase | Status | Commit | Tests | Blocker |
|---|---|---|---|---|
```

Statuses:

```text
NOT_STARTED
IN_PROGRESS
PASS
PARTIAL
BLOCKED
FAIL
```

Maintain `docs/DECISIONS.md` for:

```text
SQLite choice
local-first architecture
manual publishing
browser launcher
Engine isolation
one-niche rule
```

Maintain `docs/ENGINE_SYSTEM.md` with every Engine's:

```text
purpose
inputs
outputs
rules
dependencies
extension points
tests
```

---

# 67. Coding-Agent Phase Report

After each phase:

```text
PHASE:
STATUS:

Implemented:
-

Files changed:
-

Tests:
-

Manual/browser verification:
-

Known limitations:
-

Architecture concerns:
-

Security concerns:
-

Next phase:
-

Commit:
```

Never report complete when acceptance tests were skipped.

---

# 68. First Execution Boundary

Execute **Phase 0 only** first.

Do not begin Phase 1 unless all Phase 0 acceptance criteria pass.

Phase 0 output must include:

```text
public repository URL
initial commit SHA
frontend local URL
backend local URL
health result
SQLite initialization result
secret scan result
confirmation no CI/CD exists
```

---

# 69. V1 Definition of Done

The application is V1-complete when the user can:

```text
1. Open the local application
2. See one niche and one brand
3. Refresh RSS and Trends Engines
4. Understand why topics rank
5. Approve a topic
6. Build traceable research
7. Add original test/insight
8. Generate brand-consistent content
9. Edit/approve script
10. Build scenes/assets
11. Generate voice/subtitles
12. Render and preview
13. Pass QC
14. Export package
15. Copy metadata
16. Open each platform/channel page with one click
17. Upload manually
18. Mark each platform published
19. Record metrics
20. Review feedback
21. Safely clean unused media
22. Back up metadata
```

Preserve these architectural invariants:

```text
ONE NICHE
ONE BRAND
LOCAL-FIRST
ENGINE-BASED
HUMAN-APPROVED
MANUAL-PUBLISH-FIRST
COST-AWARE
EVIDENCE-DRIVEN
NO N8N
NO CI/CD
```
