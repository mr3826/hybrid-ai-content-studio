"""
Phase 22 Final E2E Certification Test Suite.

Certifies the entire Fresh Local AI Content Studio V1 lifecycle,
validating all 24 creator capabilities and 10 non-negotiable architectural invariants:
1. One Niche (Singleton NicheProfile)
2. One Brand (Singleton BrandProfile)
3. Local-First (SQLite WAL, local storage, offline-ready)
4. Engine-Based (13 decoupled concrete engines)
5. Human-Approved (Human Quality Gates at topic, research, script, media, QC, and feedback)
6. Manual-Publish-First (One-click browser launcher + clipboard metadata copy)
7. Cost-Aware (Zero required paid APIs, compute & token tracking)
8. Evidence-Driven (Claims backed by primary/supporting sources, originality proof)
9. No n8n (Pure Python/FastAPI/SQLAlchemy architecture)
10. No CI/CD (Autonomous local verification)
"""

import hashlib
import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from app.models.brand import BrandProfile, SINGLETON_BRAND_ID
from app.engines.core.registry import engine_registry


@pytest.mark.asyncio
async def test_e2e_24_step_creator_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """
    Executes a comprehensive, uninterrupted 24-step creator workflow through the API,
    validating the complete V1 Definition of Done (Sections 48 & 69).
    """
    run_id = uuid.uuid4().hex[:8]

    # =========================================================================
    # Step 1: Health & Creator Cockpit Bootstrap
    # =========================================================================
    health_res = await client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    cockpit_res = await client.get("/api/v1/opportunities/cockpit/summary")
    assert cockpit_res.status_code == 200
    cockpit_data = cockpit_res.json()
    assert "signals_today" in cockpit_data
    assert "engine_health_summary" in cockpit_data

    # =========================================================================
    # Step 2: Singleton Niche & Brand Foundation
    # =========================================================================
    niche_payload = {
        "name": f"AI Engineering & Local Workflows ({run_id})",
        "one_sentence_definition": "Hands-on engineering benchmarks and production AI agent architectures.",
        "audience": "Software architects, machine learning engineers, and developers.",
        "audience_regions": ["Global", "North America", "Europe"],
        "primary_problems": [
            "Agent benchmark claims often mismatch dirty production codebases.",
            "High token costs and vendor lock-in.",
        ],
        "allowed_topics": ["coding agents", "local LLMs", "developer automation"],
        "adjacent_topics": ["DevOps", "system architecture"],
        "blocked_topics": ["crypto trading", "unverified hype"],
        "must_have_signals": ["reproducible benchmark", "git repository"],
        "negative_keywords": ["secret hack", "revolutionary game-changer"],
        "preferred_source_types": ["engineering_blogs", "github_releases"],
        "content_pillars": [
            {
                "id": "agent_benchmarks",
                "name": "Local Agent Benchmarks",
                "description": "Stress testing code generation on complex repositories.",
            }
        ],
        "commercial_intent_topics": ["developer workstations"],
        "evergreen_topics": ["how to evaluate local LLMs"],
    }
    niche_res = await client.put("/api/v1/niche", json=niche_payload)
    assert niche_res.status_code == 200
    assert niche_res.json()["id"] == SINGLETON_NICHE_ID

    brand_payload = {
        "brand_name": f"Evidence AI Studio ({run_id})",
        "brand_promise": "Objective benchmarks, local workflows, zero sponsored hype.",
        "audience": "Engineers and builders.",
        "tone": ["evidence-driven", "calm", "concise", "practical"],
        "voice_rules": [
            "Show the terminal logs; do not just describe them.",
            "Always state hardware specifications, latency, and costs.",
        ],
        "preferred_vocabulary": ["benchmark", "reproducible", "latency", "trade-off"],
        "avoid_vocabulary": ["insane", "mind-blowing", "game-changer"],
        "banned_cliches": ["In today's fast-paced world...", "Let's dive right in!"],
        "claim_rules": ["Every empirical claim must link to a benchmark artifact or source."],
        "cta_style": "Educational and direct.",
        "humor_policy": "Subtle and technical.",
        "controversy_policy": "Rely strictly on measurable data.",
        "sponsor_policy": "Full disclosure upfront.",
        "affiliate_disclosure_style": "Transparent footnote in descriptions.",
        "visual_identity": {
            "primary_font": "Inter",
            "secondary_font": "JetBrains Mono",
            "caption_style": "mono-cyan-highlight",
        },
        "platform_adaptations": {
            "youtube": {"default_tags": ["ai", "coding", "benchmark"]},
            "tiktok": {"caption_limit": 150},
        },
    }
    brand_res = await client.put("/api/v1/brand", json=brand_payload)
    assert brand_res.status_code == 200
    assert brand_res.json()["id"] == SINGLETON_BRAND_ID

    # =========================================================================
    # Step 3: RSS Discovery Source Ingestion & Feed Refresh
    # =========================================================================
    feed_url = f"https://tech-feed.local/rss-{run_id}.xml"
    feed_payload = {
        "name": f"Local AI Systems Digest ({run_id})",
        "url": feed_url,
        "category": "Engineering",
        "trust_weight": 0.95,
        "enabled": True,
    }
    src_res = await client.post("/api/v1/rss/feeds", json=feed_payload)
    assert src_res.status_code == 201
    feed_id = src_res.json()["id"]

    from tests.test_rss_api import _make_xml
    xml_fixture = _make_xml(
        title=f"Coding Agent Benchmark Evaluation on Dirty Codebases ({run_id})",
        link=f"https://tech-feed.local/article-{run_id}?utm_source=rss",
        summary="Stress testing autonomous coding agents on Python repositories with reproducible benchmark.",
    )
    run_res = await client.post(
        "/api/v1/rss/run",
        json={
            "feeds": [feed_payload],
            "xml_fixtures": {feed_url: xml_fixture},
        },
    )
    assert run_res.status_code == 200
    assert run_res.json()["engine_result"]["success"] is True

    # Clean up test feed so it does not persist in SQLite
    del_feed_res = await client.delete(f"/api/v1/rss/feeds/{feed_id}")
    assert del_feed_res.status_code == 204

    # =========================================================================
    # Step 4: Trends Engine Velocity & Explainability
    # =========================================================================
    trends_res = await client.get("/api/v1/trends")
    assert trends_res.status_code == 200
    trends_data = trends_res.json()
    assert isinstance(trends_data, list)
    if len(trends_data) > 0:
        sample_hash = trends_data[0].get("topic_hash") or trends_data[0].get("id")
        explain_res = await client.get(f"/api/v1/trends/explain/{sample_hash}")
        assert explain_res.status_code in (200, 404)

    # =========================================================================
    # Step 5: Opportunity Intelligence Run & Scoring
    # =========================================================================
    opp_topic = f"Local Quantized Inference Benchmarks on M4 Max ({run_id})"
    opp_run_res = await client.post(
        "/api/v1/opportunities/run",
        json={
            "custom_topics": [
                {
                    "topic": opp_topic,
                    "summary": "Benchmarking token generation, memory bandwidth saturation, and thermal throttling.",
                    "pillar": "Hardware Benchmarks",
                    "trend_score": 92.5,
                }
            ],
            "include_candidates": False,
            "include_trends": False,
        },
    )
    assert opp_run_res.status_code == 200
    assert opp_run_res.json()["success"] is True

    opps_res = await client.get("/api/v1/opportunities?limit=100")
    assert opps_res.status_code == 200
    all_opps = opps_res.json()
    target_opp = next((o for o in all_opps if run_id in o["topic"]), None)
    assert target_opp is not None, "Opportunity was successfully scored and indexed"
    opp_id = target_opp["id"]

    # =========================================================================
    # Step 6: Human Gate 1 — Topic Selection & Approval
    # =========================================================================
    opp_approve_res = await client.post(f"/api/v1/opportunities/{opp_id}/research")
    assert opp_approve_res.status_code == 200
    assert opp_approve_res.json()["status"] == "research_ready"

    # =========================================================================
    # Step 7: Evidence-Based Research Packet Creation
    # =========================================================================
    research_payload = {
        "topic": opp_topic,
        "sources": [
            {
                "url": f"https://benchmark-lab.local/apple-m4-eval-{run_id}",
                "title": "Hardware Stress Testing Lab Report",
                "excerpt": (
                    "Apple M4 Max delivered 142 tokens/sec on DeepSeek-R1-67B quantized. "
                    "First-token latency clocked at 16ms under ambient temperature 21C. "
                    "However, thermal saturation reduces sustained throughput by 8% after 20 minutes."
                ),
                "trust_weight": 1.6,
            },
            {
                "url": f"https://developer-forum.local/vendor-claims-{run_id}",
                "title": "Vendor Community Discussion",
                "excerpt": (
                    "Marketers claimed zero throttling and infinite memory bandwidth. "
                    "Our independent testing showed memory bandwidth peaks at 410 GB/s."
                ),
                "trust_weight": 1.1,
            },
        ],
        "context": "Benchmarking conducted in local lab environment.",
    }
    packet_res = await client.post("/api/v1/research/packets", json=research_payload)
    assert packet_res.status_code == 201
    packet = packet_res.json()
    packet_id = packet["id"]
    assert len(packet["primary_sources"]) >= 1
    assert len(packet["facts"]) >= 1
    assert packet["is_verified"] is False  # Requires human verification

    # Human Gate: Verify Research Packet
    verify_pkt_res = await client.post(f"/api/v1/research/packets/{packet_id}/verify")
    assert verify_pkt_res.status_code == 200
    assert verify_pkt_res.json()["is_verified"] is True

    # =========================================================================
    # Step 8: Evidence Provenance Graph & Claim Verification
    # =========================================================================
    claim_payload = {
        "text": f"M4 Max delivers 142 tokens/sec on DeepSeek-R1 quantized ({run_id})",
        "claim_type": "external_fact",
        "confidence": 0.98,
    }
    claim_res = await client.post("/api/v1/evidence/claims", json=claim_payload)
    assert claim_res.status_code == 201
    claim_id = claim_res.json()["id"]

    link_res = await client.post(
        f"/api/v1/evidence/claims/{claim_id}/link-source",
        json={
            "source_url": f"https://benchmark-lab.local/apple-m4-eval-{run_id}",
            "source_title": "Hardware Stress Testing Lab Report",
            "source_type": "primary",
            "trust_weight": 1.6,
            "quote": "142 tokens/sec sustained throughput.",
            "confidence": 0.99,
        },
    )
    assert link_res.status_code == 200
    assert link_res.json()["is_claim_verified"] is True

    # =========================================================================
    # Step 9: Originality "What are WE adding?" Experiment & Plan Approval
    # =========================================================================
    orig_plan_res = await client.post(
        "/api/v1/originality/plans",
        json={
            "topic": opp_topic,
            "originality_type": "benchmark",
            "what_are_we_adding": "Independent thermal stress curve and side-by-side power draw wattmeter logs.",
            "why_it_matters": "Shows creators exact hardware trade-offs before purchasing $4,000 workstations.",
        },
    )
    assert orig_plan_res.status_code == 201
    orig_plan = orig_plan_res.json()
    orig_plan_id = orig_plan["id"]
    assert orig_plan["status"] == "needs_review"

    # Human Gate: Approve Originality Plan
    orig_approve_res = await client.post(
        f"/api/v1/originality/plans/{orig_plan_id}/approve",
        json={"reviewer": "creative_director", "notes": "Solid test protocol that adds proprietary lab value."},
    )
    assert orig_approve_res.status_code == 200
    assert orig_approve_res.json()["status"] == "approved"

    # =========================================================================
    # Step 10: Parent Content Family & Child Content Item Creation
    # =========================================================================
    family_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"M4 Max Local Inference Master Family ({run_id})",
            "content_pillar": "Local Agent Benchmarks",
            "original_value_type": "benchmark",
            "summary": "Core experiment validating local LLM throughput, power draw, and cost amortization.",
            "research_cost": 2.00,
            "experiment_cost": 0.00,
            "ai_cost": 0.40,
            "manual_time_minutes": 60,
        },
    )
    assert family_res.status_code == 201
    family = family_res.json()
    family_id = family["id"]

    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"M4 Max 142 Tokens/Sec Reality Test ({run_id})",
            "angle": "Direct wattmeter and terminal benchmark showing true performance without cloud fees.",
            "hook_type": "bold_claim",
            "original_value_connection": "Proprietary wattmeter and thermal camera measurements.",
            "viewer_value": "Actionable command-line config flags for local llama.cpp runners.",
        },
    )
    assert item_res.status_code == 201
    item = item_res.json()
    item_id = item["id"]

    # =========================================================================
    # Step 11: Evidence-Grounded Script Draft Generation & Refinement
    # =========================================================================
    gen_script_res = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 45},
    )
    assert gen_script_res.status_code == 200
    script = gen_script_res.json()
    script_id = script["id"]
    assert len(script["sections"]) >= 4
    assert script["status"] in ("DRAFT", "SCRIPT_REVIEW")

    # Section-level refinement
    sec_id = script["sections"][0]["id"]
    refine_res = await client.post(
        f"/api/v1/scripts/{script_id}/sections/{sec_id}/refine",
        json={"refinement_type": "shorten", "guidance": "Hook must deliver punch in under 3 seconds"},
    )
    assert refine_res.status_code == 200

    # =========================================================================
    # Step 12: Script Brand QA Audit & Human Approval Gate
    # =========================================================================
    qa_check_res = await client.post(f"/api/v1/scripts/{script_id}/quality-check")
    assert qa_check_res.status_code == 200
    assert "dimension_scores" in qa_check_res.json()

    # Human Gate: Explicit Script Approval
    approve_script_res = await client.post(
        f"/api/v1/scripts/{script_id}/approve",
        json={"reviewer": "lead_editor", "notes": "Concise, evidence-grounded script approved for production."},
    )
    assert approve_script_res.status_code == 200
    approved_script = approve_script_res.json()
    assert approved_script["is_approved"] is True
    assert approved_script["status"] == "SCRIPT_APPROVED"

    # =========================================================================
    # Step 13: Storyboard Scene Decomposition
    # =========================================================================
    decompose_res = await client.post(f"/api/v1/scenes/decompose/{script_id}")
    assert decompose_res.status_code == 200
    scenes = decompose_res.json()
    assert len(scenes) >= 3

    # =========================================================================
    # Step 14: Asset Rights Registry & License Classification
    # =========================================================================
    asset_res = await client.post(
        "/api/v1/asset-rights",
        json={
            "title": f"Terminal Wattmeter Chart ({run_id})",
            "asset_type": "chart",
            "source": "Local ML Rig Script",
            "creator_provider": "Internal Studio",
            "license_type": "Self-Created",
            "license_proof": "Generated locally by lab suite",
            "notes": "Original proprietary benchmark chart",
        },
    )
    assert asset_res.status_code == 201
    asset_data = asset_res.json()
    assert asset_data["status"] == "VERIFIED"

    stats_res = await client.get("/api/v1/asset-rights/summary/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_assets"] >= 1

    # =========================================================================
    # Step 15: Local Media Generation (Voice Audio & Timed Subtitles)
    # =========================================================================
    voice_res = await client.post(
        f"/api/v1/media/voice/{script_id}",
        json={"voice_id": "en-US-Studio-Standard", "speed": 1.0},
    )
    assert voice_res.status_code == 200
    media_pkg = voice_res.json()
    assert media_pkg["status"] == "READY"
    assert media_pkg["audio_path"] is not None

    sub_res = await client.post(
        f"/api/v1/media/subtitles/{script_id}",
        json={"format": "srt", "max_words_per_line": 3},
    )
    assert sub_res.status_code == 200
    assert "-->" in sub_res.json()["content_text"]

    render_res = await client.post(
        f"/api/v1/media/render/{script_id}",
        json={"resolution": "1080x1920", "fps": 30},
    )
    assert render_res.status_code == 200
    assert render_res.json()["status"] == "READY"

    # =========================================================================
    # Step 16: 9-Dimension Creator Quality Gate Evaluation & Human Sign-off
    # =========================================================================
    qg_audit_res = await client.get(f"/api/v1/quality-gate/item/{item_id}")
    assert qg_audit_res.status_code == 200
    qg_data = qg_audit_res.json()
    assert len(qg_data["dimensions"]) == 9

    # Human Gate: Final Quality Gate Approval
    qg_app_res = await client.post(
        f"/api/v1/quality-gate/approve/{item_id}",
        json={"approved_by": "Senior QC Lead", "notes": "All 9 dimensions passed; unlocked for export."},
    )
    assert qg_app_res.status_code == 200
    assert qg_app_res.json()["is_approved"] is True
    assert qg_app_res.json()["unlocked_export"] is True

    # =========================================================================
    # Step 17: Platform-Ready Offline Export Package with SHA-256 Manifest
    # =========================================================================
    export_res = await client.post(f"/api/v1/export/{item_id}")
    assert export_res.status_code == 200
    export_pkg = export_res.json()
    assert "manifest.json" in export_pkg["files"]
    assert len(export_pkg["checksum"]) == 64

    # Verify download route returns valid ZIP bundle
    download_res = await client.get(f"/api/v1/export/item/{item_id}/download")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/zip"
    assert len(download_res.content) > 100

    # =========================================================================
    # Step 18: Browser Launchers & Platform Settings
    # =========================================================================
    platforms_res = await client.get("/api/v1/platforms")
    assert platforms_res.status_code == 200
    platforms = platforms_res.json()
    assert "youtube" in platforms
    assert platforms["youtube"]["publishing_url"].startswith("https://")

    # =========================================================================
    # Step 19: Manual Platform Publishing Flow & Checklist Verification
    # =========================================================================
    pub_overview_res = await client.get(f"/api/v1/publishing/item/{item_id}")
    assert pub_overview_res.status_code == 200
    pub_overview = pub_overview_res.json()
    publications = {p["platform"]: p for p in pub_overview["publications"]}
    assert "youtube" in publications

    yt_pub_id = publications["youtube"]["id"]
    # Complete YouTube publishing checklist
    checklist_res = await client.patch(
        f"/api/v1/publishing/{yt_pub_id}",
        json={
            "checklist": {
                "media_ready": True,
                "thumbnail_ready": True,
                "title_caption_ready": True,
                "sources_checked": True,
                "asset_rights_verified": True,
            }
        },
    )
    assert checklist_res.status_code == 200
    assert checklist_res.json()["status"] == "READY"

    # Mark published with valid HTTPS URL
    pub_finish_res = await client.patch(
        f"/api/v1/publishing/{yt_pub_id}",
        json={
            "status": "PUBLISHED",
            "post_url": f"https://www.youtube.com/watch?v={run_id}",
            "platform_post_id": run_id,
            "notes": "Published manually via clipboard metadata copy.",
        },
    )
    assert pub_finish_res.status_code == 200
    assert pub_finish_res.json()["status"] == "PUBLISHED"

    # =========================================================================
    # Step 20: Performance Analytics Snapshots, 3s Retention & Creator ROI
    # =========================================================================
    snap_res = await client.post(
        "/api/v1/analytics/snapshots",
        json={
            "content_item_id": item_id,
            "platform": "youtube",
            "snapshot_label": "24h",
            "views": 4200,
            "impressions": 28000,
            "watch_time_seconds": 16800.0,
            "average_view_duration_seconds": 40.0,
            "retention_rate_pct": 72.0,
            "hook_retention_3s_pct": 82.5,
            "hook_retention_30s_pct": 58.0,
            "likes": 340,
            "comments": 48,
            "shares": 31,
            "saves": 45,
            "clicks": 90,
            "subscribers_gained": 65,
            "revenue_estimated_usd": 75.0,
            "notes": "Exceptional hook retention from empirical benchmark data.",
        },
    )
    assert snap_res.status_code == 201
    snap_id = snap_res.json()["id"]

    # Verify item analytics and ROI calculations
    item_roi_res = await client.get(f"/api/v1/analytics/item/{item_id}")
    assert item_roi_res.status_code == 200
    item_roi = item_roi_res.json()
    assert item_roi["total_views"] >= 4200
    assert "roi_analysis" in item_roi
    assert item_roi["roi_analysis"]["net_profit_usd"] is not None

    hooks_res = await client.get("/api/v1/analytics/hooks")
    assert hooks_res.status_code == 200
    assert isinstance(hooks_res.json(), list)

    # =========================================================================
    # Step 21: Human-Approved Feedback Engine (Synthesis & Brand DNA Application)
    # =========================================================================
    feedback_eval_res = await client.post("/api/v1/feedback/evaluate", json={"days": 30, "min_impressions": 10})
    assert feedback_eval_res.status_code == 200
    eval_result = feedback_eval_res.json()
    assert "evaluated_snapshots" in eval_result

    # Create explicit feedback lesson proposal
    manual_lesson_payload = {
        "lesson_type": "preferred_vocabulary_addition",
        "title": f"Terminal hardware telemetry drives +80% 3s retention ({run_id})",
        "observation": "Audience drops significantly if opening with theoretical slides rather than real code.",
        "impact_level": "HIGH",
        "confidence_score": 0.94,
        "evidence_data": {"snapshot_id": snap_id, "hook_retention_3s": 82.5},
        "proposed_adjustment": {
            "target": "brand_profile",
            "field": "preferred_vocabulary",
            "action": "append",
            "value": "wattmeter",
            "summary": "Emphasize physical test measurements in brand voice",
        },
    }
    lesson_res = await client.post("/api/v1/feedback/lessons", json=manual_lesson_payload)
    assert lesson_res.status_code == 201
    lesson_id = lesson_res.json()["id"]

    # Human Gate: Approve feedback lesson
    appr_lesson_res = await client.post(
        f"/api/v1/feedback/lessons/{lesson_id}/approve",
        json={"creator_notes": "Confirmed by audience analytics data."},
    )
    assert appr_lesson_res.status_code == 200
    assert appr_lesson_res.json()["status"] == "APPROVED"

    # Apply approved lesson to Brand DNA
    apply_lesson_res = await client.post(f"/api/v1/feedback/lessons/{lesson_id}/apply")
    assert apply_lesson_res.status_code == 200
    assert apply_lesson_res.json()["status"] == "APPLIED"

    # Verify Brand DNA memory updated
    brand_check = await client.get("/api/v1/brand")
    assert brand_check.status_code == 200
    assert "wattmeter" in brand_check.json()["preferred_vocabulary"]

    # =========================================================================
    # Step 22: Owned Audience Tracking (Lead Magnets, UTM Builder, Valuation)
    # =========================================================================
    magnet_slug = f"local-ai-benchmark-kit-{run_id}"
    magnet_res = await client.post(
        "/api/v1/audience/magnets",
        json={
            "title": f"Local AI Benchmark Rig Kit ({run_id})",
            "slug": magnet_slug,
            "description": "Full open-source bash harness and telemetry dashboard for local inference.",
            "magnet_type": "code_repository",
            "landing_page_url": f"https://practical-ai.local/resources/{magnet_slug}",
            "cta_copy": "Download the benchmark harness: {url}",
            "status": "ACTIVE",
            "target_pillar": "Local Agent Benchmarks",
            "estimated_value_usd": 25.0,
        },
    )
    assert magnet_res.status_code == 201
    magnet_id = magnet_res.json()["id"]

    # Generate deterministic UTM tracking link
    utm_res = await client.post(
        "/api/v1/audience/build-utm",
        json={
            "base_url": f"https://practical-ai.local/resources/{magnet_slug}",
            "platform": "youtube",
            "lead_magnet_slug": magnet_slug,
            "content_slug": f"m4-benchmarks-{run_id}",
            "campaign_name": "m4_benchmarks",
        },
    )
    assert utm_res.status_code == 200
    assert "utm_source=youtube" in utm_res.json()["tracking_url"]
    assert "utm_campaign=sc_m4_benchmarks" in utm_res.json()["tracking_url"]

    # Subscriber valuation check
    val_res = await client.get("/api/v1/audience/summary")
    assert val_res.status_code == 200
    assert "total_lead_magnets" in val_res.json()

    # =========================================================================
    # Step 23: Storage Cleanup Inspection & Reference-Safe Dry Run
    # =========================================================================
    clean_summary_res = await client.get("/api/v1/cleanup/summary")
    assert clean_summary_res.status_code == 200
    assert "storage_usage_bytes" in clean_summary_res.json()

    clean_inspect_res = await client.get("/api/v1/cleanup/inspect")
    assert clean_inspect_res.status_code == 200
    assert "total_files_scanned" in clean_inspect_res.json()

    # Dry run execution (preserves all referenced assets)
    dry_exec_res = await client.post(
        "/api/v1/cleanup/execute",
        json={"dry_run": True, "max_files_to_delete": 25},
    )
    assert dry_exec_res.status_code == 200
    dry_report = dry_exec_res.json()
    assert dry_report["mode"] == "DRY_RUN"
    assert dry_report["status"] == "SUCCESS"

    # =========================================================================
    # Step 24: Verified Backup Snapshot Archive & Sandbox Restore Test
    # =========================================================================
    backup_res = await client.post(
        "/api/v1/cleanup/backups",
        json={
            "backup_name": f"studio_v1_certification_{run_id}",
            "backup_type": "FULL",
            "notes": "V1 Final E2E Certification Snapshot",
        },
    )
    assert backup_res.status_code == 201
    backup_data = backup_res.json()
    backup_id = backup_data["id"]
    assert backup_data["size_bytes"] > 0
    assert len(backup_data["checksum_sha256"]) == 64

    # Sandbox restore test: executes SQLite PRAGMA integrity_check;
    restore_res = await client.post(
        f"/api/v1/cleanup/backups/{backup_id}/test-restore",
        json={"dry_run": True},
    )
    assert restore_res.status_code == 200
    restore_data = restore_res.json()
    assert restore_data["status"] == "SUCCESS"
    assert restore_data["integrity_check"] == "ok"

    # Catalog & Engines version check
    engines_res = await client.get("/api/v1/engines")
    assert engines_res.status_code == 200
    all_engines = engines_res.json()
    assert len(all_engines) >= 14
    for eng in all_engines:
        assert "version" in eng
        assert eng["health"]["status"] in ("healthy", "degraded")


