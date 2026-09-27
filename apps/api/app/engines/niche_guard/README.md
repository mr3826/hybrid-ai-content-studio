# Niche Guard Engine

## Overview
The **Niche Guard Engine** is the deterministic gatekeeper of the Fresh Local AI Content Studio. It enforces strict alignment against the single active `NicheProfile` without invoking third-party LLMs.

## Core Responsibilities
1. **Instant Block**: Hard-rejects any candidate containing blocked topics (e.g., crypto schemes, passive income, consumer gadgets) immediately with a score of 0.0.
2. **Deterministic Taxonomy Scoring**:
   - **Content Pillars**: Matches defined pillar names or associated technical keywords.
   - **Allowed Topics**: Scores presence of primary allowed niche topics.
   - **Adjacent Topics**: Evaluates contextual fit, penalizing candidates that lack core allowed topics.
   - **Must-Have Signals**: Rewards presence of technical proof (code repos, benchmarks, papers).
   - **Negative Keywords**: Penalizes spam or hype terms (-25 pts each).
3. **Audit & Explainability**: Every verdict retains an itemized breakdown of factors, matched keywords, and scoring contributions.

## Contracts
- **Input**: `NicheGuardInput` (`title`, `text`, `tags`, `url`, `metadata`)
- **Output**: `NicheGuardVerdict` (`passed`, `score`, `reason`, `blocked_topics_detected`, `pillar_matches`, `matched_allowed_topics`, `factors`)

## Configuration (`rules.yaml`)
- `thresholds.min_pass_score`: Minimum score required to pass (default: `55.0`).
- `behavior.instant_block_on_blocked_topic`: Flag to instantly reject blocked topics.
