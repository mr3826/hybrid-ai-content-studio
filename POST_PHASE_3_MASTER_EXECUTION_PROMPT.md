# Post-Phase-3 Master Execution Prompt
## Evidence-Driven AI Creator Studio — End-to-End Agent Plan

**Current baseline:** Phase 3 is implemented.  
**Goal:** Audit/retrofit Phases 1–3, then execute the project through V1 completion.  
**Product:** Local-first, one-niche, one-brand Creator Operating System.  
**Publishing:** Manual-first.  
**Repository:** Continue the current fresh public GitHub repository.  
**CI/CD:** Out of scope.  
**Core principle:** Build for content-market fit, originality, evidence, and creator efficiency—not maximum automation.

---

# 1. Mandatory Skill Set

Use the **Jeff Allan Claude Skills full-stack skill set** throughout this project.

Reference:
https://jeffallan.github.io/claude-skills/skills-guide/

Use the relevant skills for each phase, especially:

- Feature Forge
- Architecture Designer
- Fullstack Guardian
- Next.js Developer
- TypeScript Pro
- FastAPI Expert
- Python Pro
- SQL Pro
- API Designer
- Prompt Engineer
- Test Master
- Playwright Expert
- Code Reviewer
- Debugging Wizard
- Security Reviewer
- Code Documenter
- Common Ground
- The Fool

Recommended feature workflow:

```text
Feature Forge
→ Architecture Designer
→ Fullstack Guardian + framework/language skills
→ Test Master + Playwright Expert where relevant
→ Code Reviewer
→ Security Reviewer
```

For major product/architecture decisions:

```text
Common Ground
→ The Fool
→ Architecture Designer
```

For bugs:

```text
Debugging Wizard
→ relevant implementation skill
→ Test Master
→ Code Reviewer
```

Do not create CI/CD or GitHub Actions.

---

# 2. Product Invariants

Keep these throughout the project:

```text
ONE NICHE
ONE BRAND
ONE CREATOR WORKSPACE
LOCAL-FIRST
ENGINE-BASED
EVIDENCE-DRIVEN
HUMAN-APPROVED
MANUAL-PUBLISH-FIRST
COST-AWARE
NO N8N
NO SOCIAL PUBLISHING API IN V1
NO CI/CD
```

The app is not an AI mass-posting bot.

It is an **Evidence-Driven AI Creator Studio**.

Core loop:

```text
Signals
→ Opportunity Intelligence
→ Human Topic Decision
→ Research
→ Evidence / Provenance
→ Originality / Experiment
→ Content Family
→ Brand-Constrained Content
→ Export / Production
→ Manual Publishing
→ Analytics
→ Human-Approved Feedback
```

---

# 3. First Task: Audit and Retrofit Phases 1–3

Phases already implemented:

```text
Phase 0 — Greenfield Bootstrap
Phase 1 — Single Brand/Niche Foundation
Phase 2 — Engine Framework
Phase 3 — Niche Guard + Brand Engines
```

Treat them as implemented but not final.

Before Phase 4, create:

```text
docs/PHASE_1_3_RETROFIT_AUDIT.md
```

Audit:

- current commit SHA
- working tree
- repository structure
- migrations
- NicheProfile
- BrandProfile
- Brand Exemplars
- Brand Engine
- Niche Guard
- Engine contracts
- Engine registry
- local job handling
- settings UI
- platform links
- tests
- docs

Classify findings:

```text
KEEP
MODIFY
REMOVE
ADD
```

Do not rewrite working code without reason.

---

# 4. Phase 1 Retrofit — Single Niche + Stronger Brand Foundation

Enhance the existing single-niche foundation.

The niche should be specific enough to guide decisions. Recommended direction unless the owner changes it:

```text
Practical AI automation, coding agents, workflows, and AI tools
tested against real-world problems.
```

Do not hardcode that text into domain logic.

Add/editable fields:

```text
niche statement
target audience
regions
primary pain points
content pillars
allowed topics
adjacent topics
blocked topics
commercial-intent topics
evergreen topics
preferred source types
negative keywords
```