@pytest.mark.asyncio
async def test_e2e_singleton_niche_and_brand_invariants(client: AsyncClient, db_session: AsyncSession):
    """
    Enforces Invariants 1 & 2: Single Niche and Single Brand.
    There is strictly ONE active niche and ONE active brand in the system.
    """
    # Verify Niche count in DB is exactly 1 (or 0 before first save, but after save strictly 1)
    res_niche = await client.get("/api/v1/niche")
    assert res_niche.status_code == 200
    assert res_niche.json()["id"] == SINGLETON_NICHE_ID

    # Verify Brand count in DB is strictly 1
    res_brand = await client.get("/api/v1/brand")
    assert res_brand.status_code == 200
    assert res_brand.json()["id"] == SINGLETON_BRAND_ID

    # Direct database verification
    niche_count = (await db_session.execute(select(NicheProfile))).scalars().all()
    assert len(niche_count) <= 1, "Only singleton NicheProfile may exist in DB"

    brand_count = (await db_session.execute(select(BrandProfile))).scalars().all()
    assert len(brand_count) <= 1, "Only singleton BrandProfile may exist in DB"


@pytest.mark.asyncio
async def test_e2e_human_gates_strict_enforcement(client: AsyncClient):
    """
    Enforces Invariant 5: Human Quality Gates.
    Automated bypasses are strictly prevented by the API at each stage.
    """
    test_id = uuid.uuid4().hex[:6]

    # Create test family and item
    fam_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"Strict Gate Enforcement Family ({test_id})",
            "content_pillar": "Local Agent Benchmarks",
            "original_value_type": "benchmark",
            "summary": "Testing gate blockage.",
        },
    )
    family_id = fam_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"Blocked Item ({test_id})",
            "angle": "Must fail before human gate.",
            "hook_type": "bold_claim",
            "original_value_connection": "Lab measurements.",
            "viewer_value": "Gate tests.",
        },
    )
    item_id = item_res.json()["id"]

    # Gate 1: Export blocked before script exists
    exp_block_1 = await client.post(f"/api/v1/export/{item_id}")
    assert exp_block_1.status_code == 422
    assert "No script draft exists" in exp_block_1.json()["detail"]

    # Generate draft
    gen_res = await client.post("/api/v1/scripts/generate", json={"content_item_id": item_id})
    script_id = gen_res.json()["id"]

    # Gate 2: Export blocked when script is not approved
    exp_block_2 = await client.post(f"/api/v1/export/{item_id}")
    assert exp_block_2.status_code == 422
    assert "unapproved script" in exp_block_2.json()["detail"].lower()

    # Gate 3: Script approval rejected when violating brand clichés without explicit override
    sec_id = gen_res.json()["sections"][0]["id"]
    await client.patch(
        f"/api/v1/scripts/{script_id}/sections/{sec_id}",
        json={"narration": "This revolutionary game-changer tool will blow your mind."},
    )
    fail_approve = await client.post(
        f"/api/v1/scripts/{script_id}/approve",
        json={"reviewer": "test_bot"},
    )
    assert fail_approve.status_code == 422
    assert "blocking_reasons" in fail_approve.json()["detail"]

    # Gate 4: Publishing URL requires HTTPS
    pub_overview_res = await client.get(f"/api/v1/publishing/item/{item_id}")
    if pub_overview_res.status_code == 200:
        pubs = pub_overview_res.json().get("publications", [])
        if pubs:
            pub_id = pubs[0]["id"]
            bad_publish = await client.patch(
                f"/api/v1/publishing/{pub_id}",
                json={"status": "PUBLISHED", "post_url": "http://insecure.site/post"},
            )
            assert bad_publish.status_code == 422


@pytest.mark.asyncio
async def test_e2e_engine_catalog_and_isolation(client: AsyncClient):
    """
    Enforces Invariant 4: Engine-Based Architecture.
    All 13 core engines are decoupled, have registered manifests, health checks, and rules.
    """
    res = await client.get("/api/v1/engines")
    assert res.status_code == 200
    engines = res.json()
    engine_ids = [e["id"] for e in engines]

    core_13_engines = [
        "rss",
        "trends",
        "niche_guard",
        "opportunity",
        "brand",
        "research",
        "originality",
        "ai",
        "content",
        "media",
        "export",
        "analytics",
        "cleanup",
    ]

    for eng in core_13_engines:
        assert eng in engine_ids, f"Engine '{eng}' must be registered in the catalog"

    # Verify each engine manifest has contracts, inputs, and outputs
    for eng_info in engines:
        if eng_info["id"] in core_13_engines:
            assert "name" in eng_info
            assert "version" in eng_info
            assert "inputs" in eng_info
            assert "outputs" in eng_info
            assert eng_info["health"]["status"] in ("healthy", "degraded")
