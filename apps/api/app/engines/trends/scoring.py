import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.engines.trends.adapters.rss_signals import extract_entities_and_keywords
from app.engines.trends.contracts import (
    TopicSignal,
    TrendCluster,
    TrendExplanation,
    TrendScoreBreakdown,
)


def slugify_topic(title: str) -> str:
    """Generate clean slug identifier for a topic cluster."""
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower()).strip()
    slug = re.sub(r'[\s-]+', '-', clean)
    return slug[:80] or "trend-topic"


def cluster_signals(
    signals: List[TopicSignal],
    similarity_threshold: float = 0.35,
) -> List[List[TopicSignal]]:
    """Group signals into clusters based on shared keywords and entities deterministically."""
    if not signals:
        return []

    clusters: List[List[TopicSignal]] = []

    for signal in signals:
        placed = False
        sig_entities = set(e.lower() for e in signal.entities)
        sig_words = set(re.findall(r'\b[a-z0-9_-]{3,}\b', signal.title.lower()))

        for cluster in clusters:
            # Check overlap against cluster's aggregate entities
            cluster_entities: Set[str] = set()
            cluster_words: Set[str] = set()
            for s in cluster:
                cluster_entities.update(e.lower() for e in s.entities)
                cluster_words.update(re.findall(r'\b[a-z0-9_-]{3,}\b', s.title.lower()))

            # Jaccard on entities if available
            entity_overlap = 0.0
            if sig_entities and cluster_entities:
                intersection = sig_entities.intersection(cluster_entities)
                union = sig_entities.union(cluster_entities)
                entity_overlap = len(intersection) / len(union) if union else 0.0

            # Jaccard on title words
            word_overlap = 0.0
            if sig_words and cluster_words:
                w_intersection = sig_words.intersection(cluster_words)
                w_union = sig_words.union(cluster_words)
                word_overlap = len(w_intersection) / len(w_union) if w_union else 0.0

            match_score = max(entity_overlap * 1.2, word_overlap)

            # Direct entity match check (if they share 2+ exact entities, automatic cluster)
            shared_entities_count = len(sig_entities.intersection(cluster_entities))

            if match_score >= similarity_threshold or shared_entities_count >= 2:
                cluster.append(signal)
                placed = True
                break

        if not placed:
            clusters.append([signal])

    return clusters


def format_time_ago(dt: datetime, ref_time: datetime) -> str:
    """Format timestamp into human-readable recency string e.g. '42m ago', '3h ago'."""
    delta = ref_time - dt
    total_seconds = max(0, int(delta.total_seconds()))
    minutes = total_seconds // 60
    hours = total_seconds // 3600
    days = total_seconds // 86400

    if minutes < 60:
        return f"{max(1, minutes)}m ago"
    elif hours < 24:
        return f"{hours}h ago"
    else:
        return f"{days}d ago"


def calculate_trend_score(
    signals: List[TopicSignal],
    rules: Dict[str, Any],
    now: Optional[datetime] = None,
    baseline_velocity: Optional[float] = None,
    manual_boost: float = 1.0,
    is_suppressed: bool = False,
    override_first_seen: Optional[datetime] = None,
) -> Tuple[TrendScoreBreakdown, TrendExplanation, float, float]:
    """Compute transparent multi-factor trend momentum score and explainability."""
    if now is None:
        now = datetime.now(timezone.utc)

    weights = rules.get("weights", {})
    w_mentions = float(weights.get("mentions_weight", 0.25))
    w_velocity = float(weights.get("velocity_weight", 0.30))
    w_recency = float(weights.get("recency_weight", 0.20))
    w_authority = float(weights.get("authority_weight", 0.15))
    w_diversity = float(weights.get("diversity_weight", 0.10))

    thresholds = rules.get("thresholds", {})
    recency_half_life = float(thresholds.get("recency_half_life_hours", 12.0))

    # 1. Cross-Source Mentions
    mention_count = len(signals)
    # Logarithmic-linear curve to reward multi-mentions
    base_mentions_score = min(100.0, mention_count * 20.0)

    # 2. Source Diversity
    distinct_sources = set(s.source_name for s in signals)
    distinct_count = len(distinct_sources)
    if mention_count <= 1:
        source_diversity_score = 50.0
        diversity_ratio = 1.0
    else:
        diversity_ratio = distinct_count / mention_count
        source_diversity_score = min(100.0, (distinct_count / max(1, min(5, mention_count))) * 100.0)

    # 3. Source Authority
    avg_authority = sum(s.trust_weight for s in signals) / max(1, mention_count)
    source_authority_score = min(100.0, avg_authority * 100.0)

    # 4. First-Seen Recency
    if override_first_seen:
        first_seen_at = override_first_seen
    else:
        first_seen_at = min((s.published_at for s in signals), default=now)

    age_seconds = max(60.0, (now - first_seen_at).total_seconds())
    age_hours = age_seconds / 3600.0
    recency_decay = math.pow(2, -age_hours / max(1.0, recency_half_life))
    recency_score = min(100.0, recency_decay * 100.0)

    # 5. Mention Velocity & Historical Baseline
    # Mentions per hour:
    effective_hours = max(0.5, age_hours)
    velocity = mention_count / effective_hours

    # Baseline comparison
    if baseline_velocity is None or baseline_velocity <= 0:
        default_mentions_per_day = float(rules.get("baseline", {}).get("default_mentions_per_day", 1.0))
        baseline_velocity = default_mentions_per_day / 24.0

    velocity_ratio = (velocity - baseline_velocity) / max(0.01, baseline_velocity)
    # Velocity score (scaled so 1.0/hr is 50 pts, 3.0/hr is 90 pts)
    velocity_score = min(100.0, max(0.0, 30.0 + (velocity * 25.0)))
    momentum_score = min(100.0, max(0.0, 50.0 + (velocity_ratio * 25.0)))

    # 6. Weighted Sum & Boost
    raw_score = (
        (w_mentions * base_mentions_score)
        + (w_velocity * velocity_score)
        + (w_recency * recency_score)
        + (w_authority * source_authority_score)
        + (w_diversity * source_diversity_score)
    )

    if is_suppressed:
        final_score = 0.0
    else:
        final_score = min(100.0, max(0.0, raw_score * manual_boost))

    # 7. Formatted Explainability
    mentions_text = f"{mention_count} independent mention{'s' if mention_count != 1 else ''}"
    sources_text = f"{distinct_count} trusted source{'s' if distinct_count != 1 else ''}"
    recency_text = f"first seen {format_time_ago(first_seen_at, now)}"
    velocity_text = f"{velocity:.1f} mentions/hr"

    pct_baseline = int(round(velocity_ratio * 100))
    if pct_baseline >= 0:
        baseline_text = f"+{pct_baseline}% vs baseline"
    else:
        baseline_text = f"{pct_baseline}% vs baseline"

    summary = f"{mentions_text} across {sources_text}; {recency_text}; {baseline_text}"

    breakdown = TrendScoreBreakdown(
        base_mentions_score=round(base_mentions_score, 2),
        source_diversity_score=round(source_diversity_score, 2),
        source_authority_score=round(source_authority_score, 2),
        recency_score=round(recency_score, 2),
        velocity_score=round(velocity_score, 2),
        baseline_ratio=round(velocity_ratio, 2),
        manual_boost=round(manual_boost, 2),
        is_suppressed=is_suppressed,
        raw_score=round(raw_score, 2),
        final_score=round(final_score, 2),
    )

    topic_title = signals[0].title if signals else "Trend Topic"
    slug = slugify_topic(topic_title)

    explanation = TrendExplanation(
        topic_key=slug,
        title=topic_title,
        summary=summary,
        mentions_text=mentions_text,
        sources_text=sources_text,
        recency_text=recency_text,
        baseline_text=baseline_text,
        velocity_text=velocity_text,
        breakdown=breakdown,
    )

    return breakdown, explanation, final_score, momentum_score