Initial content-pillar examples:

```text
Tool Tests
Workflow Builds
Coding-Agent Tests
Cost / Performance Comparisons
New-Release Impact
```

## Brand Memory

Add persistent Brand Memory for:

```text
recent approved hooks
recent CTAs
recent topics
recent products/models tested
recent conclusions
recent visual patterns
frequently used phrases
thumbnail wording
```

Brand consistency means:

```text
same identity
different execution
```

not:

```text
same template with a different product name
```

## Platform Settings

Keep one-click browser launcher settings:

```text
YouTube channel/studio URL
Facebook page/publishing URL
Instagram profile/publishing URL
TikTok profile/upload URL
```

HTTPS only.

## Monetization Metadata

Add optional:

```text
affiliate disclosure style
default lead magnet
newsletter CTA
digital-product CTA
sponsor disclosure style
```

Acceptance:

- one niche remains enforced
- Brand Memory persists
- content pillars are editable
- platform URLs persist
- no second workspace/niche exists

Commit:

```text
refactor: strengthen single-brand niche foundation
```

---

# 5. Phase 2 Retrofit — Lightweight Engine Architecture

Preserve modular Engines, but avoid framework overengineering.

Each Engine needs:

```text
id
version
rules_version
validate_config
health
run
dry_run where useful
explain where scoring/filtering occurs
structured result
run logs
```

Do NOT build:

```text
plugin marketplace
runtime plugin installation
distributed Engine scheduler
generic workflow DSL
complex dependency graph runtime
```

## Engine Versioning

Store:

```text
engine_version
rules_version
updated_at
change_reason
```

Produced content should record relevant Engine versions.

## Local Job System

Use a database-backed queue, not Redis/Celery.

Minimum fields:

```text
id
job_type
engine_id
project_id
payload
status
attempts
created_at
started_at
finished_at
error
```

## Repository Interfaces

Introduce clean storage boundaries:

```text
OpportunityRepository
ResearchRepository
EvidenceRepository
ProjectRepository
ContentRepository
AnalyticsRepository
AssetRepository
```

SQLite remains the implementation.

## Observability

Track:

```text
run ID
Engine/version
rules version
project
duration
cost
status
error summary
```

Acceptance:

- simple Engine contract
- versioning exists
- local job queue exists
- repository boundaries exist
- no unnecessary plugin framework

Commit:

```text
refactor: harden lightweight engine architecture
```

---

# 6. Phase 3 Retrofit — Niche Guard + Brand Intelligence

## Niche Guard

Must evaluate:

```text
niche fit
content pillar
adjacent-topic status
blocked-topic rules
negative keywords
audience relevance
```

Output must explain itself.

## Brand Engine

Add:

```text
tone rules
vocabulary
banned clichés
claim style
CTA consistency
Brand Memory lookup
repetition detection
platform adaptation
```

Detect:

```text
same hook pattern too often
same topic too recently
same CTA too often
same conclusion repeatedly
same content structure repeatedly
```

Warn intelligently rather than hard-blocking all repetition.

Brand QA dimensions:

```text
Tone
Vocabulary
Repetition
Audience Fit
CTA Fit
Platform Fit
```

Acceptance:

- brand history affects QA
- Niche Guard returns pillar
- repetition checks work
- explanations visible
- tests cover tone drift/repetition

Commit:

```text
refactor: add persistent brand memory and repetition intelligence
```

---

# 7. Retrofit Verification Gate

Run:

```text
backend tests
frontend tests
migration tests
Playwright tests for setup/settings/engines
security review
secret scan
```

Create:

```text
docs/PHASE_1_3_RETROFIT_REPORT.md
```

Do not continue if:

```text
existing DB migration is broken
single-niche invariant is broken
Brand/Niche persistence fails
Engine registry fails
tests regress without justified replacement
```

---

# 8. Phase 4 — RSS Engine

Purpose:

```text
What relevant material was newly published?
```

