import pytest
from app.engines.core.base import EngineContext
from app.engines.originality.engine import OriginalityEngine


@pytest.mark.asyncio
async def test_originality_manifest_and_rules():
    engine = OriginalityEngine()
    assert engine.id == "originality"
    assert engine.manifest.name == "Originality Engine"
    assert "OpportunityScore" in engine.manifest.inputs
    assert "OriginalityPlan" in engine.manifest.outputs
    assert engine.rules.get("block_generic_summary") is True
    assert len(engine.rules.get("supported_originality_types", [])) == 12


@pytest.mark.asyncio
async def test_evaluate_originality_valid():
    engine = OriginalityEngine()
    res = engine.evaluate_originality(
        topic="Apple M4 Max Unified Memory Scaling",
        originality_type="benchmark",
        what_are_we_adding="Side-by-side token generation throughput and unified memory bandwidth saturation benchmark.",
    )
    assert res.is_ready is True
    assert res.is_generic_summary is False
    assert res.status == "needs_review"
    assert res.confidence_score >= 80.0


@pytest.mark.asyncio
async def test_generic_summary_quarantine():
    engine = OriginalityEngine()

    # Rule: Generic summary defaults to NOT READY
    res = engine.evaluate_originality(
        topic="New AI Model Released Today",
        originality_type="benchmark",
        what_are_we_adding="Just a generic summary of the article and recap of news.",
    )
    assert res.is_ready is False
    assert res.is_generic_summary is True
    assert res.status == "not_ready"
    assert "Generic summary detected" in (res.rejection_reason or "")


@pytest.mark.asyncio
async def test_too_brief_contribution():
    engine = OriginalityEngine()
    res = engine.evaluate_originality(
        topic="DeepSeek R1",
        originality_type="tool_test",
        what_are_we_adding="testing it",
    )
    assert res.is_ready is False
    assert res.is_generic_summary is True
    assert res.status == "not_ready"
    assert "too brief" in (res.rejection_reason or "")


@pytest.mark.asyncio
async def test_unsupported_type():
    engine = OriginalityEngine()
    res = engine.evaluate_originality(
        topic="DeepSeek R1",
        originality_type="unsupported_vague_reaction",
        what_are_we_adding="Our reaction and reading the spec sheet on camera.",
    )
    assert res.is_ready is False
    assert res.is_generic_summary is True
    assert res.status == "not_ready"
    assert "Unsupported originality type" in (res.rejection_reason or "")


@pytest.mark.asyncio
async def test_propose_original_angles():
    engine = OriginalityEngine()
    angles = engine.propose_original_angles("Local Whisper Transcription on RTX 4090")
    assert len(angles) == 3
    types = [a["originality_type"] for a in angles]
    assert "benchmark" in types
    assert "failure_analysis" in types
    assert "practical_tutorial" in types
    for a in angles:
        assert len(a["what_are_we_adding"]) > 20
        assert len(a["suggested_experiments"]) >= 1


@pytest.mark.asyncio
async def test_originality_engine_run_and_explain():
    engine = OriginalityEngine()
    context = EngineContext(
        run_id="test-orig-run-1",
        dry_run=True,
        trigger="manual",
        parameters={
            "topic": "Benchmarking Ollama vs vLLM on Linux",
            "originality_type": "benchmark",
            "what_are_we_adding": "Measured tokens/sec across 10 concurrent requests.",
        },
    )
    result = await engine.run(context)
    assert result.engine_id == "originality"
    assert result.success is True
    assert result.output_count == 3

    health = engine.health()
    assert health.status == "healthy"

    explanation = engine.explain("test-orig-run-1")
    assert "What are WE adding?" in explanation.summary
    assert len(explanation.factors) >= 4
