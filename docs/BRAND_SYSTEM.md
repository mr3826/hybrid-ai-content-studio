# Brand System — DNA & Consistency Guard

## 1. Single-Brand Principle
The studio enforces exactly **one brand profile** across all generated content and multi-platform distribution. No per-project brand overrides or multi-tenant switching is permitted.

## 2. Brand Profile Structure
```yaml
brand_name: "Practical AI Studio"
brand_promise: "Tested AI tools, automated workflows, and honest benchmarks without hype."
audience: "Engineers, builders, and technical knowledge workers."

tone:
  - evidence-driven
  - concise
  - practical
  - calm
  - transparent

voice_rules:
  - "Show the terminal or interface; do not merely talk about it."
  - "State costs, latency, and failure rates explicitly."
  - "Never declare a tool 'game-changing' or 'revolutionary'."

preferred_vocabulary:
  - "workflow"
  - "benchmark"
  - "latency"
  - "trade-off"
  - "failure rate"
  - "reproducible"

avoid_vocabulary:
  - "game-changer"
  - "insane"
  - "mind-blowing"
  - "unbelievable"
  - "passive income"

banned_cliches:
  - "In today's fast-paced world..."
  - "Without further ado..."
  - "Let's dive right in!"

claim_rules:
  - "Every speed or accuracy claim must cite a benchmark run or primary source."
  - "Include pricing tiers and hidden API token limits."

cta_style: "Direct, educational, and low-friction (e.g., 'Inspect the reproduction script linked below')."
```

## 3. Brand QA Output Contract
```json
{
  "on_brand": true,
  "tone_score": 92,
  "niche_score": 95,
  "repetition_score": 4,
  "violations": [],
  "suggested_fixes": []
}
```
A script that fails Brand QA cannot proceed to final approval without an explicit user override logged in the audit trail.