RSS must work with zero AI calls.

Implement:

```text
RSS/Atom adapters
timeouts
bounded retry
feed failure isolation
source trust
language filter
freshness filter
canonical URL
exact URL dedupe
normalized-title dedupe
near-title dedupe
content fingerprint
first_seen
last_seen
cross-source grouping
Niche Guard integration
```

If several sources cover one story:

```text
one candidate
+ source_count
+ source list
+ authority mix
```

UI:

```text
Add source
Disable source
Trust weight
Category
Last success/failure
Refresh
Dry Run
```

Acceptance:

- 100+ fixture items
- duplicate rerun creates no new candidate
- failing feed isolated
- old content rejected
- off-niche rejected
- cross-source copies grouped
- explanations available

Commit:

```text
feat: add resilient rss discovery engine
```

---

# 9. Phase 5 — Trends Engine

Purpose:

```text
What is gaining momentum inside our niche?
```

V1 must not require a paid Trends API.

Signals:

```text
cross-source mentions
mention velocity
first-seen recency
source diversity
source authority
keyword/entity momentum
historical baseline
manual boost
manual suppress
```

Adapters:

```text
RSS-derived signals
manual signals
future search-trend provider
future Reddit
future Hacker News
future GitHub
future YouTube discovery
```

Do not use unstable scraping just to increase source count.

Every score must explain itself, e.g.:

```text
6 independent mentions
4 trusted sources
first seen 42m ago
+180% vs baseline
```

Commit:

```text
feat: add explainable trends engine
```

---

# 10. Phase 6 — Opportunity Intelligence + Creator Cockpit

Replace simple trend ranking with:

```text
Is this worth creating for THIS channel?
```

Editable scoring dimensions:

```text
Niche fit                      18
Original test/value potential 20
Audience usefulness           15
Search/evergreen value        12
Trend momentum                10
Commercial/affiliate fit      10
Content-family potential       5
Sponsor relevance              3
Production effort/cost         4
Recent channel saturation      penalty
```

Output:

```text
Opportunity Score
Trend Score
Originality Potential
Evergreen Value
Commercial Fit
Estimated Effort
Suggested Original Angle
Suggested Content Family
Risks
Why
Recommended Action
```

## Creator Cockpit

Main dashboard should show decisions, not Engine internals:

```text
Signals Today
Needs Review
Research Ready
In Production
Ready to Publish
Published
AI Spend
Disk Usage
Engine Health summary
```

Top Opportunity card:

```text
Topic
Opportunity Score
Original Test Idea
Estimated Cost
Estimated Effort

[Research]
[Watch]
[Reject]
```

`/engines` remains a secondary engineering/configuration area.

Commit:

```text
feat: add opportunity intelligence and creator cockpit
```

---

# 11. Phase 7 — Research Engine

Create traceable Research Packets:

```text
primary sources
supporting sources
summary
facts
numbers
dates
entities
claims
contradictions
uncertain claims
things not to claim
```

Current facts must not rely only on model memory.

Allow manual corrections and preserve revisions.

Acceptance:

Every factual claim is:

```text
source-backed
OR explicitly uncertain
OR manually entered/labeled
```

Commit:

```text
feat: add traceable research packets
```

---

# 12. Phase 8 — Evidence / Provenance Engine

Add this as a first-class Engine.

Evidence graph:

```text
SOURCE
→ CLAIM
→ EXPERIMENT / MEASUREMENT
→ CONCLUSION
→ CONTENT CLAIM
→ SCRIPT SECTION
→ SCENE
→ PUBLISHED CONTENT
```

Entities:

```text
EvidenceSource
Claim
ClaimEvidence
Experiment
ExperimentRun
Measurement
Conclusion
ContentClaim
```

Claim types:

```text
external_fact
original_measurement
derived_conclusion
opinion
prediction/speculation
```

Never present opinion/speculation as fact.

## Evidence Coverage

Before Script Approval show:

```text
Total factual claims
Primary-source backed
Supporting-source backed
Original-test backed
Unsupported
Evidence Coverage %
```

