import pytest
from app.engines.core.base import EngineContext
from app.engines.scene_studio.adapters import LocalDeterministicVisualAdapter
from app.engines.scene_studio.contracts import (
    DecompositionRequest,
    SectionInput,
)
from app.engines.scene_studio.engine import SceneStudioEngine
from app.models.scene import VisualPriority


def test_scene_studio_engine_initialization_and_health():
    engine = SceneStudioEngine()
    assert engine.id == "scene_studio"
    assert engine.name == "Scene Studio Engine"
    health = engine.health()
    assert health.status == "healthy"
    assert health.details["visual_hierarchy_levels"] == 7
    assert health.details["words_per_second"] == 2.4


def test_scene_decomposition_visual_hierarchy():
    engine = SceneStudioEngine()

    sections = [
        SectionInput(
            id="sec-hook",
            section_type="hook",
            heading="Opening Demo",
            narration="Watch this local coding assistant run completely offline in our developer terminal.",
        ),
        SectionInput(
            id="sec-benchmark",
            section_type="evidence",
            heading="Empirical Latency Test",
            narration="We measured 142 tokens/s on RTX 4090 with 45ms time to first token.",
            linked_claim_ids=["claim-benchmark-4090"],
        ),
        SectionInput(
            id="sec-code",
            section_type="method_test",
            heading="Terminal Execution",
            narration="Run the bash script with git clone to reproduce the local setup.",
        ),
        SectionInput(
            id="sec-diagram",
            section_type="problem_context",
            heading="Pipeline Architecture",
            narration="Here is how the pipeline workflow connects the SQLite database to the local worker.",
        ),
        SectionInput(
            id="sec-cta",
            section_type="cta",
            heading="Closing Invitation",
            narration="Inspect the reproduction repository linked below and subscribe for tested benchmarks.",
        ),
    ]

    req = DecompositionRequest(
        script_id="script-test-1",
        format="short_vertical",
        title="Local AI Coding Benchmark",
        sections=sections,
    )

    scenes = engine.decompose_script(req)
    assert len(scenes) >= 5

    # Check Visual Priority Hierarchy mapping
    visual_types = [s.visual_type for s in scenes]
    assert VisualPriority.REAL_SCREEN_RECORDING in visual_types
    assert VisualPriority.BENCHMARK_CHART in visual_types
    assert VisualPriority.CODE_TERMINAL in visual_types
    assert VisualPriority.WORKFLOW_DIAGRAM in visual_types

    # Check evidence reference on benchmark scene
    benchmark_scene = next(s for s in scenes if s.visual_type == VisualPriority.BENCHMARK_CHART)
    assert benchmark_scene.evidence_reference == "claim-benchmark-4090"

    # Check timing estimates
    for s in scenes:
        assert s.timing_estimate >= 1.5
        assert s.on_screen_text is not None


def test_storyboard_validation():
    engine = SceneStudioEngine()

    # Case 1: Valid high-empirical storyboard
    valid_scenes = [
        {"scene_order": 1, "visual_type": "real_screen_recording", "visual_source": "data/assets/screen.mp4", "timing_estimate": 10.0, "narration": "Watch the test."},
        {"scene_order": 2, "visual_type": "benchmark_chart", "visual_source": "data/assets/chart.png", "timing_estimate": 15.0, "narration": "Benchmark ran 2x faster.", "evidence_reference": "c1"},
        {"scene_order": 3, "visual_type": "code_terminal", "visual_source": "data/assets/terminal.mp4", "timing_estimate": 15.0, "narration": "Code executes in 100ms."},
        {"scene_order": 4, "visual_type": "workflow_diagram", "visual_source": "data/assets/diagram.png", "timing_estimate": 12.0, "narration": "Architecture overview."},
    ]
    val_result = engine.validate_storyboard(valid_scenes, target_duration=60.0)
    assert val_result.total_scenes == 4
    assert val_result.total_duration_sec == 52.0
    assert val_result.is_timing_valid is True
    assert val_result.empirical_visual_ratio >= 50.0
    assert val_result.blocked_rights_count == 0
    assert val_result.all_valid is True

    # Case 2: Over-duration storyboard (>60s)
    long_scenes = [
        {"scene_order": 1, "visual_type": "real_screen_recording", "timing_estimate": 35.0, "narration": "Long intro part 1."},
        {"scene_order": 2, "visual_type": "benchmark_chart", "timing_estimate": 35.0, "narration": "Long benchmark part 2."},
    ]
    val_long = engine.validate_storyboard(long_scenes, target_duration=60.0)
    assert val_long.total_duration_sec == 70.0
    assert val_long.is_timing_valid is False
    assert any("exceeds the strict 60.0s" in w for w in val_long.warnings)

    # Case 3: Blocked rights
    blocked_scenes = [
        {"scene_order": 1, "visual_type": "real_screen_recording", "timing_estimate": 10.0, "rights_status": "DO_NOT_USE", "narration": "Scene with pirate media."},
    ]
    val_blocked = engine.validate_storyboard(blocked_scenes, target_duration=60.0)
    assert val_blocked.blocked_rights_count == 1
    assert val_blocked.all_valid is False


def test_local_deterministic_visual_adapter():
    adapter = LocalDeterministicVisualAdapter()
    result = adapter.generate_visual(
        prompt="RTX 4090 vs Apple M4 Max Benchmark Latency",
        visual_type="benchmark_chart",
        title="Empirical Comparison",
    )
    assert result["is_local_mock"] is True
    assert result["file_path"].endswith(".svg")
    assert result["width"] == 1080
    assert result["height"] == 1920

    # Ensure file exists and contains SVG elements
    with open(result["file_path"], "r", encoding="utf-8") as f:
        content = f.read()
        assert "<svg" in content
        assert "EVIDENCE 1st" in content


@pytest.mark.asyncio
async def test_scene_studio_engine_run_and_explain():
    engine = SceneStudioEngine()
    context = EngineContext(
        run_id="run-scene-1",
        parameters={
            "scenes": [
                {"scene_order": 1, "visual_type": "real_screen_recording", "timing_estimate": 12.0, "narration": "Watch the demo."},
                {"scene_order": 2, "visual_type": "benchmark_chart", "timing_estimate": 18.0, "narration": "Benchmark chart result."},
            ],
            "target_duration": 60.0,
        },
    )
    res = await engine.run(context)
    assert res.engine_id == "scene_studio"
    assert res.input_count == 2
    assert res.success is True

    explanation = engine.explain("run-scene-1")
    assert explanation.result_id == "run-scene-1"
    assert "visual_priority_hierarchy" in str(explanation.factors)
