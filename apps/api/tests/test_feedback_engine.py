import pytest
from app.engines.core.base import EngineContext
from app.engines.feedback.engine import FeedbackEngine
from app.engines.feedback.synthesizer import FeedbackSynthesizer


def test_feedback_engine_metadata():
    engine = FeedbackEngine()
    assert engine.id == "feedback"
    assert engine.version == "1.0.0"
    assert "analytics" in engine.manifest.dependencies
    assert "brand" in engine.manifest.dependencies
    assert engine.rules.get("auto_apply") is False


def test_feedback_engine_health():
    engine = FeedbackEngine()
    health = engine.health()
    assert health.status == "healthy"
    assert health.details["auto_apply_disabled"] is True
    assert "hook_optimization" in health.details["allowed_lesson_types"]


def test_feedback_engine_invariant_auto_apply_forbidden():
    engine = FeedbackEngine()
    engine.rules["auto_apply"] = True
    with pytest.raises(ValueError, match="Invariant violation"):
        engine.validate_config()
    # Reset
    engine.rules["auto_apply"] = False


def test_feedback_synthesizer_hook_drop_cliche():
    synthesizer = FeedbackSynthesizer(rules={
        "hook_retention_critical_threshold_pct": 45.0,
        "hook_retention_viral_threshold_pct": 75.0,
        "engagement_rate_critical_threshold_pct": 2.0,
        "engagement_rate_strong_threshold_pct": 8.0,
    })

    snapshot = {
        "content_item_id": "item-101",
        "platform": "tiktok",
        "views": 500,
        "hook_retention_3s_pct": 28.5,
    }
    script_data = {
        "hook_text": "Hey guys welcome back today I'm going to talk about microservices",
    }
    content_item = {"working_title": "Microservices Intro"}

    lessons = synthesizer.evaluate_item_performance(snapshot, content_item, script_data)
    assert len(lessons) >= 1
    cliche_lesson = next((l for l in lessons if l["lesson_type"] == "banned_phrase_addition"), None)
    assert cliche_lesson is not None
    assert cliche_lesson["proposed_adjustment"]["target"] == "brand_profile"
    assert cliche_lesson["proposed_adjustment"]["field"] == "avoid_vocabulary"
    assert cliche_lesson["proposed_adjustment"]["value"] == "hey guys"


def test_feedback_synthesizer_viral_hook():
    synthesizer = FeedbackSynthesizer(rules={
        "hook_retention_critical_threshold_pct": 45.0,
        "hook_retention_viral_threshold_pct": 75.0,
        "engagement_rate_critical_threshold_pct": 2.0,
        "engagement_rate_strong_threshold_pct": 8.0,
    })

    snapshot = {
        "content_item_id": "item-202",
        "platform": "youtube",
        "views": 1500,
        "hook_retention_3s_pct": 82.0,
    }
    script_data = {
        "hook_text": "Here is why 90% of developers fail with asyncio.",
    }
    content_item = {"working_title": "Asyncio Failures"}

    lessons = synthesizer.evaluate_item_performance(snapshot, content_item, script_data)
    viral_lesson = next((l for l in lessons if l["proposed_adjustment"]["target"] == "brand_exemplar"), None)
    assert viral_lesson is not None
    assert viral_lesson["proposed_adjustment"]["field"] == "approved_hook"
    assert viral_lesson["impact_level"] == "MEDIUM"


def test_feedback_synthesizer_engagement_lessons():
    synthesizer = FeedbackSynthesizer(rules={
        "hook_retention_critical_threshold_pct": 45.0,
        "hook_retention_viral_threshold_pct": 75.0,
        "engagement_rate_critical_threshold_pct": 2.0,
        "engagement_rate_strong_threshold_pct": 8.0,
    })

    # High engagement
    snap_high = {
        "content_item_id": "item-303",
        "platform": "youtube",
        "views": 1000,
        "likes": 90,
        "comments": 20,
        "shares": 10,
        "saves": 5,
    }
    content_item = {"working_title": "Deep Dive on SQLite"}
    lessons_high = synthesizer.evaluate_item_performance(snap_high, content_item)
    topic_lesson = next((l for l in lessons_high if l["lesson_type"] == "topic_reinforcement"), None)
    assert topic_lesson is not None
    assert topic_lesson["proposed_adjustment"]["target"] == "brand_memory"


@pytest.mark.asyncio
async def test_feedback_engine_run_and_dry_run():
    engine = FeedbackEngine()
    context = EngineContext(
        run_id="test-run-123",
        parameters={
            "snapshots": [
                {
                    "content_item_id": "item-404",
                    "platform": "instagram",
                    "views": 200,
                    "likes": 1,
                    "comments": 0,
                    "shares": 0,
                    "saves": 0,
                    "hook_retention_3s_pct": 20.0,
                }
            ],
            "content_items_map": {"item-404": {"working_title": "Short Tech News"}},
            "scripts_map": {"item-404": {"hook_text": "In this video we review updates"}},
        },
    )

    result = await engine.run(context)
    assert result.engine_id == "feedback"
    assert len(result.outputs) >= 1
    assert result.output_count >= 1

    dry_result = await engine.dry_run(context)
    assert "[Dry-Run]" in dry_result.summary


def test_feedback_engine_explain():
    engine = FeedbackEngine()
    explanation = engine.explain("lesson-test-123")
    assert explanation.result_id == "lesson-test-123"
    assert "Closed Loop Learning" in explanation.summary
    assert len(explanation.factors) >= 3
