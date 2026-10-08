"""Opt-in real-provider smoke; never substitute a mock provider for this check."""

import os
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from script_test_utils import prepare_script_inputs


LIVE_SMOKE_ENABLED = os.environ.get("RUN_LIVE_AI_SMOKE") == "1"
LIVE_PROVIDER_CONFIGURED = bool(settings.GEMINI_API_KEY or settings.QWEN_API_KEY)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not LIVE_SMOKE_ENABLED or not LIVE_PROVIDER_CONFIGURED,
    reason="Set RUN_LIVE_AI_SMOKE=1 and configure a real provider key to run the live smoke.",
)
async def test_live_provider_script_uses_verified_official_source(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    topic = "SQLite WAL reader and writer concurrency"
    family_res = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"{topic} {uuid.uuid4().hex[:8]}",
            "content_pillar": "Database engineering",
            "original_value_type": "research_explainer",
            "summary": "Explain one verified SQLite WAL behavior.",
        },
    )
    assert family_res.status_code == 201, family_res.text
    family_id = family_res.json()["id"]

    item_res = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": topic,
            "angle": "Explain the documented concurrency rule without adding benchmark claims.",
            "hook_type": "direct_value",
            "original_value_connection": "Translate one official SQLite behavior into plain language.",
            "viewer_value": "Understand the WAL reader and writer concurrency limit.",
        },
    )
    assert item_res.status_code == 201, item_res.text
    item_id = item_res.json()["id"]

    claim_text = "In SQLite WAL mode, readers and writers can run at the same time."
    claim_id = await prepare_script_inputs(
        db_session,
        item_id,
        topic=topic,
        claim_text=claim_text,
        source_url="https://www.sqlite.org/wal.html",
        source_title="Write-Ahead Logging",
        source_domain="sqlite.org",
    )

    response = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 60},
    )
    assert response.status_code == 200, response.text
    script = response.json()
    metadata = script["generation_metadata"]
    assert metadata["generation_mode"] == "live"
    assert metadata["provider"] in {"gemini", "qwen"}
    assert metadata["model"] and "mock" not in metadata["model"].casefold()
    assert metadata["total_tokens"] > 0
    evidence_sections = [section for section in script["sections"] if section["section_type"] == "evidence"]
    assert evidence_sections
    assert any(claim_id in section["linked_claim_ids"] for section in evidence_sections)
    assert "sqlite" in " ".join(section["narration"] for section in script["sections"]).casefold()
    assert all("mock preview" not in section["narration"].casefold() for section in script["sections"])
    print(
        "LIVE_SCRIPT_SMOKE "
        f"item_id={item_id} provider={metadata['provider']} model={metadata['model']} "
        f"tokens={metadata['total_tokens']} cost_usd={metadata['estimated_cost_usd']}"
    )