For unsupported claims allow:

```text
find evidence
rewrite
remove
label as opinion
explicit override with reason
```

Preserve Evidence metadata long-term even if media is deleted.

Acceptance:

A script claim can be traced to evidence.

Commit:

```text
feat: add evidence provenance engine
```

---

# 13. Phase 9 — AI Provider Engine

Centralize all LLM calls.

Adapters:

```text
Gemini primary
Qwen fallback
```

Contract:

```text
generate_text
generate_structured
analyze
```

Store:

```text
provider
model
task
prompt version
usage
cost
latency
success
```

Fallback only for technical/schema failure.

Do not use fallback to manufacture factual support.

Provide mocks for tests.

Secrets never logged or returned after save.

Commit:

```text
feat: add pluggable ai provider engine
```

---

# 14. Phase 10 — Originality + Experiment Workspace

Every topic must answer:

```text
What are WE adding?
```

Supported originality:

```text
tool test
benchmark
cost comparison
workflow demonstration
before/after
implementation attempt
multi-source synthesis
original framework
original chart/data analysis
practical tutorial
failure analysis
clearly labeled opinion
```

Generic summary defaults to NOT READY.

Experiment Workspace stores:

```text
question
hypothesis
method
dataset/sample
tools/models
parameters
results
failures
latency
cost
screenshots/files
notes
conclusion
```

Attachments:

```text
JSON
CSV
screenshots
images
screen recordings
terminal output
code snippets
```

Measurements link into Evidence Engine.

Commit:

```text
feat: add originality and experiment workspace
```

---

# 15. Phase 11 — Content Family Engine

Replace:

```text
Project = one video
```

with:

```text
Content Family = one research/evidence investment
```

Example:

```text
Gemini vs Qwen Benchmark
├── Long YouTube video
├── Short: accuracy
├── Short: cost
├── Short: failure
├── Facebook companion post
├── Instagram version
├── TikTok version
└── Newsletter/article
```

Each child remains independently editable.

Do not duplicate identical storytelling blindly across platforms.

Commit:

```text
feat: add content family engine
```

---

# 16. Phase 12 — Evidence-Driven Content + Script Studio

Inputs:

```text
Research
Evidence
Original Experiment
Brand Profile
Brand Memory
Niche
Content Family
Format
```

Formats:

```text
Short Vertical Script
Long-form YouTube Script
Social Companion Copy
```

Script sections:

```text
Hook
Problem/Context
Method/Test
Evidence
Result
Interpretation
CTA
```

Support section-level:

```text
edit
regenerate
shorten
expand
make clearer
make more evidence-driven
restore revision
```

Quality dimensions:

```text
Evidence
Brand
Originality
Viewer Value
Niche Fit
Repetition
```

No single opaque score.

Script cannot approve when:

```text
off-niche
critical Brand failure
unsupported factual claim
missing original value
```

unless explicit override is recorded.

Commit:

```text
feat: add evidence-driven content studio
```

---

# 17. Phase 13 — Export + Publishing Assistant
## Build Before Full Media Automation

This phase makes the product usable before building a sophisticated renderer.

Export package should contain:

```text
sources.md
evidence-summary.md
script.md
platform metadata
asset requirements
manifest.json
manual/final media if present
```

## Publishing Assistant

From one page:

```text
YouTube
[Copy Title]
[Copy Description]
[Copy Hashtags]
[Open YouTube Studio]

Facebook
[Copy Caption]
[Open Facebook]

Instagram
[Copy Caption]
[Open Instagram]

TikTok
[Copy Caption]
[Open TikTok Upload]
```

Open the configured HTTPS URL in the normal browser/new tab.

Do not iframe social sites.

## Publishing Checklist

Per platform:

```text
media ready?
thumbnail ready?
title/caption ready?
sources checked?
affiliate disclosure needed?
AI disclosure recommendation?
asset rights verified?
```

Manual publication record:

```text
platform
status
published_at
URL
post ID optional
notes
```

