# Content Family Engine

## Mission
The **Content Family Engine** replaces the naive assumption that `Project = one piece of content` with:
> **Content Family = one research, evidence, and originality investment**

A single Content Family amortizes high research and empirical benchmark investments by generating multiple tailored, platform-specific child items (long-form video, vertical shorts, social companion cheat-sheets, and deep-dive technical newsletters) from the exact same factual foundation.

## Core Invariants
1. **Evidence Reference Inheritance:** Child content items reference claims in the Evidence Engine provenance graph via `ContentItemEvidenceSelection` without duplicating claim records.
2. **Originality Preservation:** Every child item must maintain an explicit `original_value_connection` to the parent's `what_are_we_adding` declaration.
3. **Anti-Clone & Brand Variation:** Child suggestions automatically vary hooks, angles, and platform styles to prevent publishing clone content.
4. **Independent Child Customization:** Each child item has its own status, angle, working title, and incremental economics.
5. **No Script Approval in Phase 11:** Children remain in `PLANNED` or `DRAFT` status; script approval belongs exclusively to Phase 12.

## Engine Contracts
- `manifest.yaml`: Declares engine identity, inputs, outputs, and capabilities.
- `rules.yaml`: Declares supported formats, platforms, repetition prevention limits, and min angle lengths.
- `contracts.py`: Declares Pydantic schemas for family creation, child suggestions, validations, and economics summaries.
- `engine.py`: Implements `BaseEngine` interface with `suggest_children`, `validate_family`, `validate_child`, and `calculate_economics`.
