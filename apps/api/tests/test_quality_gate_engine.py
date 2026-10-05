from types import SimpleNamespace
import pytest

from app.engines.core.base import EngineContext
from app.engines.quality_gate.contracts import DimensionStatus
from app.engines.quality_gate.engine import QualityGateEngine
from app.engines.quality_gate.evaluator import QualityGateEvaluator


def test_quality_gate_engine_manifest_and_health():
    engine = QualityGateEngine()
    engine.validate_config()
    health = engine.health()

    assert health.status in ("healthy", "degraded")
    assert health.details["has_rules"] is True
    assert health.details["dimensions_count"] == 9
    assert engine.id == "quality_gate"


def test_quality_gate_evaluator_all_nine_dimensions():
    evaluator = QualityGateEvaluator()

    item = SimpleNamespace(
        id="item-test-1",
        working_title="High-Performance Async Workflows",
        format="short_vertical",
        platform_target="youtube",
        hook_type="bold_claim",
        original_value_connection="Local Python benchmark scripts.",
        incremental_cost=0.005,
        manual_time_minutes=15,
    )
    section1 = SimpleNamespace(narration="Here is an empirical test of local database pipelines.")
    script = SimpleNamespace(
        id="script-test-1",
        total_word_count=120,
        sections=[section1],
    )
    family = SimpleNamespace(
        id="fam-test-1",
        original_value_type="benchmark",
        ai_cost=0.02,
        research_cost=0.0,
        manual_time_minutes=10,
    )
    packet = SimpleNamespace(
        id="packet-test-1",
        sources=[SimpleNamespace(id="s1"), SimpleNamespace(id="s2")],
        claims=[SimpleNamespace(id="c1")],
    )
    brand = SimpleNamespace(
        banned_cliches=["game-changer", "revolutionary", "dive into"],
    )
    niche = SimpleNamespace(
        name="Developer Productivity",
    )
    scene = SimpleNamespace(
        id="sc1",
        rights_status="CLEARED",
    )
    media_pkg = SimpleNamespace(
        status="READY",
        subtitle_path="/tmp/sub.srt",
        video_path="/tmp/video.mp4",
    )

    result = evaluator.evaluate_all(
        item=item,
        script=script,
        family=family,
        packet=packet,
        originality_plan=None,
        brand=brand,
        niche=niche,
        scenes=[scene],
        media_package=media_pkg,
    )

    assert result["overall_score"] >= 70.0
    assert result["status"] == "PASSED"
    assert len(result["dimensions"]) == 9

    dim_ids = [d.id for d in result["dimensions"]]
    assert "evidence_quality" in dim_ids
    assert "brand_fit" in dim_ids
    assert "originality" in dim_ids
    assert "viewer_value" in dim_ids
    assert "niche_fit" in dim_ids
    assert "repetition_intelligence" in dim_ids
    assert "asset_rights" in dim_ids
    assert "media_qc" in dim_ids
    assert "estimated_cost" in dim_ids


def test_quality_gate_evaluator_blocks_on_banned_cliches():
    evaluator = QualityGateEvaluator()

    item = SimpleNamespace(id="item-test-2", original_value_connection="Test", hook_type="curiosity_gap", incremental_cost=0.0, manual_time_minutes=0)
    section = SimpleNamespace(narration="This is a revolutionary game-changer for content creators.")
    script = SimpleNamespace(id="script-test-2", total_word_count=50, sections=[section])
    brand = SimpleNamespace(banned_cliches=["game-changer", "revolutionary"])

    result = evaluator.evaluate_all(
        item=item,
        script=script,
        family=None,
        packet=None,
        originality_plan=None,
        brand=brand,
        niche=None,
        scenes=[],
        media_package=None,
    )

    assert result["status"] == "BLOCKED"
    brand_dim = next(d for d in result["dimensions"] if d.id == "brand_fit")
    assert brand_dim.status == DimensionStatus.BLOCKED
    assert any(r.action_type == "return_to_script" for r in result["recommendations"])


def test_quality_gate_evaluator_blocks_on_restricted_rights():
    evaluator = QualityGateEvaluator()

    item = SimpleNamespace(id="item-test-3", original_value_connection="Test", hook_type="curiosity_gap", incremental_cost=0.0, manual_time_minutes=0)
    script = SimpleNamespace(id="script-test-3", total_word_count=50, sections=[SimpleNamespace(narration="Clean audio.")])
    scenes = [SimpleNamespace(id="sc-blocked", rights_status="BLOCKED")]

    result = evaluator.evaluate_all(
        item=item,
        script=script,
        family=None,
        packet=None,
        originality_plan=None,
        brand=SimpleNamespace(banned_cliches=[]),
        niche=None,
        scenes=scenes,
        media_package=None,
    )

    assert result["status"] == "BLOCKED"
    rights_dim = next(d for d in result["dimensions"] if d.id == "asset_rights")
    assert rights_dim.status == DimensionStatus.BLOCKED
    assert any(r.action_type == "replace_asset" for r in result["recommendations"])


@pytest.mark.asyncio
async def test_quality_gate_engine_run_and_explain():
    engine = QualityGateEngine()
    ctx = EngineContext(
        run_id="run-qg-1",
        parameters={
            "content_item_id": "item-e2e-1",
            "evaluation_data": {
                "overall_score": 88.0,
                "status": "PASSED",
                "dimensions": [],
            },
        },
    )

    res = await engine.run(ctx)
    assert res.success is True
    assert len(res.outputs) == 1
    assert res.outputs[0]["status"] == "PASSED"

    dry_res = await engine.dry_run(ctx)
    assert dry_res.success is True

    explanation = engine.explain("audit-123")
    assert explanation.result_id == "audit-123"
    assert len(explanation.factors) >= 5