Statuses:

```text
NOT_READY
READY
PUBLISHED
SKIPPED
```

Commit:

```text
feat: add export and manual publishing assistant
```

---

# 18. Mandatory Real-World Validation Gate

After Phase 13 the product should already be usable.

Create:

```text
docs/CONTENT_VALIDATION_PROTOCOL.md
```

Target:

```text
30–50 Shorts
6–10 long-form videos
```

Agents must never fabricate audience results.

Build tracking for:

```text
3-second hold where available
average percentage viewed
completion
rewatches
shares
saves
comments
returning viewers
subscriber conversion
search impressions
profile visits
link clicks
email signups
affiliate clicks
affiliate revenue
production cost
human production time
```

If results show no improvement:

```text
do not solve by adding automation
review niche
review pillars
review hook style
review original-value type
review evidence quality
review format
```

Media automation is a scaling investment, not a prerequisite to prove the channel.

---

# 19. Phase 14 — Asset Rights Engine

Track for every external/generated asset:

```text
source
creator/provider
license type
commercial-use status
attribution requirement
license proof/reference
expiry where relevant
AI-generated flag
notes
```

Statuses:

```text
VERIFIED
UNKNOWN
REQUIRES_ATTRIBUTION
DO_NOT_USE
```

Final QC warns on UNKNOWN/unsafe assets.

Do not claim legal certainty; track available documentation/provenance.

Commit:

```text
feat: add asset rights registry
```

---

# 20. Phase 15 — Scene + Asset Studio

Scene fields:

```text
narration
timing estimate
on-screen text
visual type
visual source
evidence reference
asset rights record
transition
status
```

Preferred visual priority:

```text
1 real screen recording
2 benchmark/chart
3 code/terminal
4 workflow diagram
5 product screenshot
6 original motion graphic
7 generated visual
```

Support:

```text
uploads
screen recordings
charts
images
generated-media adapter contract
asset tagging/search
```

App must remain usable with no paid image/video provider.

Commit:

```text
feat: add evidence-first scene and asset studio
```

---

# 21. Phase 16 — Voice, Subtitle + Media Engine

Media Engine owns:

```text
TTS
audio normalization
subtitle alignment
BGM
scene composition
FFmpeg
ffprobe
preview render
final render
```

Use replaceable adapters.

Voice:

```text
voice
speed
pauses
pronunciation
segment regeneration
```

Subtitles:

```text
actual alignment
timestamps
line breaks
Brand styling
manual corrections
```

BGM must come from approved/licensed library and have Asset Rights records.

Render using local DB-backed jobs.

No Redis/Celery.

Acceptance:

- local render works
- valid MP4
- expected dimensions
- audio exists
- captions work
- missing assets detected
- worker/job recovery tested

Commit:

```text
feat: add local media production engine
```

---

# 22. Phase 17 — Final Creator Quality Gate

One final review screen shows separately:

```text
Evidence Quality
Brand Fit
Originality
Viewer Value
Niche Fit
Repetition
Asset Rights
Technical Media QC
Estimated Cost
```

Require:

```text
Approve Final
```

Allow:

```text
return to script
return to scene
replace asset
fix unsupported claim
re-render segment
```

Commit:

```text
feat: add final creator quality gate
```

---

# 23. Phase 18 — Analytics Engine

Manual-first.

Support:

```text
manual metrics
CSV import abstraction
multiple snapshots over time
```

Track:

```text
views
likes
comments
shares
saves
watch time
average watch time
completion
followers/subscribers gained
link clicks
email signups
affiliate clicks
affiliate revenue
product revenue
platform revenue
AI cost
media cost
human time
```

Calculate:

```text
cost/content
revenue/content
subscriber conversion
email conversion
affiliate conversion
revenue per 1,000 qualified viewers
```

Analyze by:

```text
pillar
source
hook type
original-value type
format
duration
posting time
provider/model
```

Commit:

```text
feat: add creator business analytics
```

---

# 24. Phase 19 — Feedback Engine