def build_trend_cluster(
    signals: List[TopicSignal],
    rules: Dict[str, Any],
    now: Optional[datetime] = None,
    manual_boost: float = 1.0,
    is_suppressed: bool = False,
    historical_baseline: float = 1.0,
    override_first_seen: Optional[datetime] = None,
) -> TrendCluster:
    """Build a complete TrendCluster from a group of signals."""
    if now is None:
        now = datetime.now(timezone.utc)

    # Sort signals descending by published_at
    signals_sorted = sorted(signals, key=lambda s: s.published_at, reverse=True)
    first_seen_at = override_first_seen or min(s.published_at for s in signals_sorted)
    last_seen_at = max(s.published_at for s in signals_sorted)

    # Representative title: choose the signal with highest trust_weight or longest title
    representative = max(signals_sorted, key=lambda s: (s.trust_weight, len(s.title)))
    title = representative.title
    summary = representative.summary or title
    pillar = representative.pillar

    # Extract consolidated keywords
    combined_text = " ".join(f"{s.title} {s.summary}" for s in signals_sorted)
    keywords = extract_entities_and_keywords(combined_text, max_keywords=6)

    # Compute baseline velocity
    baseline_velocity = historical_baseline / 24.0

    breakdown, explanation, trend_score, momentum_score = calculate_trend_score(
        signals=signals_sorted,
        rules=rules,
        now=now,
        baseline_velocity=baseline_velocity,
        manual_boost=manual_boost,
        is_suppressed=is_suppressed,
        override_first_seen=first_seen_at,
    )

    age_hours = max(0.5, (now - first_seen_at).total_seconds() / 3600.0)
    velocity = len(signals_sorted) / age_hours

    distinct_sources = set(s.source_name for s in signals_sorted)
    source_diversity = len(distinct_sources) / max(1, len(signals_sorted))
    source_authority = sum(s.trust_weight for s in signals_sorted) / max(1, len(signals_sorted))

    slug = slugify_topic(title)

    # Status classification
    if is_suppressed:
        status = "archived"
    elif breakdown.baseline_ratio >= 1.5 or trend_score >= 80.0:
        status = "emerging"
    elif trend_score >= 50.0:
        status = "active"
    else:
        status = "cooling"

    return TrendCluster(
        topic_key=slug,
        title=title,
        summary=summary,
        pillar=pillar,
        keywords=keywords,
        signals=signals_sorted,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
        mention_count=len(signals_sorted),
        distinct_sources_count=len(distinct_sources),
        velocity=round(velocity, 2),
        velocity_ratio=round(breakdown.baseline_ratio, 2),
        source_diversity_score=round(source_diversity, 2),
        source_authority_score=round(source_authority, 2),
        trend_score=round(trend_score, 2),
        momentum_score=round(momentum_score, 2),
        manual_boost=round(manual_boost, 2),
        is_suppressed=is_suppressed,
        status=status,
        explanation=explanation,
    )
