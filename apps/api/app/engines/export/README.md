# Export & Publishing Assistant Engine

## Overview
The **Export Engine** compiles approved content packages into reference-safe offline directories (`data/exports/{timestamp}-{slug}/`), calculates SHA256 integrity checksums, and formats tailored metadata and copyable text for YouTube, Facebook, Instagram, and TikTok distribution.

## Engine Contract
- **Inputs**: `ExportEngineInput` (Item metadata, approved script sections, brand profile, sources, claims, experiments)
- **Outputs**: `ExportPackageOutput` (Package ID, slug, files written, SHA256 checksums, platform metadata)
- **Dependencies**: None (Operates on verified upstream artifacts)

## Output Package Structure
```text
data/exports/2026-09-27-coding-benchmark-short/
  ├─ sources.md
  ├─ evidence-summary.md
  ├─ script.md
  ├─ asset-requirements.md
  ├─ manifest.json
  ├─ youtube/
  │  ├─ title.txt
  │  ├─ description.txt
  │  ├─ hashtags.txt
  │  └─ pinned-comment.txt
  ├─ facebook/
  │  └─ caption.txt
  ├─ instagram/
  │  └─ caption.txt
  └─ tiktok/
     └─ caption.txt
```

## Publishing Checklist (7 Gates)
1. `media_ready`: Final media render or companion graphic verified
2. `thumbnail_ready`: Eye-catching thumbnail rendered and checked
3. `title_caption_ready`: Platform-tailored title, description, and hashtags approved
4. `sources_checked`: Primary sources and citations fact-checked
5. `affiliate_disclosure_needed`: Affiliate/promotional disclosures declared
6. `ai_disclosure_recommended`: Transparent AI-assistance declared
7. `asset_rights_verified`: Visual, audio, and font rights confirmed
