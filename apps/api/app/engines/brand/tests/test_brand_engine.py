import pytest
from app.engines.brand.contracts import BrandQAInput
from app.engines.brand.engine import BrandEngine
from app.engines.core.base import EngineContext


@pytest.fixture
def engine():
    return BrandEngine()


@pytest.fixture
def sample_brand():
    return {
        "brand_name": "Practical AI Studio",
        "brand_promise": "Tested AI tools, automated workflows, and honest benchmarks without hype.",
        "audience": "Engineers, builders, and technical knowledge workers.",
        "tone": ["evidence-driven", "concise", "practical", "calm", "transparent"],
        "voice_rules": [
            "Show the terminal or interface; do not merely talk about it.",
            "State costs, latency, and failure rates explicitly.",
            "Never declare a tool 'game-changing' or 'revolutionary'.",
        ],
        "preferred_vocabulary": ["workflow", "benchmark", "latency", "trade-off", "failure rate", "reproducible"],
        "avoid_vocabulary": ["game-changer", "insane", "mind-blowing", "unbelievable", "passive income"],
        "banned_cliches": [
            "in today's fast-paced world",
            "without further ado",
            "let's dive right in",
            "dive right into",
        ],
        "claim_rules": [
            "Every speed or accuracy claim must cite a benchmark run or primary source.",
        ],
        "cta_style": "Direct, educational, and low-friction.",
    }


def test_brand_engine_manifest_and_health(engine: BrandEngine):
    assert engine.id == "brand"
    assert engine.name == "Brand Engine"
    assert engine.version == "1.0.0"

    health = engine.health()
    assert health.status == "healthy"
    assert "operational" in health.message


def test_on_brand_content_passes(engine: BrandEngine, sample_brand):
    item = BrandQAInput(
        id="draft-01",
        title="Local Coding Assistant Benchmark: Latency and Token Costs",
        body="We measured the latency and failure rate of local models. The trade-off is clear when comparing reproducible benchmarks against API costs.",
        hook="Here is our empirical benchmark testing local coding assistants.",
        cta="Inspect the benchmark repository linked in the description.",
    )
    verdict = engine.evaluate_item(item, sample_brand, exemplars=[])

    assert verdict.on_brand is True
    assert verdict.overall_score >= 70.0
    assert len(verdict.matched_preferred_words) >= 3
    assert len(verdict.matched_avoid_words) == 0
    assert len(verdict.matched_cliches) == 0
    critical_violations = [v for v in verdict.violations if v.severity == "critical"]
    assert len(critical_violations) == 0


def test_banned_cliche_causes_rejection(engine: BrandEngine, sample_brand):
    item = BrandQAInput(
        id="draft-cliche",
        title="AI Tools You Must Know",
        body="In today's fast-paced world, software moves fast. Without further ado, let's dive right in and look at the benchmark.",
        hook="Without further ado, let's dive right in!",
    )
    verdict = engine.evaluate_item(item, sample_brand, exemplars=[])

    assert verdict.on_brand is False
    assert len(verdict.matched_cliches) >= 2
    assert any(v.rule_type == "banned_cliche" for v in verdict.violations)
    assert len(verdict.suggested_fixes) > 0


def test_avoid_vocabulary_causes_rejection(engine: BrandEngine, sample_brand):
    item = BrandQAInput(
        id="draft-hype",
        title="This Insane New Tool Will Blow Your Mind",
        body="This is a total game-changer. The results are unbelievable and insane for generating passive income.",
    )
    verdict = engine.evaluate_item(item, sample_brand, exemplars=[])

    assert verdict.on_brand is False
    assert len(verdict.matched_avoid_words) >= 3
    assert any(v.rule_type == "avoid_vocabulary" for v in verdict.violations)


