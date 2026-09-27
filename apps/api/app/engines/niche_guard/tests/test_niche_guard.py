import pytest
from app.engines.core.base import EngineContext
from app.engines.niche_guard.contracts import NicheGuardInput
from app.engines.niche_guard.engine import NicheGuardEngine


@pytest.fixture
def engine():
    return NicheGuardEngine()


@pytest.fixture
def sample_niche():
    return {
        "name": "AI Engineering & Coding Automation",
        "allowed_topics": [
            "coding agents", "local LLMs", "developer tools",
            "AI engineering", "IDE integrations", "evals and benchmarks", "workflow automation"
        ],
        "adjacent_topics": ["software architecture", "DevOps", "vector databases", "open source models"],
        "blocked_topics": [
            "crypto/web3 trading", "general consumer gadgets",
            "passive income schemes", "clickbait AI news without code/tests"
        ],
        "must_have_signals": ["code repository", "reproducible benchmark", "documentation or paper", "practical tool release"],
        "negative_keywords": ["get rich quick", "secret trick", "replaced all coders", "100x money"],
        "content_pillars": [
            {"name": "Coding Agent Stress Tests", "keywords": ["agent", "benchmark", "coding"]},
            {"name": "Local Models & Tooling", "keywords": ["ollama", "vllm", "local", "deepseek"]},
            {"name": "Production Automation Recipes", "keywords": ["automation", "recipe", "workflow"]},
        ],
        "primary_problems": ["API costs", "benchmark claims", "local LLM integration"],
    }


def test_niche_guard_manifest_and_health(engine: NicheGuardEngine):
    assert engine.id == "niche_guard"
    assert engine.name == "Niche Guard Engine"
    assert engine.version == "1.0.0"

    health = engine.health()
    assert health.status == "healthy"
    assert "operational" in health.message


def test_in_niche_candidate_passes(engine: NicheGuardEngine, sample_niche):
    item = NicheGuardInput(
        id="cand-01",
        title="Benchmarking Coding Agents in VS Code with Local LLMs",
        text="Empirical benchmark measuring latency and code repository generation using Ollama and vLLM.",
        tags=["coding agents", "local LLMs", "evals and benchmarks"],
    )
    verdict = engine.evaluate_item(item, sample_niche)

    assert verdict.passed is True
    assert verdict.score >= 55.0
    assert len(verdict.pillar_matches) > 0
    assert len(verdict.matched_allowed_topics) > 0
    assert len(verdict.blocked_topics_detected) == 0
    assert "Approved" in verdict.reason


def test_blocked_topic_instant_rejection(engine: NicheGuardEngine, sample_niche):
    item = NicheGuardInput(
        id="cand-blocked",
        title="Top 5 Passive Income Schemes Using Automated Trading Bots",
        text="Make money fast with crypto/web3 trading algorithms and passive income schemes.",
        tags=["passive income schemes", "crypto"],
    )
    verdict = engine.evaluate_item(item, sample_niche)

    assert verdict.passed is False
    assert verdict.score == 0.0
    assert len(verdict.blocked_topics_detected) > 0
    assert "Rejected" in verdict.reason
    assert "blocked topic detected" in verdict.reason


def test_off_niche_content_rejected(engine: NicheGuardEngine, sample_niche):
    item = NicheGuardInput(
        id="cand-off",
        title="Best Sourdough Bread Recipe for Home Bakers",
        text="Learn how to ferment sourdough starter and bake artisanal loaves with crispy crust.",
        tags=["baking", "cooking", "recipes"],
    )
    verdict = engine.evaluate_item(item, sample_niche)

    assert verdict.passed is False
    assert verdict.score < 55.0
    assert "Rejected" in verdict.reason


def test_negative_keywords_heavily_penalized(engine: NicheGuardEngine, sample_niche):
    item = NicheGuardInput(
        id="cand-spam",
        title="Coding agents get rich quick and secret trick that replaced all coders",
        text="Use this secret trick to make 100x money with coding agents today.",
        tags=["coding agents"],
    )
    verdict = engine.evaluate_item(item, sample_niche)

    assert len(verdict.matched_negative_keywords) >= 2
    assert verdict.passed is False


@pytest.mark.asyncio
async def test_niche_guard_run_and_explain(engine: NicheGuardEngine, sample_niche):
    context = EngineContext(
        run_id="run-ng-01",
        parameters={
            "niche_profile": sample_niche,
            "items": [
                {
                    "id": "c1",
                    "title": "Local LLMs and Coding Agents Stress Test",
                    "text": "Tested code repository generation against local models.",
                    "tags": ["local LLMs", "coding agents"],
                },
                {
                    "id": "c2",
                    "title": "Crypto/web3 trading passive income schemes",
                    "text": "Trading crypto.",
                    "tags": [],
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
    assert len(explanation.factors) > 0


@pytest.mark.asyncio
async def test_niche_guard_dry_run(engine: NicheGuardEngine, sample_niche):
    context = EngineContext(
        run_id="dry-ng-01",
        dry_run=True,
        parameters={"niche_profile": sample_niche},
    )
    result = await engine.dry_run(context)
    assert result.success is True
    assert "[DRY RUN]" in result.summary
