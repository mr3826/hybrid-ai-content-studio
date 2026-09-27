import hashlib
import json
import pytest
from pathlib import Path

from app.engines.core import EngineContext
from app.engines.export.contracts import ExportEngineInput
from app.engines.export.engine import ExportEngine


def test_export_engine_health_and_config():
    engine = ExportEngine()
    engine.validate_config()
    health = engine.health()
    assert health.status == "healthy"
    assert "youtube" in health.details["supported_platforms"]
    assert "manifest.json" in health.details["required_files"]


def test_export_engine_dry_run():
    engine = ExportEngine()
    payload = ExportEngineInput(
        content_item_id="item-test-123",
        working_title="Gemini 2.0 vs Qwen 2.5 Coding Benchmark",
        slug="gemini-2-vs-qwen-2-5-benchmark",
        format="short_vertical",
        platform_target="youtube",
        script_title="Gemini 2.0 vs Qwen 2.5 Coding Benchmark",
        sections=[
            {
                "section_type": "hook",
                "heading": "The Hook",
                "narration": "Can an open-weights model beat Gemini 2.0 in Python refactoring?",
                "visual_cue": "Side by side split screen benchmark terminal",
                "estimated_seconds": 8,
                "word_count": 14,
                "linked_claim_ids": ["c1"],
            },
            {
                "section_type": "evidence",
                "heading": "Empirical Test",
                "narration": "We tested 100 complex AST refactorings on identical hardware.",
                "visual_cue": "Benchmark bar chart showing execution latency",
                "estimated_seconds": 20,
                "word_count": 35,
                "linked_claim_ids": ["c2"],
            },
            {
                "section_type": "cta",
                "heading": "Call to Action",
                "narration": "Check the code in the description and tell us what you think.",
                "visual_cue": "Channel logo and repository link overlay",
                "estimated_seconds": 7,
                "word_count": 12,
                "linked_claim_ids": [],
            },
        ],
        sources=[
            {
                "title": "SWE-bench Official Results",
                "url": "https://swebench.com/results",
                "source_type": "benchmark_data",
                "author_or_org": "SWE-bench Team",
                "excerpt": "Qwen 2.5 achieved 46.2% on SWE-bench Verified.",
            }
        ],
        claims=[
            {
                "claim_text": "Qwen 2.5 achieved 46.2% resolution rate",
                "claim_type": "benchmark",
                "verification_status": "verified",
                "quote_or_metric": "46.2% on SWE-bench",
            }
        ],
        originality_summary="First local side-by-side AST refactoring benchmark with zero prompt alterations.",
        dry_run=True,
    )

    result = engine.generate_export_package(payload)

    assert result.package_slug.endswith("gemini-2-vs-qwen-2-5-benchmark")
    assert "sources.md" in result.files
    assert "evidence-summary.md" in result.files
    assert "script.md" in result.files
    assert "asset-requirements.md" in result.files
    assert "manifest.json" in result.files
    assert "youtube/title.txt" in result.files
    assert "facebook/caption.txt" in result.files
    assert "instagram/caption.txt" in result.files
    assert "tiktok/caption.txt" in result.files
    assert len(result.checksum) == 64
    assert result.manifest_data["sources_count"] == 1
    assert result.manifest_data["claims_count"] == 1


def test_export_engine_disk_write_and_checksum_integrity(tmp_path: Path):
    engine = ExportEngine()
    payload = ExportEngineInput(
        content_item_id="item-test-456",
        working_title="Local AI Workflow Benchmark",
        slug="local-ai-workflow",
        format="short_vertical",
        platform_target="youtube",
        script_title="Local AI Workflow Benchmark",
        sections=[
            {
                "section_type": "hook",
                "heading": "Hook",
                "narration": "Testing local agents without cloud SaaS.",
                "visual_cue": "Fast typing in terminal",
                "estimated_seconds": 6,
                "word_count": 10,
                "linked_claim_ids": [],
            }
        ],
        sources=[
            {
                "title": "Local Agent Paper",
                "url": "https://arxiv.org/abs/example",
                "source_type": "academic_paper",
                "author_or_org": "AI Labs",
                "excerpt": "Local models achieve 90% accuracy with 0 egress cost.",
            }
        ],
        claims=[
            {
                "claim_text": "Local agents have 0 cloud egress cost",
                "claim_type": "cost",
                "verification_status": "verified",
                "quote_or_metric": "$0.00 cloud egress",
            }
        ],
        dry_run=False,
    )

    result = engine.generate_export_package(payload, base_dir=tmp_path)

    export_dir = Path(result.export_dir)
    assert export_dir.exists()
    assert (export_dir / "sources.md").is_file()
    assert (export_dir / "evidence-summary.md").is_file()
    assert (export_dir / "script.md").is_file()
    assert (export_dir / "asset-requirements.md").is_file()
    assert (export_dir / "manifest.json").is_file()
    assert (export_dir / "youtube" / "title.txt").is_file()
    assert (export_dir / "youtube" / "description.txt").is_file()

    # Verify SHA256 integrity of all files against manifest
    manifest_data = json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))
    for rel_file, expected_hash in manifest_data["file_checksums"].items():
        if rel_file == "manifest.json":
            continue
        actual_content = (export_dir / rel_file).read_text(encoding="utf-8")
        actual_hash = hashlib.sha256(actual_content.encode("utf-8")).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_file}"


@pytest.mark.asyncio
async def test_export_engine_standard_context_run():
    engine = ExportEngine()
    context = EngineContext(
        run_id="run-exp-001",
        trigger="manual",
        dry_run=True,
        parameters={
            "content_item_id": "item-ctx-789",
            "working_title": "Context Test Item",
            "slug": "context-test-item",
            "format": "youtube_long",
            "dry_run": True,
        },
    )

    result = await engine.run(context)
    assert result.success is True
    assert result.output_count > 0
    assert result.engine_id == "export"

    dry_result = await engine.dry_run(context)
    assert dry_result.success is True


def test_export_engine_explain():
    engine = ExportEngine()
    exp = engine.explain("item-123")
    assert exp.result_id == "item-123"
    assert len(exp.factors) >= 4
