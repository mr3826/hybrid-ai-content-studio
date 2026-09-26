# Product Specification — Fresh Local AI Content Studio

## 1. Product Vision & Philosophy
The **Fresh Local AI Content Studio** is a local-first system designed to build original, high-trust, brand-aligned content packages from niche signals without relying on generic auto-posting or cloud SaaS orchestrators.

Instead of the anti-pattern:
```text
RSS → AI summarize → AI voice → generic video → auto-post at scale
```

The system enforces:
```text
Niche Sources → Discovery Engines → Opportunity Ranking → Research / Evidence →
Original Test / Insight / Comparison → Human Editorial Decision →
Brand-Constrained AI Production → Preview + QC → Export Package →
Open Platform in Browser → Manual Upload → Performance Feedback
```

## 2. Core Functional Requirements
1. **Single-Niche Focus:** Exactly one configured niche profile with defined content pillars, allowed topics, adjacent topics, and blocked topics.
2. **Single-Brand Consistency:** Exactly one brand DNA defining tone, vocabulary rules, banned clichés, claim rules, and visual guidelines.
3. **Evidence & Originality Gates:** Every publishable item must attach an original contribution (e.g., benchmark, before/after, tool test, tutorial, failure analysis). Generic summaries default to blocked unless an explicit override is recorded.
4. **Independent Engine Architecture:** 13 specialized engines with typed contracts, isolated configurations, independent health checks, and full explainability.
5. **Manual Platform Launchers:** One-click HTTPS buttons opening authenticated platform pages in the user's default browser (`target="_blank"`, `rel="noopener noreferrer"`) alongside one-click copy buttons for platform-specific titles, captions, and hashtags.
6. **Publication & Analytics Logging:** Manual post-publication URL and performance tracking (views, retention, engagement, link clicks, revenue).
7. **Storage & Cost Discipline:** Real-time tracking of AI token expenditures and automated reference-safe media retention policies.

## 3. Supported Formats
- **Short Vertical Video:** 9:16 vertical video (30s–60s) for YouTube Shorts, Instagram Reels, TikTok, and Facebook Reels.
- **Long-Form Script:** Structured multi-section scripts for standard YouTube videos.
- **Social Companion Posts:** Tailored text posts and carousels for Facebook and Instagram.