Suggest changes; never silently mutate production rules.

Example:

```text
Tool Comparison posts produce 2.3x subscriber conversion.

Suggested Opportunity weight:
Original Test Potential 20 → 24
```

Actions:

```text
[Apply]
[Edit]
[Ignore]
```

All rule changes are:

```text
versioned
timestamped
reasoned
reversible
```

Commit:

```text
feat: add human-approved feedback engine
```

---

# 25. Phase 20 — Owned Audience Tracking

Do not build a full email system.

Track:

```text
lead magnet
landing page URL
newsletter CTA
email subscriber count
content source
conversion
```

Per content:

```text
CTA type
lead magnet
clicks
email signups
conversion rate
```

Goal:

```text
platform attention → owned audience
```

Commit:

```text
feat: add owned audience tracking
```

---

# 26. Phase 21 — Cleanup, Backup + Reliability

Cleanup Engine supports:

```text
dry run
exact file list
recoverable bytes
safe deletion
audit log
```

Defaults:

```text
tmp                    24h
cache                  24h
failed render temp      3d
downloaded source       7d
unused generated asset  7d
active-project media    retain
final media            30d after selected platforms published
exports                30d default
metadata/evidence       retain
analytics               retain
```

Never delete:

```text
active project references
render dependencies
export dependencies
READY publication assets
Evidence metadata
license proof
```

Backup:

```text
SQLite DB
Brand config
Niche config
Platform settings
critical metadata
```

Test restore against a copy.

Commit:

```text
feat: add local cleanup backup and recovery
```

---

# 27. Phase 22 — Final E2E Certification

Run end-to-end:

```text
setup
→ niche/brand
→ RSS
→ Trends
→ Opportunity
→ Research
→ Evidence
→ Originality/Experiment
→ Content Family
→ Script
→ Export/Publishing Assistant
→ Scene/Media if configured
→ Final Approval
→ Publication record
→ Analytics
→ Feedback
→ Cleanup
→ Backup/restore
```

Verify:

```text
restart persistence
single-niche invariant
Brand Memory
Engine isolation
RSS dedupe
Trend explainability
Evidence traceability
unsupported-claim gate
Content Family reuse
provider swap
asset rights
media recovery
platform launcher
analytics calculations
feedback versioning
safe cleanup
backup restore
secret safety
```

Create:

```text
FINAL_VERIFICATION_REPORT.md
```

Commit:

```text
test: certify evidence-driven creator studio
```

---

# 28. Parallel Execution Rules

Use the label **Parallel Execution** only where the work is genuinely independent.

Never parallelize tasks that:

```text
change the same migration/schema area
depend on unfinished shared contracts
change Engine core interfaces simultaneously
modify the same domain model
require another task's outputs
```

Parallel branches must:

```text
start from same known commit
have explicit file/module ownership
avoid overlapping migrations
merge/rebase deliberately
run affected and integration tests after merge
```

---

# 29. Parallel Execution — Phase 1–3 Retrofit

Do NOT parallelize the initial audit.

After the audit/architecture decisions are fixed:

### Parallel Execution

**Agent A**
```text
Phase 1:
Brand Memory
content pillars
platform/monetization settings UI
```

**Agent B**
```text
Phase 2:
job system
Engine observability
repository interfaces
```

Only if schema ownership is coordinated.

Then merge and execute Phase 3 retrofit sequentially because it depends on Brand Memory + Engine contracts.

---

# 30. Parallel Execution — RSS + Trends

First freeze shared contracts:

```text
DiscoveryCandidate
TopicKey
TopicSignal
EngineRun
```

Then:

### Parallel Execution

**Agent A**
```text
RSS adapters
fetch/dedupe
source UI
```

**Agent B**
```text
Trends scoring
trend-history service
fixture-based Trends UI
```

After merge, integrate RSS-derived trend signals.

---

# 31. Parallel Execution — Research + AI Provider

After AI Provider interfaces are defined:

### Parallel Execution

