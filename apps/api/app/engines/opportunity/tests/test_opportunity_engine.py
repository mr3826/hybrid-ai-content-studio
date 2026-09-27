import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.engines.core.base import EngineContext
from app.engines.opportunity.engine import OpportunityEngine
from app.engines.opportunity.evaluator import (
    build_opportunity_item,
    calculate_opportunity_score,
)
from app.models.brand import BrandMemoryItem, BrandProfile
from app.models.niche import NicheProfile
from app.models.opportunity import Opportunity
from app.repositories.opportunity_repository import OpportunityRepository


def test_manifest_and_health():
    engine = OpportunityEngine()
    assert engine.id == "opportunity"
    assert engine.version == "1.0.0"
    health = engine.health()
    assert health.status == "healthy"
    assert "weights" in health.details
    assert "penalties" in health.details


def test_10_dimension_scoring_dimensions():
    rules = {
        "weights": {
            "niche_fit": 18.0,
            "original_value": 20.0,
            "audience_usefulness": 15.0,
            "evergreen_value": 12.0,
            "trend_momentum": 10.0,
            "commercial_fit": 10.0,
            "content_family_potential": 5.0,
            "sponsor_relevance": 3.0,
            "production_effort": 4.0,
        },
        "penalties": {
            "saturation_penalty_max": 25.0,
            "saturation_window_days": 30,
        },
    }

    niche = NicheProfile(
        name="Local AI Engineering",
        allowed_topics=["local llms", "quantization", "vllm", "benchmarking"],
        primary_problems=["high latency", "gpu vram limits", "inference costs"],
        commercial_intent_topics=["workstations", "nvidia gpus", "cloud vs local"],
        evergreen_topics=["architecture guides", "how to optimize inference"],
        negative_keywords=["crypto", "nft"],
        content_pillars=[{"id": "p1", "name": "Local LLM Benchmarks"}],
    )

    breakdown, meta = calculate_opportunity_score(
        title="vLLM v0.7 Released: Groundbreaking Latency and Memory Benchmarks",
        summary="Empirical benchmarks show 2.5x higher throughput on local consumer hardware.",
        pillar="Local LLM Benchmarks",
        trend_score=85.0,
        niche=niche,
        brand=None,
        brand_memory=[],
        rules=rules,
    )

    # Niche fit should be high (matched allowed topic & pillar)
    assert breakdown.niche_fit >= 15.0
    # Original test potential should be high (benchmark, latency, memory, benchmarks)
    assert breakdown.original_value >= 14.0
    # Audience usefulness should match latency & vram problems
    assert breakdown.audience_usefulness >= 10.0
    # Trend momentum (85% of 10)
    assert breakdown.trend_momentum == pytest.approx(8.5, rel=1e-1)
    # Total score should be strong (> 75)
    assert breakdown.final_score >= 70.0
    assert meta["recommended_action"] == "Research"
    assert "Benchmark" in meta["suggested_content_family"]


def test_saturation_penalty_applied():
    rules = {
        "weights": {
            "niche_fit": 18.0,
            "original_value": 20.0,
            "audience_usefulness": 15.0,
            "evergreen_value": 12.0,
            "trend_momentum": 10.0,
            "commercial_fit": 10.0,
            "content_family_potential": 5.0,
            "sponsor_relevance": 3.0,
            "production_effort": 4.0,
        },
        "penalties": {
            "saturation_penalty_max": 25.0,
            "saturation_window_days": 30,
        },
    }

    # Simulate recent channel memory published 3 days ago on exact topic
    recent_memory = BrandMemoryItem(
        id=str(uuid.uuid4()),
        memory_type="topic",
        content="vLLM v0.7 Latency and Memory Benchmarks on RTX 4090",
        context_note="benchmarking memory throughput",
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )

    breakdown_clean, _ = calculate_opportunity_score(
        title="vLLM Latency and Memory Benchmarks Comparison",
        summary="Detailed benchmarks testing memory optimization.",
        pillar=None,
        trend_score=70.0,
        niche=None,
        brand=None,
        brand_memory=[],
        rules=rules,
    )

    breakdown_saturated, meta_saturated = calculate_opportunity_score(
        title="vLLM Latency and Memory Benchmarks Comparison",
        summary="Detailed benchmarks testing memory optimization.",
        pillar=None,
        trend_score=70.0,
        niche=None,
        brand=None,
        brand_memory=[recent_memory],
        rules=rules,
    )

    # Saturation penalty should be applied
    assert breakdown_saturated.saturation_penalty >= 15.0
    assert breakdown_saturated.final_score < breakdown_clean.final_score
    assert any("fatigue" in r.lower() or "saturation" in r.lower() for r in meta_saturated["risks"])


