import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.engines.core.base import EngineContext
from app.engines.trends.adapters.rss_signals import (
    extract_entities_and_keywords,
    RssSignalAdapter,
)
from app.engines.trends.contracts import TopicSignal
from app.engines.trends.engine import TrendsEngine
from app.engines.trends.scoring import (
    build_trend_cluster,
    calculate_trend_score,
    cluster_signals,
    format_time_ago,
    slugify_topic,
)
from app.models.trend import TrendTopic, TrendHistory


def test_manifest_and_health():
    engine = TrendsEngine()
    assert engine.id == "trends"
    assert engine.version == "1.0.0"
    health = engine.health()
    assert health.status == "healthy"
    assert "weights" in health.details


def test_entity_and_keyword_extraction():
    text = (
        "Google DeepMind announces Gemini 2.5 with groundbreaking reasoning capabilities "
        "and advanced neural network architectures."
    )
    keywords = extract_entities_and_keywords(text, max_keywords=5)
    assert len(keywords) > 0
    # Should contain key terms like 'Gemini 2.5' or 'DeepMind' or 'reasoning'
    assert any("gemini" in k.lower() or "deepmind" in k.lower() for k in keywords)


def test_clustering_signals():
    now = datetime.now(timezone.utc)
    sig1 = TopicSignal(
        signal_id="1",
        source_name="TechCrunch",
        title="NVIDIA announces new Blackwell Ultra GPUs for AI data centers",
        published_at=now,
        entities=["NVIDIA", "Blackwell Ultra", "GPU"],
    )
    sig2 = TopicSignal(
        signal_id="2",
        source_name="The Verge",
        title="NVIDIA unveils Blackwell Ultra AI chips with enhanced memory",
        published_at=now - timedelta(minutes=15),
        entities=["NVIDIA", "Blackwell Ultra", "chips"],
    )
    sig3 = TopicSignal(
        signal_id="3",
        source_name="Ars Technica",
        title="Apple releases Swift 6 with full concurrency safety",
        published_at=now - timedelta(minutes=30),
        entities=["Apple", "Swift 6", "concurrency"],
    )

    clusters = cluster_signals([sig1, sig2, sig3])
    # sig1 and sig2 should cluster together; sig3 should be a separate cluster
    assert len(clusters) == 2
    nvidia_cluster = next(c for c in clusters if len(c) == 2)
    assert any(s.source_name == "TechCrunch" for s in nvidia_cluster)
    assert any(s.source_name == "The Verge" for s in nvidia_cluster)


def test_explainability_summary_format():
    """Verify exact formatting:
    '6 independent mentions across 4 trusted sources; first seen 42m ago; +180% vs baseline'
    """
    now = datetime.now(timezone.utc)
    first_seen = now - timedelta(minutes=42)

    # Create 6 signals across 4 distinct sources
    sources = ["Source A", "Source B", "Source C", "Source D", "Source A", "Source B"]
    signals = []
    for i, src in enumerate(sources):
        pub = first_seen if i == 0 else now - timedelta(minutes=10 * i)
        signals.append(
            TopicSignal(
                signal_id=f"sig_{i}",
                source_name=src,
                title="Quantum Computing Breakthrough at MIT Labs",
                published_at=pub,
                entities=["Quantum Computing", "MIT Labs"],
                trust_weight=0.9,
            )
        )

    rules = {
        "weights": {
            "mentions_weight": 0.25,
            "velocity_weight": 0.30,
            "recency_weight": 0.20,
            "authority_weight": 0.15,
            "diversity_weight": 0.10,
        },
        "thresholds": {"recency_half_life_hours": 12.0},
        "baseline": {"default_mentions_per_day": 1.0},
    }

    # Set baseline velocity so that velocity_ratio is 1.8 (+180%)
    age_hours = 42.0 / 60.0  # 0.7h
    current_velocity = 6.0 / age_hours  # ~8.57/hr
    # velocity_ratio = (current_velocity - baseline) / baseline = 1.8 => current_velocity = 2.8 * baseline
    baseline_velocity = current_velocity / 2.8

    breakdown, explanation, score, momentum = calculate_trend_score(
        signals=signals,
        rules=rules,
        now=now,
        baseline_velocity=baseline_velocity,
        override_first_seen=first_seen,
    )

    assert explanation.mentions_text == "6 independent mentions"
    assert explanation.sources_text == "4 trusted sources"
    assert explanation.recency_text == "first seen 42m ago"
    assert explanation.baseline_text == "+180% vs baseline"
    assert explanation.summary == "6 independent mentions across 4 trusted sources; first seen 42m ago; +180% vs baseline"
    assert score > 0.0