def test_excessive_hype_triggers_warning(engine: BrandEngine, sample_brand):
    item = BrandQAInput(
        id="draft-exclamation",
        title="Awesome benchmark test",
        body="We tested the workflow! It was super fast! Look at this latency! WOW! AMAZING!",
    )
    verdict = engine.evaluate_item(item, sample_brand, exemplars=[])

    assert verdict.tone_score < 100.0
    assert any(v.rule_type in ("excessive_hype", "tone_mismatch") for v in verdict.violations)


@pytest.mark.asyncio
async def test_brand_engine_run_and_explain(engine: BrandEngine, sample_brand):
    context = EngineContext(
        run_id="run-brand-01",
        parameters={
            "brand_profile": sample_brand,
            "drafts": [
                {
                    "id": "d1",
                    "title": "Local LLM Benchmark",
                    "body": "In this benchmark, we measured latency and failure rate across local workflows.",
                },
                {
                    "id": "d2",
                    "title": "Hype script",
                    "body": "Let's dive right in to this insane game-changer!",
                },
            ],
        },
    )

    result = await engine.run(context)
    assert result.success is True
    assert result.input_count == 2
    assert result.output_count == 1
    assert result.rejected_count == 1

    first_verdict_id = result.outputs[0]["id"]
    explanation = engine.explain(first_verdict_id)
    assert explanation.result_id == first_verdict_id
    assert "ON-BRAND" in explanation.summary


@pytest.mark.asyncio
async def test_brand_engine_dry_run(engine: BrandEngine, sample_brand):
    context = EngineContext(
        run_id="dry-brand-01",
        dry_run=True,
        parameters={"brand_profile": sample_brand},
    )
    result = await engine.dry_run(context)
    assert result.success is True
    assert "[DRY RUN]" in result.summary


def test_brand_engine_six_dimensions(engine: BrandEngine, sample_brand):
    item = BrandQAInput(
        id="draft-dims",
        title="Local Model Benchmarks",
        body="We benchmarked reproducible latency across developer workflows.",
        hook="Here is our local model benchmark.",
        cta="Check out the reproduction repository.",
        platform="youtube_shorts",
    )
    verdict = engine.evaluate_item(item, sample_brand, exemplars=[])

    # Check 6 formal QA dimensions
    assert "Tone" in verdict.dimensions
    assert "Vocabulary" in verdict.dimensions
    assert "Repetition" in verdict.dimensions
    assert "Audience Fit" in verdict.dimensions
    assert "CTA Fit" in verdict.dimensions
    assert "Platform Fit" in verdict.dimensions

    for dim_name, score in verdict.dimensions.items():
        assert 0.0 <= score <= 100.0


def test_brand_memory_repetition_detection(engine: BrandEngine, sample_brand):
    memory = [
        {
            "id": "mem-1",
            "memory_type": "hook",
            "content": "Stop paying OpenAI for batch summarization when Ollama is faster.",
            "usage_count": 3,
        },
        {
            "id": "mem-2",
            "memory_type": "topic",
            "content": "ollama benchmarks",
            "usage_count": 4,
        },
    ]

    item = BrandQAInput(
        id="draft-rep",
        title="Ollama Benchmarks",
        body="We measured the latency and reproducible token throughput of ollama benchmarks.",
        hook="Stop paying OpenAI for batch summarization when Ollama is faster.",
        cta="Inspect the benchmark repository.",
    )

    verdict = engine.evaluate_item(item, sample_brand, exemplars=[], memory=memory)

    assert len(verdict.repetition_warnings) >= 1
    assert any("Stop paying OpenAI" in w for w in verdict.repetition_warnings)
    assert verdict.repetition_score < 100.0
    assert any(v.rule_type == "hook_repetition" for v in verdict.violations)


def test_brand_tone_drift_detection(engine: BrandEngine, sample_brand):
    item = BrandQAInput(
        id="draft-drift",
        title="This tool will destroy everything",
        body="This miracle setup will crazy destroy your previous benchmarks with insane speed.",
    )

    verdict = engine.evaluate_item(item, sample_brand, exemplars=[])

    assert verdict.tone_score < 100.0
    assert any(v.rule_type == "tone_drift" for v in verdict.violations)