@pytest.mark.asyncio
async def test_human_gate_actions():
    async with AsyncSessionLocal() as session:
        repo = OpportunityRepository(session)
        test_slug = f"test-opp-{uuid.uuid4().hex[:8]}"

        item = build_opportunity_item(
            topic="DeepSeek R1 Model Architecture Teardown",
            summary="Technical paper analysis examining reasoning reinforcement learning.",
            pillar="Architecture",
            trend_score=80.0,
        )
        item.slug = test_slug
        opp = await repo.upsert_opportunity(item)
        assert opp.status == "needs_review"

        # 1. Action: Watch
        watched = await repo.update_status(opp.id, status="watching")
        assert watched.status == "watching"
        assert watched.reviewed_at is not None

        # 2. Action: Approve for Research
        approved = await repo.update_status(opp.id, status="research_ready")
        assert approved.status == "research_ready"

        # 3. Action: Reject
        rejected = await repo.update_status(opp.id, status="rejected", rejection_reason="Too theoretical for V1")
        assert rejected.status == "rejected"
        assert rejected.rejection_reason == "Too theoretical for V1"


@pytest.mark.asyncio
async def test_engine_run_and_dry_run():
    engine = OpportunityEngine()
    test_id = uuid.uuid4().hex[:8]

    custom_topics = [
        {
            "topic": f"LangGraph Multi-Agent Orchestration Patterns {test_id}",
            "summary": "Hands-on benchmark comparing state machines vs reactive agent loops.",
            "pillar": "Agentic AI",
            "trend_score": 78.0,
        }
    ]

    # Dry run
    dry_context = EngineContext(
        run_id=f"dry_{test_id}",
        dry_run=True,
        parameters={"custom_topics": custom_topics, "include_candidates": False, "include_trends": False},
    )
    dry_res = await engine.dry_run(dry_context)
    assert dry_res.success is True
    assert dry_res.output_count >= 1

    # Check not in database
    async with AsyncSessionLocal() as session:
        stmt = select(Opportunity).where(Opportunity.slug.like(f"%{test_id}%"))
        res = await session.execute(stmt)
        assert res.scalar_one_or_none() is None

    # Full Run
    run_context = EngineContext(
        run_id=f"run_{test_id}",
        dry_run=False,
        parameters={"custom_topics": custom_topics, "include_candidates": False, "include_trends": False},
    )
    run_res = await engine.run(run_context)
    assert run_res.success is True
    assert run_res.output_count >= 1

    # Check written to database
    async with AsyncSessionLocal() as session:
        stmt = select(Opportunity).where(Opportunity.slug.like(f"%{test_id}%"))
        res = await session.execute(stmt)
        opp = res.scalar_one_or_none()
        assert opp is not None
        assert opp.opportunity_score > 0.0
        assert opp.status == "needs_review"


def test_zero_ai_calls():
    """Verify that Opportunity evaluation runs deterministically without paid AI calls."""
    item = build_opportunity_item(
        topic="PyTorch 2.6 TensorRT Acceleration",
        summary="Speed comparisons on consumer GPUs.",
        pillar="Hardware Acceleration",
        trend_score=75.0,
    )
    assert item.opportunity_score > 0.0
    assert item.suggested_original_angle != ""
    assert item.suggested_content_family != ""
