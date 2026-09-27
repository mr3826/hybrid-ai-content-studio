import pytest
from app.engines.core.base import EngineContext
from app.engines.content_family.engine import ContentFamilyEngine


def test_content_family_manifest_and_health():
    engine = ContentFamilyEngine()
    health = engine.health()
    assert health.status == "healthy"
    assert health.details["has_manifest"] is True
    assert health.details["has_rules"] is True
    assert health.details["supported_formats"] >= 5
    assert health.details["supported_platforms"] >= 5


def test_suggest_children_proposals():
    engine = ContentFamilyEngine()
    claims = [
        {"id": "c1", "text": "DeepSeek-14B achieves 48.2 tokens/sec on M4 Max"},
        {"id": "c2", "text": "Local execution cost is $0.00 vs $0.08 per 1k tokens on cloud API"},
        {"id": "c3", "text": "Metal memory allocation spills to swap at 32k context size"},
    ]
    result = engine.suggest_children(
        family_title="DeepSeek-14B Apple Silicon Benchmark",
        topic="DeepSeek-14B on M4 Max",
        originality_type="benchmark",
        what_are_we_adding="Side-by-side prompt ingestion & generation throughput benchmarks across 5 iterations on local unified memory.",
        claims=claims,
        brand_name="Local AI Studio",
        content_pillar="Local Hardware",
    )

    assert result.family_title == "DeepSeek-14B Apple Silicon Benchmark"
    assert len(result.proposals) >= 4

    formats = [p.format for p in result.proposals]
    assert "youtube_long" in formats
    assert "short_vertical" in formats
    assert "social_post" in formats
    assert "newsletter" in formats

    # Verify each child has distinct angles, hooks, and originality connections
    hooks = [p.hook_type for p in result.proposals]
    assert len(set(hooks)) >= 3  # Diverse hooks

    for p in result.proposals:
        assert len(p.working_title) > 5
        assert len(p.angle) >= 15
        assert len(p.original_value_connection) > 0
        assert len(p.viewer_value) > 0


def test_suggest_children_anti_clone_repetition_prevention():
    engine = ContentFamilyEngine()
    recent_items = [
        {"hook_type": "bold_claim", "format": "short_vertical"},
        {"hook_type": "curiosity_gap", "format": "short_vertical"},
    ]
    result = engine.suggest_children(
        family_title="Ollama Memory Saturation",
        topic="Ollama VRAM Limits",
        originality_type="tool_test",
        what_are_we_adding="Stress-testing KV cache allocation limits.",
        recent_items=recent_items,
    )

    # Check that short_vertical proposal adapted its hook to avoid bold_claim collision
    shorts = [p for p in result.proposals if p.format == "short_vertical"]
    assert any(s.hook_type != "bold_claim" for s in shorts)


def test_validate_family():
    engine = ContentFamilyEngine()

    # Valid family
    valid = engine.validate_family(
        title="Valid Family Title",
        topic_id="opp-123",
        research_packet_id="packet-123",
        originality_plan_id="plan-123",
        claims_count=5,
    )
    assert valid.is_valid is True
    assert len(valid.errors) == 0

    # Invalid title
    invalid = engine.validate_family(
        title="Tiny",
        topic_id="opp-123",
        research_packet_id=None,
        originality_plan_id=None,
    )
    assert invalid.is_valid is False
    assert any("at least 5 characters" in err for err in invalid.errors)
    assert len(invalid.warnings) >= 2


def test_validate_child():
    engine = ContentFamilyEngine()

    # Valid child
    valid = engine.validate_child(
        child_format="short_vertical",
        platform_target="youtube",
        working_title="Fastest Model on Mac",
        angle="Detailed 45-second test spotlighting the single most impactful speed metric.",
        hook_type="bold_claim",
        original_value_connection="Visualizes the measured throughput from our local benchmark.",
        claims_count=2,
    )
    assert valid.is_valid is True
    assert len(valid.errors) == 0

    # Invalid: unsupported format
    invalid_fmt = engine.validate_child(
        child_format="hologram_stream",
        platform_target="youtube",
        working_title="Test Title",
        angle="Sufficient angle description that is long enough.",
        hook_type="bold_claim",
        original_value_connection="Original test",
    )
    assert invalid_fmt.is_valid is False
    assert any("not one of supported formats" in err for err in invalid_fmt.errors)

    # Invalid: angle too brief (generic recap protection)
    invalid_angle = engine.validate_child(
        child_format="social_post",
        platform_target="facebook",
        working_title="Test Post",
        angle="Too short",
        hook_type="surprising_stat",
        original_value_connection="Original test",
    )
    assert invalid_angle.is_valid is False
    assert any("must be at least" in err for err in invalid_angle.errors)


def test_calculate_economics():
    engine = ContentFamilyEngine()
    child_items = [
        {"incremental_cost": 0.50, "manual_time_minutes": 30, "local_compute_seconds": 120.0},
        {"incremental_cost": 0.25, "manual_time_minutes": 15, "local_compute_seconds": 60.0},
        {"incremental_cost": 0.00, "manual_time_minutes": 20, "local_compute_seconds": 0.0},
    ]
    econ = engine.calculate_economics(
        shared_cost=2.00,
        shared_time=60,
        shared_compute=300.0,
        child_items=child_items,
    )

    assert econ.shared_family_cost == 2.00
    assert econ.total_incremental_cost == 0.75
    assert econ.total_family_cost == 2.75
    assert econ.cost_per_child == round(2.75 / 3, 4)
    assert econ.total_time_minutes == 125
    assert econ.total_compute_seconds == 480.0


@pytest.mark.asyncio
async def test_engine_run_and_explain():
    engine = ContentFamilyEngine()
    context = EngineContext(
        run_id="cf-test-run-1",
        dry_run=True,
        trigger="manual",
        parameters={
            "action": "suggest_children",
            "family_title": "Benchmark Ollama vs vLLM",
            "topic": "Ollama vs vLLM",
            "originality_type": "benchmark",
            "what_are_we_adding": "Throughput and latency tests on 64GB Mac.",
        },
    )
    result = await engine.run(context)
    assert result.engine_id == "content_family"
    assert result.success is True
    assert result.output_count >= 4

    explanation = engine.explain("cf-test-run-1")
    assert "Content Family" in explanation.summary
    assert len(explanation.factors) >= 3
