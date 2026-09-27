import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.engines.opportunity.contracts import (
    OpportunityItem,
    OpportunityScoreBreakdown,
)
from app.models.brand import BrandMemoryItem, BrandProfile
from app.models.niche import NicheProfile


def slugify(title: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower()).strip()
    return re.sub(r'[\s-]+', '-', clean)[:80] or "opportunity-topic"


def calculate_opportunity_score(
    title: str,
    summary: str,
    pillar: Optional[str],
    trend_score: float,
    niche: Optional[NicheProfile],
    brand: Optional[BrandProfile],
    brand_memory: List[BrandMemoryItem],
    rules: Dict[str, Any],
) -> Tuple[OpportunityScoreBreakdown, Dict[str, Any]]:
    """Compute 10-dimensional opportunity intelligence score, original angle, content family, and risks."""
    weights = rules.get("weights", {})
    w_niche = float(weights.get("niche_fit", 18.0))
    w_orig = float(weights.get("original_value", 20.0))
    w_aud = float(weights.get("audience_usefulness", 15.0))
    w_ever = float(weights.get("evergreen_value", 12.0))
    w_trend = float(weights.get("trend_momentum", 10.0))
    w_comm = float(weights.get("commercial_fit", 10.0))
    w_fam = float(weights.get("content_family_potential", 5.0))
    w_spon = float(weights.get("sponsor_relevance", 3.0))
    w_eff = float(weights.get("production_effort", 4.0))

    penalties = rules.get("penalties", {})
    max_sat_pen = float(penalties.get("saturation_penalty_max", 25.0))
    sat_window_days = int(penalties.get("saturation_window_days", 30))

    text_lower = f"{title} {summary}".lower()
    words = set(re.findall(r'\b[a-z0-9_-]{3,}\b', text_lower))

    # 1. Niche Fit (max 18)
    niche_fit = 10.0  # default baseline
    if niche:
        # Check allowed topics and content pillars
        allowed = set(t.lower() for t in niche.allowed_topics)
        pillars = set(p.get("name", "").lower() for p in niche.content_pillars if isinstance(p, dict))
        if any(a in text_lower for a in allowed) or any(p in text_lower for p in pillars):
            niche_fit = w_niche  # 18.0
        elif pillar:
            niche_fit = 15.0

        # Negative keywords heavy penalty
        if any(neg.lower() in text_lower for neg in niche.negative_keywords):
            niche_fit = max(0.0, niche_fit - 12.0)
    else:
        niche_fit = 14.0

    # 2. Original Test / Value Potential (max 20)
    # Technical benchmarks, speed tests, teardowns, empirical tests score highest
    test_keywords = {
        "benchmark", "performance", "test", "comparison", "speed", "latency",
        "memory", "architecture", "v2", "release", "teardown", "hands-on",
        "quantization", "fine-tuning", "evaluation", "breakthrough", "vs"
    }
    overlap_tests = len(words.intersection(test_keywords))
    orig_ratio = min(1.0, 0.45 + (overlap_tests * 0.2))
    original_value = round(orig_ratio * w_orig, 2)

    # 3. Audience Usefulness (max 15)
    # Solves core problems in the niche
    usefulness_ratio = 0.6
    if niche and niche.primary_problems:
        prob_matches = sum(1 for p in niche.primary_problems if any(w in p.lower() for w in words))
        usefulness_ratio = min(1.0, 0.5 + (prob_matches * 0.25))
    audience_usefulness = round(usefulness_ratio * w_aud, 2)

    # 4. Search / Evergreen Value (max 12)
    evergreen_ratio = 0.5
    if niche and niche.evergreen_topics:
        eg_matches = sum(1 for eg in niche.evergreen_topics if any(w in eg.lower() for w in words))
        evergreen_ratio = min(1.0, 0.4 + (eg_matches * 0.3))
    # Guide / architecture keywords increase evergreen potential
    if any(k in text_lower for k in ["how to", "architecture", "deep dive", "guide", "tutorial", "explained"]):
        evergreen_ratio = min(1.0, evergreen_ratio + 0.3)
    evergreen_value = round(evergreen_ratio * w_ever, 2)

    # 5. Trend Momentum (max 10)
    trend_momentum = round((min(100.0, max(0.0, trend_score)) / 100.0) * w_trend, 2)

    # 6. Commercial / Affiliate Fit (max 10)
    comm_ratio = 0.4
    if niche and niche.commercial_intent_topics:
        comm_matches = sum(1 for c in niche.commercial_intent_topics if any(w in c.lower() for w in words))
        comm_ratio = min(1.0, 0.3 + (comm_matches * 0.35))
    if any(k in text_lower for k in ["tool", "hardware", "gpu", "saas", "cloud", "pricing", "pricing plan", "cost"]):
        comm_ratio = min(1.0, comm_ratio + 0.3)
    commercial_fit = round(comm_ratio * w_comm, 2)

    # 7. Content-Family Potential (max 5)
    # Topics that can yield long-form + short clips + written guide
    family_ratio = 0.7 if overlap_tests >= 1 else 0.5
    content_family_potential = round(family_ratio * w_fam, 2)

    # 8. Sponsor Relevance (max 3)
    sponsor_ratio = 0.6 if commercial_fit > 5.0 else 0.4
    sponsor_relevance = round(sponsor_ratio * w_spon, 2)

    # 9. Production Effort / Economy (max 4)
    # Determine effort tier
    if any(k in text_lower for k in ["benchmark", "hands-on", "teardown", "full pipeline"]):
        production_effort = "high"
        effort_score = 2.5
        est_cost = 0.12
        est_time = 75
    elif any(k in text_lower for k in ["comparison", "deep dive", "architecture"]):
        production_effort = "medium"
        effort_score = 3.5
        est_cost = 0.05
        est_time = 45
    else:
        production_effort = "low"
        effort_score = 4.0
        est_cost = 0.02
        est_time = 25

    # 10. Channel Saturation Penalty (penalty up to 25 pts)
    saturation_penalty = 0.0
    cutoff = datetime.now(timezone.utc) - timedelta(days=sat_window_days)
    recent_memories = []
    for m in brand_memory:
        if m.created_at:
            m_dt = m.created_at if m.created_at.tzinfo else m.created_at.replace(tzinfo=timezone.utc)
            if m_dt >= cutoff:
                recent_memories.append(m)

    for mem in recent_memories:
        content_attr = getattr(mem, "content", "") or ""
        context_attr = getattr(mem, "context_note", "") or ""
        mem_text = f"{content_attr} {context_attr}".lower()
        mem_words = set(re.findall(r'\b[a-z0-9_-]{3,}\b', mem_text))
        overlap = len(words.intersection(mem_words))
        if overlap >= 3:
            # Significant overlap with content covered within past 30 days
            saturation_penalty = min(max_sat_pen, saturation_penalty + 15.0)

    saturation_penalty = round(saturation_penalty, 2)

    # Compute Composite Score
    positive_sum = (
        niche_fit
        + original_value
        + audience_usefulness
        + evergreen_value
        + trend_momentum
        + commercial_fit
        + content_family_potential
        + sponsor_relevance
        + effort_score
    )

    # Normalize to 0 - 100 scale (max possible positive sum = 97)
    normalized_raw = min(100.0, (positive_sum / 97.0) * 100.0)
    final_score = max(0.0, min(100.0, normalized_raw - saturation_penalty))

    breakdown = OpportunityScoreBreakdown(
        niche_fit=round(niche_fit, 2),
        original_value=round(original_value, 2),
        audience_usefulness=round(audience_usefulness, 2),
        evergreen_value=round(evergreen_value, 2),
        trend_momentum=round(trend_momentum, 2),
        commercial_fit=round(commercial_fit, 2),
        content_family_potential=round(content_family_potential, 2),
        sponsor_relevance=round(sponsor_relevance, 2),
        production_effort_score=round(effort_score, 2),
        saturation_penalty=round(saturation_penalty, 2),
        raw_score=round(normalized_raw, 2),
        final_score=round(final_score, 2),
    )

    # Determine Content Family & Original Angle
    if "benchmark" in text_lower or "latency" in text_lower or "speed" in text_lower:
        content_family = "Hands-on Benchmark"
        original_angle = f"Empirical side-by-side benchmark measuring latency, memory usage, and throughput of {title} on consumer hardware."
    elif "architecture" in text_lower or "internals" in text_lower or "paper" in text_lower:
        content_family = "Architecture Teardown"
        original_angle = f"Visual step-by-step architectural breakdown of {title}, unmasking internal tradeoffs that official marketing glosses over."
    elif "vs" in text_lower or "comparison" in text_lower or "alternative" in text_lower:
        content_family = "Tool Comparison"
        original_angle = f"Objective migration guide and feature-matrix stress test comparing {title} with existing industry standards."
    elif "short" in text_lower or effort_score == 4.0:
        content_family = "Quick Take Short"
        original_angle = f"Bite-sized, high-retention breakdown answering the single most pressing question creators have about {title}."
    else:
        content_family = "Deep Dive Video"
        original_angle = f"Practical implementation walkthrough building a complete local-first workflow around {title}."

    # Identify Risks
    risks: List[str] = []
    if "announced" in text_lower or "unveiled" in text_lower:
        risks.append("Vendor claims currently lack third-party independent benchmark verification.")
    if "experimental" in text_lower or "preview" in text_lower or "alpha" in text_lower:
        risks.append("Rapidly shifting API syntax; code snippets may require maintenance.")
    if saturation_penalty > 0:
        risks.append(f"Channel covered closely related topic within past {sat_window_days} days (fatigue risk).")
    if trend_momentum < 3.0:
        risks.append("Low immediate search velocity; relies primarily on evergreen and subscriber distribution.")

    if not risks:
        risks.append("Standard verification needed: confirm claims against official documentation before script approval.")

    # Recommended Action & Why
    if final_score >= 70.0:
        recommended_action = "Research"
        why = (
            f"Strong niche fit ({niche_fit:.1f}/18) with exceptional original test potential ({original_value:.1f}/20). "
            f"Directly addresses audience problem areas with {content_family} potential."
        )
    elif final_score >= 45.0:
        recommended_action = "Watch"
        why = (
            f"Moderate opportunity score ({final_score:.1f}/100). High niche relevance but requires stronger trend momentum "
            f"or further empirical confirmation before committing production resources."
        )
    else:
        recommended_action = "Reject"
        why = (
            f"Sub-threshold score ({final_score:.1f}/100) due to low original test potential or high channel saturation penalty."
        )

    meta = {
        "production_effort": production_effort,
        "estimated_cost": est_cost,
        "estimated_time_minutes": est_time,
        "suggested_original_angle": original_angle,
        "suggested_content_family": content_family,
        "risks": risks,
        "why": why,
        "recommended_action": recommended_action,
    }

    return breakdown, meta