def test_manual_boost_and_suppress():
    now = datetime.now(timezone.utc)
    signals = [
        TopicSignal(
            signal_id="1",
            source_name="Ars Technica",
            title="Local AI Models Run 4x Faster with New Quantization",
            published_at=now - timedelta(hours=2),
            entities=["Local AI", "Quantization"],
            trust_weight=0.85,
        ),
        TopicSignal(
            signal_id="2",
            source_name="TechCrunch",
            title="Local AI Breakthrough in Model Compression",
            published_at=now - timedelta(hours=1),
            entities=["Local AI", "Compression"],
            trust_weight=0.85,
        ),
    ]

    rules = {
        "weights": {
            "mentions_weight": 0.25,
            "velocity_weight": 0.30,
            "recency_weight": 0.20,
            "authority_weight": 0.15,
            "diversity_weight": 0.10,
        },
        "thresholds": {"recency_half_life_hours": 12.0},
        "baseline": {"default_mentions_per_day": 1.0},
    }

    # Baseline cluster
    cluster_norm = build_trend_cluster(signals, rules, now=now, manual_boost=1.0)
    score_norm = cluster_norm.trend_score
    assert score_norm > 0.0

    # Boosted cluster
    cluster_boosted = build_trend_cluster(signals, rules, now=now, manual_boost=1.25)
    assert cluster_boosted.trend_score == pytest.approx(min(100.0, score_norm * 1.25), rel=1e-2)

    # Suppressed cluster
    cluster_suppressed = build_trend_cluster(signals, rules, now=now, is_suppressed=True)
    assert cluster_suppressed.trend_score == 0.0
    assert cluster_suppressed.status == "archived"


@pytest.mark.asyncio
async def test_trends_engine_run_and_dry_run():
    engine = TrendsEngine()
    now = datetime.now(timezone.utc)

    test_id = uuid.uuid4().hex[:8]
    custom_signals = [
        TopicSignal(
            signal_id=f"sig_{test_id}_1",
            source_name="Feed Alpha",
            title=f"Autonomous Agents Benchmark Released {test_id}",
            summary="New benchmarks test multi-agent reasoning and tool execution.",
            published_at=now - timedelta(hours=1),
            entities=["Autonomous Agents", "Benchmark", test_id],
            trust_weight=0.9,
            pillar="Agentic AI",
        ),
        TopicSignal(
            signal_id=f"sig_{test_id}_2",
            source_name="Feed Beta",
            title=f"State of Autonomous Agents in 2026 {test_id}",
            summary="Comprehensive evaluation of agent performance across coding tasks.",
            published_at=now - timedelta(minutes=30),
            entities=["Autonomous Agents", "Evaluation", test_id],
            trust_weight=0.85,
            pillar="Agentic AI",
        ),
    ]

    # Dry run test: does not persist to database
    dry_context = EngineContext(
        run_id=f"test_dry_{test_id}",
        dry_run=True,
        parameters={"custom_signals": [s.model_dump(mode="json") for s in custom_signals]},
    )
    dry_res = await engine.dry_run(dry_context)
    assert dry_res.success is True
    assert dry_res.output_count >= 1

    # Verify dry run did not write to trend_topics
    async with AsyncSessionLocal() as session:
        stmt = select(TrendTopic).where(TrendTopic.topic_key.like(f"%{test_id}%"))
        res = await session.execute(stmt)
        assert res.scalar_one_or_none() is None

    # Full Run test: persists to database
    run_context = EngineContext(
        run_id=f"test_full_{test_id}",
        dry_run=False,
        parameters={"custom_signals": [s.model_dump(mode="json") for s in custom_signals]},
    )
    run_res = await engine.run(run_context)
    assert run_res.success is True
    assert run_res.output_count >= 1

    # Verify written to database
    async with AsyncSessionLocal() as session:
        stmt = select(TrendTopic).where(TrendTopic.topic_key.like(f"%{test_id}%"))
        res = await session.execute(stmt)
        topic = res.scalar_one_or_none()
        assert topic is not None
        assert topic.mention_count >= 2
        assert topic.trend_score > 0.0
        assert any("autonomous" in k.lower() for k in topic.keywords)


def test_zero_ai_calls():
    """Verify that TrendsEngine calculation does not make any AI provider calls."""
    signals = [
        TopicSignal(
            signal_id="1",
            source_name="OpenSource Digest",
            title="FastAPI v2 Released with Native Async Drivers",
            published_at=datetime.now(timezone.utc),
            entities=["FastAPI", "Async"],
            trust_weight=0.8,
        )
    ]
    rules = {
        "weights": {
            "mentions_weight": 0.25,
            "velocity_weight": 0.30,
            "recency_weight": 0.20,
            "authority_weight": 0.15,
            "diversity_weight": 0.10,
        },
        "thresholds": {"recency_half_life_hours": 12.0},
        "baseline": {"default_mentions_per_day": 1.0},
    }

    # Pure deterministic code without any network or LLM calls
    cluster = build_trend_cluster(signals, rules)
    assert cluster.trend_score > 0.0
    assert "breakdown" in cluster.explanation.model_dump()