**Agent A**
```text
Gemini/Qwen adapters
mock provider
usage/cost tracking
```

**Agent B**
```text
Research models
source/claim workflow
Research UI
```

Integrate AI extraction after both merge.

---

# 32. Parallel Execution — Evidence + Originality

First freeze:

```text
Claim
Experiment
Measurement
Conclusion
```

Then:

### Parallel Execution

**Agent A**
```text
Evidence graph
coverage calculation
Evidence UI
```

**Agent B**
```text
Originality scoring
Experiment Workspace
experiment UI
```

Merge, then connect Experiment Measurements to Evidence.

---

# 33. Parallel Execution — Content Family + Script UI

After shared ContentFamily/MasterContent contracts are frozen:

### Parallel Execution

**Agent A**
```text
Content Family domain/services
child-content management
```

**Agent B**
```text
Script Studio UI
revision editor
Brand/Evidence QA presentation
```

Content orchestration integrates after merge.

---

# 34. Parallel Execution — Export + Publishing Assistant

After platform metadata contracts are stable:

### Parallel Execution

**Agent A**
```text
Export Engine
manifests/checksums
filesystem packages
```

**Agent B**
```text
Publishing Assistant UI
copy buttons
platform launcher
manual publication records
```

Then merge and run Playwright E2E.

---

# 35. Parallel Execution — Asset Rights + Scene Foundations

After Asset contract is stable:

### Parallel Execution

**Agent A**
```text
Asset Rights Engine
license/provenance UI
```

**Agent B**
```text
Scene editor
asset library
upload/tag/search
```

After merge, require Scene assets to expose rights state.

---

# 36. Parallel Execution — Voice + Subtitle

After Media job contracts are frozen:

### Parallel Execution

**Agent A**
```text
TTS
voice segments
voice UI
```

**Agent B**
```text
subtitle alignment
subtitle editor
```

FFmpeg composition follows after both merge.

---

# 37. Parallel Execution — Analytics + Owned Audience

After publication/content IDs are stable:

### Parallel Execution

**Agent A**
```text
Analytics snapshots
performance calculations
dashboard
```

**Agent B**
```text
lead magnet/CTA fields
owned-audience tracking
conversion UI
```

Feedback Engine waits until Analytics is complete.

---

# 38. Work That Must Stay Sequential

Do NOT parallelize:

```text
initial Phase 1–3 retrofit audit
shared schema/contract decisions
Engine core refactors
migrations touching same tables
Opportunity Engine before RSS/Trends contracts
Evidence integration before Research claims
Content generation before Evidence/Originality contracts
Feedback Engine before Analytics
final E2E certification
```

---

# 39. Engine Isolation Regression Tests

RSS failure must not break:

```text
historical Trends
existing Research
Content
Media
Export
```

Trend rule changes must not modify:

```text
RSS parsing
Brand
Evidence
Media
```

Brand changes must not change:

```text
source storage
Trend calculations
experiment measurements
```

AI provider changes must not require changes to:

```text
Research domain
Evidence domain
Content UI
database schema
```

TTS provider changes must not affect:

```text
Opportunity
Research
Evidence
Publishing Assistant
```

---

# 40. Cost Controls

Track where possible:

```text
LLM cost
TTS cost
image/video generation cost
render time
human-time estimate
```

Before expensive operations show:

```text
Estimated Cost
[Continue]
[Cheaper Option]
[Cancel]
```

Support:

```text
max AI cost/day
max cost/project
max generated-video seconds/project
```

No silent expensive retries.

---

# 41. Security Requirements

Defaults:

```text
localhost binding
restricted CORS
file-path validation
path traversal prevention
upload type/size validation
list-form subprocess args
FFmpeg/ffprobe timeout
unique temp dirs
secret redaction
API keys not returned after storage
```

Do not store browser cookies.

Platform launcher opens the system browser.

Run Security Reviewer for:

```text
uploads
filesystem
FFmpeg
source extraction
provider secrets
backup/restore
```

---

# 42. Founder Metrics

Do not optimize only for views.

