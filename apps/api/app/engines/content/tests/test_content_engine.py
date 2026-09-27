import pytest
from app.engines.content.engine import ContentEngine
from app.engines.content.contracts import (
    GenerateScriptRequest,
    SectionRefineRequest,
    RefinementType,
)


@pytest.fixture
def content_engine():
    return ContentEngine()


@pytest.fixture
def sample_script_request():
    return GenerateScriptRequest(
        content_item_id="item-test-123",
        format="short_vertical",
        working_title="Local Qwen 2.5 vs Cloud Gemini Benchmark",
        angle="Local model wins on latency when prompts exceed 4K tokens",
        hook_type="bold_claim",
        platform_target="youtube",
        target_duration_sec=60,
        family_title="Gemini vs Qwen Benchmark",
        content_pillar="Hardware Benchmarks",
        original_value_type="benchmark",
        what_are_we_adding="Empirical token latency tests on RTX 4090",
        evidence_claims=[
            {
                "id": "claim-1",
                "text": "Local Qwen processed 4K context in 1.2s vs Cloud 2.9s",
                "is_verified": True,
            }
        ],
        brand_tone=["Direct", "Empirical", "Technical"],
        banned_cliches=["game-changer", "dive deep", "unleash"],
        niche_allowed_topics=["local AI", "hardware benchmarks", "quantization"],
        niche_blocked_topics=["crypto", "nft", "cloud SaaS resale"],
    )


def test_engine_health_and_config(content_engine):
    health = content_engine.health()
    assert health.status == "healthy"
    assert health.details["engine_id"] == "content"


def test_generate_script_short_vertical(content_engine, sample_script_request):
    draft = content_engine.generate_script(sample_script_request)
    assert draft.format == "short_vertical"
    assert len(draft.sections) == 5
    section_types = [s.section_type for s in draft.sections]
    assert section_types == ["hook", "problem_context", "evidence", "result", "cta"]
    assert draft.total_word_count > 0
    assert draft.estimated_duration_sec > 0

    # Evidence section links claim
    ev_sec = next(s for s in draft.sections if s.section_type == "evidence")
    assert "claim-1" in ev_sec.linked_claim_ids

    # Quality verdict is passing
    assert draft.quality_verdict is not None
    assert draft.quality_verdict.is_approvable is True
    assert len(draft.quality_verdict.blocking_reasons) == 0


def test_generate_script_youtube_long(content_engine, sample_script_request):
    req = sample_script_request.model_copy(update={"format": "youtube_long", "target_duration_sec": 600})
    draft = content_engine.generate_script(req)
    assert draft.format == "youtube_long"
    assert len(draft.sections) == 7
    section_types = [s.section_type for s in draft.sections]
    assert section_types == [
        "hook",
        "problem_context",
        "method_test",
        "evidence",
        "result",
        "interpretation",
        "cta",
    ]
    assert draft.total_word_count > 100


def test_generate_script_social_post(content_engine, sample_script_request):
    req = sample_script_request.model_copy(update={"format": "social_post"})
    draft = content_engine.generate_script(req)
    assert draft.format == "social_post"
    assert len(draft.sections) == 3
    section_types = [s.section_type for s in draft.sections]
    assert section_types == ["hook", "evidence", "cta"]


def test_section_refinements(content_engine):
    base_text = "We utilize local hardware benchmarks to evaluate whether local models outperform cloud alternatives under heavy loads."
    
    # 1. Shorten
    short_res = content_engine.refine_section(
        SectionRefineRequest(
            script_id="sc-1",
            section_id="sec-1",
            section_type="hook",
            current_narration=base_text,
            refinement_type=RefinementType.SHORTEN,
        )
    )
    assert short_res.word_count <= len(base_text.split())

    # 2. Expand
    expand_res = content_engine.refine_section(
        SectionRefineRequest(
            script_id="sc-1",
            section_id="sec-1",
            section_type="hook",
            current_narration=base_text,
            refinement_type=RefinementType.EXPAND,
        )
    )
    assert expand_res.word_count > len(base_text.split())

    # 3. Make clearer
    clear_res = content_engine.refine_section(
        SectionRefineRequest(
            script_id="sc-1",
            section_id="sec-1",
            section_type="hook",
            current_narration=base_text,
            refinement_type=RefinementType.MAKE_CLEARER,
        )
    )
    assert "utilize" not in clear_res.new_narration.lower()
    assert "use" in clear_res.new_narration.lower()

    # 4. More evidence
    ev_res = content_engine.refine_section(
        SectionRefineRequest(
            script_id="sc-1",
            section_id="sec-1",
            section_type="evidence",
            current_narration=base_text,
            refinement_type=RefinementType.MORE_EVIDENCE,
            linked_claims=[{"text": "latency decreased by 42% on batch size 16"}],
        )
    )
    assert "42%" in ev_res.new_narration


def test_quality_evaluation_blocks_banned_cliche(content_engine, sample_script_request):
    draft = content_engine.generate_script(sample_script_request)
    # Inject banned cliche into hook section
    draft.sections[0].narration = "This game-changer model will revolutionize your workflow."
    
    verdict = content_engine.evaluate_quality(draft.sections, sample_script_request)
    assert verdict.is_approvable is False
    assert "critical_brand_failure" in verdict.blocking_reasons
    assert verdict.dimension_scores["brand"].passed is False


def test_quality_evaluation_blocks_unsupported_claim(content_engine, sample_script_request):
    draft = content_engine.generate_script(sample_script_request)
    # Clear linked claims
    for s in draft.sections:
        s.linked_claim_ids = []
    
    verdict = content_engine.evaluate_quality(draft.sections, sample_script_request)
    assert verdict.is_approvable is False
    assert "unsupported_claim" in verdict.blocking_reasons


def test_quality_evaluation_blocks_off_niche(content_engine, sample_script_request):
    draft = content_engine.generate_script(sample_script_request)
    # Inject blocked topic
    draft.sections[1].narration += " Plus you can buy crypto tokens to fund the cluster."
    
    verdict = content_engine.evaluate_quality(draft.sections, sample_script_request)
    assert verdict.is_approvable is False
    assert "off_niche" in verdict.blocking_reasons
