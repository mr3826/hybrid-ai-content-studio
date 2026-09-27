# Brand Engine

## Overview
The **Brand Engine** is the core brand DNA validator of the Fresh Local AI Content Studio. It guarantees that all scripts, hooks, captions, and companion posts adhere to the active `BrandProfile` guidelines and quality standards.

## Core Responsibilities
1. **Banned Cliché Detection**: Automatically flags and penalizes lazy AI openings (e.g. *"In today's fast-paced world..."*, *"Without further ado..."*, *"Let's dive right in!"*).
2. **Vocabulary Blacklist & Whitelist**:
   - Rejects hype adjectives (*"game-changer"*, *"mind-blowing"*, *"insane"*, *"passive income"*).
   - Rewards empirical terminology (*"workflow"*, *"benchmark"*, *"latency"*, *"trade-off"*, *"reproducible"*).
3. **Voice & Tone Auditing**: Detects exclamation point overuse, all-caps shouting, and unsubstantiated performance claims.
4. **Exemplar Cross-Referencing**: Identifies approved historical hooks and script exemplars for inspiration.
5. **Quality Gate Verdict**: Assigns an overall brand adherence score and blocks scripts with critical violations from downstream production.

## Contracts
- **Input**: `BrandQAInput` (`title`, `body`, `hook`, `cta`, `platform`, `metadata`)
- **Output**: `BrandQAVerdict` (`on_brand`, `overall_score`, `tone_score`, `vocabulary_score`, `cliche_score`, `violations`, `suggested_fixes`, `exemplar_matches`)

## Configuration (`rules.yaml`)
- `thresholds.min_pass_score`: Minimum brand score required to pass (default: `70.0`).
- `thresholds.max_critical_violations`: Critical violations permitted (default: `0`).