Track:

```text
viewer retention
completion
returning viewers
subscriber conversion
search impressions
shares/saves
profile visits
link clicks
email signups
affiliate clicks
affiliate revenue
product revenue
platform revenue
cost/content
human time/content
revenue/content
```

Long-term key metric:

```text
Revenue per 1,000 qualified viewers
```

---

# 43. Documentation

Maintain:

```text
docs/PHASE_STATUS.md
docs/DECISIONS.md
docs/ENGINE_SYSTEM.md
docs/BRAND_SYSTEM.md
docs/EVIDENCE_SYSTEM.md
docs/CONTENT_FAMILY.md
docs/CONTENT_VALIDATION_PROTOCOL.md
docs/DATA_RETENTION.md
docs/MANUAL_PUBLISHING.md
docs/TESTING.md
```

`PHASE_STATUS.md`:

```text
Phase
Status
Commit
Tests
Browser Verification
Blocker
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

---

# 44. Per-Phase Agent Report

After every phase:

```text
PHASE:
STATUS:

Implemented:
-

Modified existing behavior:
-

Files changed:
-

Migrations:
-

Tests:
-

Playwright/browser verification:
-

Security review:
-

Architecture concerns:
-

Known limitations:
-

Parallel work merged:
-

Next phase:
-

Commit:
```

Do not report PASS when acceptance checks were skipped.

---

# 45. Git Rules

Continue the current fresh public repository.

Do not:

```text
create another repo
reuse old n8n repo
add CI/CD
add GitHub Actions
commit secrets
commit runtime SQLite DB
commit generated media
```

Before merging parallel branches:

```text
review diff
rebase/update
resolve conflicts consciously
run affected tests
run integration tests
```

---

# 46. Execution Order

Execute exactly in this high-level order:

```text
A. Audit Phase 1–3
B. Retrofit Phase 1
C. Retrofit Phase 2
D. Retrofit Phase 3
E. Retrofit Verification Gate

4. RSS
5. Trends
6. Opportunity Intelligence + Creator Cockpit
7. Research
8. Evidence / Provenance
9. AI Provider
10. Originality + Experiment
11. Content Family
12. Content + Script Studio
13. Export + Publishing Assistant

--- REAL-WORLD CONTENT VALIDATION GATE ---

14. Asset Rights
15. Scene + Assets
16. Voice / Subtitle / Media
17. Final Quality Gate
18. Analytics
19. Feedback
20. Owned Audience
21. Cleanup / Backup / Reliability
22. Final E2E Certification
```

---

# 47. Immediate Starting Instruction

Begin with:

```text
PHASE 1–3 RETROFIT AUDIT
```

Do not modify code until the audit is complete.

First report must include:

```text
current commit SHA
working tree status
Phase 1–3 feature inventory
test baseline
migration baseline
architecture mismatches
KEEP/MODIFY/REMOVE/ADD table
safe Parallel Execution plan
```

Then execute the retrofit and continue phase-by-phase.

Do not begin RSS until the retrofit verification gate passes.

---

# 48. Final Definition of Done

The creator can:

```text
1. Open Creator Cockpit
2. Work in one niche/brand
3. Refresh RSS
4. See explainable Trends
5. Review Opportunity Intelligence
6. Select a topic
7. Build sourced Research
8. Trace claims through Evidence
9. Run/store an original Experiment
10. Build a Content Family
11. Generate/edit brand-consistent scripts
12. Check Evidence/Originality/Viewer Value separately
13. Export platform-ready content
14. Open each platform in one click
15. Manually publish and save URLs
16. Track creator/business analytics
17. Receive human-reviewable feedback
18. Produce scenes/media locally when desired
19. Verify asset rights/provenance
20. Render/preview/final approve media
21. Track owned-audience conversions
22. Clean low-value storage safely
23. Back up/restore critical data
24. Inspect Engine/rules version history
```

The software should make the creator better at:

```text
choosing
testing
proving
explaining
publishing
learning
```

—not merely better at generating more content.