def build_opportunity_item(
    topic: str,
    summary: str,
    pillar: Optional[str],
    trend_score: float,
    candidate_id: Optional[str] = None,
    trend_id: Optional[str] = None,
    niche: Optional[NicheProfile] = None,
    brand: Optional[BrandProfile] = None,
    brand_memory: Optional[List[BrandMemoryItem]] = None,
    rules: Optional[Dict[str, Any]] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
) -> OpportunityItem:
    """Construct a full OpportunityItem with scores, angles, and recommendations."""
    rules = rules or {}
    brand_memory = brand_memory or []

    breakdown, meta = calculate_opportunity_score(
        title=topic,
        summary=summary,
        pillar=pillar,
        trend_score=trend_score,
        niche=niche,
        brand=brand,
        brand_memory=brand_memory,
        rules=rules,
    )

    slug = slugify(topic)

    return OpportunityItem(
        topic=topic,
        slug=slug,
        candidate_id=candidate_id,
        trend_id=trend_id,
        pillar=pillar,
        status="needs_review",
        opportunity_score=breakdown.final_score,
        trend_score=trend_score,
        originality_potential=breakdown.original_value,
        evergreen_value=breakdown.evergreen_value,
        commercial_fit=breakdown.commercial_fit,
        production_effort=meta["production_effort"],
        estimated_cost=meta["estimated_cost"],
        estimated_time_minutes=meta["estimated_time_minutes"],
        suggested_original_angle=meta["suggested_original_angle"],
        suggested_content_family=meta["suggested_content_family"],
        risks=meta["risks"],
        why=meta["why"],
        recommended_action=meta["recommended_action"],
        score_breakdown=breakdown,
        source_references=sources or [],
    )
