import pytest
from app.engines.core.base import EngineContext
from app.engines.reference.engine import ReferenceEngine


@pytest.fixture
def engine():
    return ReferenceEngine()


def test_reference_engine_manifest_and_health(engine: ReferenceEngine):
    assert engine.id == "reference"
    assert engine.name == "Reference Benchmark Engine"
    assert engine.version == "1.0.0"

    health = engine.health()
    assert health.status == "healthy"
    assert "ReferenceEngine" in health.message


@pytest.mark.asyncio
async def test_reference_engine_run(engine: ReferenceEngine):
    context = EngineContext(run_id="test-run-1")
    result = await engine.run(context)

    assert result.success is True
    assert result.input_count == 2
    assert result.output_count == 1
    assert result.rejected_count == 1
    assert len(result.outputs) == 2


@pytest.mark.asyncio
async def test_reference_engine_dry_run(engine: ReferenceEngine):
    context = EngineContext(run_id="test-dry-run-1", dry_run=True)
    result = await engine.dry_run(context)

    assert result.success is True
    assert "[DRY RUN]" in result.summary


@pytest.mark.asyncio
async def test_reference_engine_explain(engine: ReferenceEngine):
    context = EngineContext(run_id="test-explain-1")
    result = await engine.run(context)

    first_output_id = result.outputs[0]["id"]
    explanation = engine.explain(first_output_id)

    assert explanation.result_id == first_output_id
    assert len(explanation.factors) > 0
