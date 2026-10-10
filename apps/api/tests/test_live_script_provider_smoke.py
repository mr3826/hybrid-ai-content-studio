"""One-request Gemini script smoke; enabled only by the root isolation plugin."""

import uuid

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.scripts import get_ai_provider_engine
from app.core.config import settings
from app.engines.ai.engine import AIProviderEngine
from app.main import app
from script_test_utils import prepare_script_inputs


@pytest.mark.asyncio
@pytest.mark.live_provider
async def test_live_gemini_script_smoke_preflights_and_persists_one_grounded_script(
    client: AsyncClient, db_session: AsyncSession, monkeypatch, pytestconfig: pytest.Config
):
    if not pytestconfig.getoption("--run-live-provider-smoke", default=False):
        pytest.skip("Pass --run-live-provider-smoke to opt into one live Gemini request.")
    if not settings.GEMINI_API_KEY:
        pytest.fail(
            "Live Gemini smoke requires Settings.GEMINI_API_KEY to resolve a credential "
            "from CONTENT_STUDIO_GEMINI, GEMINI_API_KEY, GEMINI_KEY, GOOGLE_API_KEY, "
            "or .env. No provider request was sent."
        )

    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    model = settings.GEMINI_MODEL.strip()
    if not model:
        pytest.fail("Live Gemini smoke requires a nonempty GEMINI_MODEL. No provider request was sent.")
    api_key = settings.GEMINI_API_KEY
    engine = AIProviderEngine()
    monkeypatch.setitem(app.dependency_overrides, get_ai_provider_engine, lambda: engine)

    print("LIVE_GEMINI_SMOKE phase=model_preflight status=started")
    async with httpx.AsyncClient(timeout=20) as provider_client:
        model_response = await provider_client.get(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}",
            headers={"x-goog-api-key": api_key},
        )
    if model_response.status_code != 200:
        # Never print provider response bodies because they may contain request details.
        pytest.fail(
            f"Gemini model preflight failed with HTTP {model_response.status_code}; "
            "no script generation request was sent. Check model access and credential configuration."
        )
    model_info = model_response.json()
    model_name = str(model_info.get("name", "")).removeprefix("models/")
    supported_methods = model_info.get("supportedGenerationMethods", [])
    if model_name != model or "generateContent" not in supported_methods:
        pytest.fail(
            "Gemini model preflight did not confirm the configured model supports generateContent; "
            "no script generation request was sent."
        )
    print(f"LIVE_GEMINI_SMOKE phase=model_preflight status=passed model={model}")

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

    print("LIVE_GEMINI_SMOKE phase=script_generation status=started request_count=1")
    response = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 60},
    )
    assert response.status_code == 200, response.text
    script = response.json()
    metadata = script["generation_metadata"]
    assert metadata["generation_mode"] == "live"
    assert metadata["provider"] == "gemini"
    assert metadata["model"] == model
    assert metadata["total_tokens"] > 0
    assert metadata["research_packet_id"]
    assert metadata["research_packet_version"] > 0
    assert metadata["originality_plan_id"]
    assert claim_id in metadata["evidence_claim_ids"]
    assert metadata["fallback_used"] is False
    assert [attempt["provider"] for attempt in metadata["provider_attempts"]] == ["gemini"]
    assert script["is_approved"] is False
    evidence_sections = [
        section for section in script["sections"] if section["section_type"] == "evidence"
    ]
    assert evidence_sections
    assert any(claim_id in section["linked_claim_ids"] for section in evidence_sections)
    assert "sqlite" in " ".join(section["narration"] for section in script["sections"]).casefold()
    assert all("mock preview" not in section["narration"].casefold() for section in script["sections"])

    persisted_response = await client.get(f"/api/v1/scripts/item/{item_id}")
    assert persisted_response.status_code == 200, persisted_response.text
    persisted_script = persisted_response.json()
    assert persisted_script["id"] == script["id"]
    assert persisted_script["is_approved"] is False
    persisted_metadata = persisted_script["generation_metadata"]
    for key in (
        "generation_mode",
        "provider",
        "model",
        "total_tokens",
        "research_packet_id",
        "research_packet_version",
        "originality_plan_id",
        "evidence_claim_ids",
    ):
        assert persisted_metadata[key] == metadata[key]
    persisted_evidence_sections = [
        section for section in persisted_script["sections"] if section["section_type"] == "evidence"
    ]
    assert any(claim_id in section["linked_claim_ids"] for section in persisted_evidence_sections)
    print(
        "LIVE_GEMINI_SMOKE phase=script_generation status=passed "
        f"item_id={item_id} provider=gemini model={model} "
        f"tokens={metadata['total_tokens']} cost_usd={metadata['estimated_cost_usd']}"
    )
