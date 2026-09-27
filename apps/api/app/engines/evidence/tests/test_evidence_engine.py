import pytest
from app.engines.core.base import EngineContext
from app.engines.evidence.engine import EvidenceEngine


@pytest.fixture
def evidence_engine():
    return EvidenceEngine()


def test_evidence_engine_manifest_and_health(evidence_engine):
    assert evidence_engine.id == "evidence"
    assert evidence_engine.version == "1.0.0"
    assert evidence_engine.rules_version == "1.0.0"
    assert "research" in evidence_engine.manifest.dependencies

    health = evidence_engine.health()
    assert health.status == "healthy"
    assert "operational" in health.message

def test_evidence_engine_explain(evidence_engine):
    expl = evidence_engine.explain("claim-123")
    assert expl.result_id == "claim-123"
    assert len(expl.factors) >= 1
    assert "Evidence Engine enforces" in expl.summary


@pytest.mark.asyncio
async def test_evidence_engine_coverage_evaluation(evidence_engine):
    # Test with custom claims list
    custom_claims = [
        {"claim_type": "external_fact", "source_type": "primary", "is_overridden": False},
        {"claim_type": "external_fact", "source_type": "supporting", "is_overridden": False},
        {"claim_type": "original_measurement", "source_type": None, "is_overridden": False},
        {"claim_type": "opinion", "source_type": None, "is_overridden": False},
        {"claim_type": "external_fact", "source_type": None, "is_overridden": False},  # unsupported
    ]

    context = EngineContext(
        run_id="test-run-1",
        dry_run=False,
        parameters={"custom_claims": custom_claims},
    )

    result = await evidence_engine.run(context)
    assert result.success is True
    report = result.outputs[0]["coverage_report"]
    assert report["total_claims"] == 5
    assert report["factual_claims"] == 4
    assert report["opinions_labeled"] == 1
    assert report["primary_source_backed"] == 1
    assert report["supporting_source_backed"] == 1
    assert report["original_test_backed"] == 1
    assert report["unsupported"] == 1
    assert report["coverage_percent"] == 75.0
    assert report["gate_passed"] is False
    assert "Gate status: BLOCKED" in result.summary


@pytest.mark.asyncio
async def test_evidence_engine_gate_passed_when_overridden_or_fully_backed(evidence_engine):
    custom_claims = [
        {"claim_type": "external_fact", "source_type": "primary", "is_overridden": False},
        {"claim_type": "external_fact", "source_type": "supporting", "is_overridden": False},
        {"claim_type": "original_measurement", "source_type": None, "is_overridden": False},
        {"claim_type": "external_fact", "source_type": None, "is_overridden": True},  # creator override
    ]

    context = EngineContext(
        run_id="test-run-2",
        dry_run=False,
        parameters={"custom_claims": custom_claims},
    )

    result = await evidence_engine.run(context)
    report = result.outputs[0]["coverage_report"]
    assert report["unsupported"] == 0
    assert report["overridden_count"] == 1
    assert report["coverage_percent"] == 100.0
    assert report["gate_passed"] is True
    assert "Gate status: PASS" in result.summary
