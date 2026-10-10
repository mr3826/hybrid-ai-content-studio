import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.scripts import get_ai_provider_engine
from app.core.config import settings
from app.engines.ai.contracts import AIResponse
from app.engines.ai.engine import AIProviderEngine
from app.main import app
from app.models.content_family import ContentFamily
from app.models.evidence import Claim, ClaimEvidence, EvidenceSource
from app.models.opportunity import Opportunity
from app.models.originality import OriginalityPlan
from app.models.research import ResearchPacket
from script_test_utils import ScriptProviderContractFixture


@pytest.mark.asyncio
async def test_scripts_health(client: AsyncClient):
    res = await client.get("/api/v1/scripts/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["engine_id"] == "content"


async def _create_approved_item(client: AsyncClient, db_session: AsyncSession, topic: str, claim_text: str):
    token = uuid.uuid4().hex[:10]
    family_response = await client.post(
        "/api/v1/content-families",
        json={
            "title": f"{topic} ({token})",
            "content_pillar": "Technical explainers",
            "original_value_type": "research_explainer",
            "summary": f"An evidence-grounded explainer about {topic}.",
        },
    )
    assert family_response.status_code == 201, family_response.text
    family_id = family_response.json()["id"]

    topic_record = Opportunity(
        id=str(uuid.uuid4()),
        topic=topic,
        slug=f"{token}-topic",
        status="approved",
    )
    packet = ResearchPacket(
        id=str(uuid.uuid4()),
        opportunity_id=topic_record.id,
        topic=topic,
        slug=f"{token}-packet",
        summary=f"Verified source notes for {topic}.",
        version=1,
        is_verified=True,
        verified_at=datetime.now(timezone.utc),
        verified_by="test_reviewer",
    )
    plan = OriginalityPlan(
        id=str(uuid.uuid4()),
        opportunity_id=topic_record.id,
        packet_id=packet.id,
        topic=topic,
        slug=f"{token}-plan",
        originality_type="research_explainer",
        what_are_we_adding=f"A concise explanation of {topic} from the cited primary source.",
        why_it_matters="Help viewers understand the documented behavior.",
        status="approved",
        is_generic_summary=False,
        reviewed_by="test_reviewer",
        reviewed_at=datetime.now(timezone.utc),
    )
    source = EvidenceSource(
        id=str(uuid.uuid4()),
        packet_id=packet.id,
        url="https://sqlite.org/wal.html",
        title="Write-Ahead Logging",
        domain="sqlite.org",
        source_type="primary",
        published_at=None,
    )
    claim = Claim(
        id=str(uuid.uuid4()),
        packet_id=packet.id,
        text=claim_text,
        claim_type="external_fact",
        confidence=1.0,
        is_verified=True,
    )
    claim_evidence = ClaimEvidence(
        id=str(uuid.uuid4()),
        claim_id=claim.id,
        source_id=source.id,
        quote=claim_text,
        confidence=1.0,
    )
    db_session.add(topic_record)
    await db_session.flush()
    db_session.add(packet)
    await db_session.flush()
    db_session.add(plan)
    await db_session.flush()
    db_session.add(source)
    await db_session.flush()
    db_session.add(claim)
    await db_session.flush()
    db_session.add(claim_evidence)
    await db_session.commit()

    family = await db_session.get(ContentFamily, family_id)
    family.topic_id = topic_record.id
    family.research_packet_id = packet.id
    family.originality_plan_id = plan.id
    await db_session.commit()

    approved = await client.post(
        f"/api/v1/content-families/{family_id}/approve",
        json={"reviewer": "test_creator"},
    )
    assert approved.status_code == 200, approved.text

    item_response = await client.post(
        f"/api/v1/content-families/{family_id}/items",
        json={
            "format": "short_vertical",
            "platform_target": "youtube",
            "working_title": f"A short explainer about {topic}",
            "angle": f"Explain {topic} using only the verified source statement.",
            "hook_type": "curiosity_gap",
            "original_value_connection": "A plain-language explanation grounded in an official source.",
            "viewer_value": "Understand the cited technical behavior.",
            "claim_ids": [claim.id],
        },
    )
    assert item_response.status_code == 201, item_response.text
    return item_response.json()["id"], claim_text


@pytest.mark.asyncio
async def test_script_generation_uses_verified_selected_claims_and_keeps_mock_unapprovable(
    client: AsyncClient, db_session: AsyncSession
):
    item_id, claim_text = await _create_approved_item(
        client,
        db_session,
        "SQLite write-ahead logging",
        "SQLite documentation says readers and writers can proceed concurrently.",
    )

    generated = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 60},
    )
    assert generated.status_code == 200, generated.text
    script = generated.json()
    script_id = script["id"]
    assert script["format"] == "short_vertical"
    assert [section["section_type"] for section in script["sections"]] == [
        "hook", "problem_context", "evidence", "result", "cta"
    ]
    assert script["total_word_count"] > 0
    assert script["estimated_duration_sec"] > 0
    assert script["generation_metadata"]["generation_mode"] == "mock"
    assert script["generation_metadata"]["approval_eligible"] is False
    assert script["generation_metadata"]["provider"] == "mock"
    assert "cannot be approved" in " ".join(script["generation_metadata"]["warnings"])
    assert claim_text in script["sections"][2]["narration"]
    assert script["sections"][2]["linked_claim_ids"]
    assert script["sections"][2]["evidence_category"] == "sourced_fact"

    check_item = await client.get(f"/api/v1/content-items/{item_id}")
    assert check_item.status_code == 200
    assert check_item.json()["status"] == "SCRIPT_REVIEW"

    by_item = await client.get(f"/api/v1/scripts/item/{item_id}")
    assert by_item.status_code == 200
    assert by_item.json()["id"] == script_id

    hook = script["sections"][0]
    refined = await client.post(
        f"/api/v1/scripts/{script_id}/sections/{hook['id']}/refine",
        json={"refinement_type": "shorten", "guidance": "Make the opening concise."},
    )
    assert refined.status_code == 200, refined.text
    assert refined.json()["refinement"]["section_id"] == hook["id"]
    assert len(refined.json()["script"]["generation_metadata"]["operation_history"]) == 2
    assert refined.json()["script"]["generation_metadata"]["generation_mode"] == "mock"
    assert refined.json()["script"]["generation_metadata"]["approval_eligible"] is False

    edited = await client.patch(
        f"/api/v1/scripts/{script_id}/sections/{hook['id']}",
        json={"narration": "A creator-edited line that makes no factual claim."},
    )
    assert edited.status_code == 200, edited.text
    revisions = await client.get(f"/api/v1/scripts/{script_id}/revisions")
    assert revisions.status_code == 200
    assert len(revisions.json()) >= 3

    restored = await client.post(
        f"/api/v1/scripts/{script_id}/revisions/{revisions.json()[-1]['id']}/restore"
    )
    assert restored.status_code == 200, restored.text

    quality = await client.post(f"/api/v1/scripts/{script_id}/quality-check")
    assert quality.status_code == 200
    assert quality.json()["is_approvable"] is False
    assert "mock_output_unverified" in quality.json()["blocking_reasons"]

    # Human override cannot turn a mock preview into an approved production script.
    approval = await client.post(
        f"/api/v1/scripts/{script_id}/approve",
        json={"reviewer": "test_creator", "override_reason": "Test only."},
    )
    assert approval.status_code == 422
    assert "missing_live_provider_provenance" in approval.json()["detail"]["blocking_reasons"]
    assert approval.json()["detail"]["message"] == (
        "Mock and legacy-unverified scripts cannot be approved. "
        "Generate the script with a configured live AI provider first."
    )


@pytest.mark.asyncio
async def test_unapproved_or_unverified_research_cannot_generate_script(client: AsyncClient):
    response = await client.post(
        "/api/v1/content-families",
        json={"title": f"Unapproved family {uuid.uuid4().hex}", "summary": "Awaiting review."},
    )
    family = response.json()
    item_response = await client.post(
        f"/api/v1/content-families/{family['id']}/items",
        json={
            "format": "short_vertical",
            "working_title": "Unverified script item",
            "angle": "A pending test case.",
            "original_value_connection": "No approved research yet.",
        },
    )
    assert item_response.status_code == 201
    response = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_response.json()["id"]},
    )
    assert response.status_code == 409
    assert "Approve this content family" in response.json()["detail"]


@pytest.mark.asyncio
async def test_separate_content_families_do_not_mix_selected_claims(
    client: AsyncClient, db_session: AsyncSession
):
    first_item_id, first_claim = await _create_approved_item(
        client,
        db_session,
        "SQLite WAL readers",
        "SQLite documentation says readers and writers can proceed concurrently.",
    )
    second_item_id, second_claim = await _create_approved_item(
        client,
        db_session,
        "SQLite WAL checkpoints",
        "SQLite documentation explains that checkpointing transfers WAL content into the database file.",
    )

    first = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": first_item_id, "target_duration_sec": 60},
    )
    second = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": second_item_id, "target_duration_sec": 60},
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    first_evidence = first.json()["sections"][2]["narration"]
    second_evidence = second.json()["sections"][2]["narration"]
    assert first_claim in first_evidence
    assert first_claim not in second_evidence
    assert second_claim in second_evidence


@pytest.mark.asyncio
async def test_gemini_script_persists_provenance_evidence_and_unapproved_state(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "script-test-gemini-key")
    monkeypatch.setattr(settings, "MAX_AI_COST_PER_DAY", 100.0)
    monkeypatch.setattr(settings, "MAX_GENERATION_COST_PER_PROJECT", 100.0)

    engine = AIProviderEngine()
    script_fixture = ScriptProviderContractFixture()

    monkeypatch.setattr(engine.gemini_adapter, "generate_structured", script_fixture.generate_structured)
    monkeypatch.setitem(
        app.dependency_overrides, get_ai_provider_engine, lambda: engine
    )

    item_id, _claim_text = await _create_approved_item(
        client,
        db_session,
        "SQLite write-ahead logging",
        "SQLite documentation says readers and writers can proceed concurrently.",
    )
    generated = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 60},
    )

    assert generated.status_code == 200, generated.text
    script = generated.json()
    metadata = script["generation_metadata"]
    assert metadata["generation_mode"] == "live"
    assert metadata["provider"] == "gemini"
    assert metadata["model"] == "gemini-script-provider-test-fixture"
    assert metadata["fallback_used"] is False
    assert metadata["estimated_cost_usd"] > 0
    assert metadata["research_packet_id"]
    assert metadata["research_packet_version"] == 1
    assert metadata["originality_plan_id"]
    selected_claim_ids = metadata["evidence_claim_ids"]
    assert selected_claim_ids
    evidence_sections = [
        section for section in script["sections"] if section["section_type"] == "evidence"
    ]
    assert any(
        claim_id in section["linked_claim_ids"]
        for claim_id in selected_claim_ids
        for section in evidence_sections
    )
    assert script["is_approved"] is False
    assert [attempt["provider"] for attempt in metadata["provider_attempts"]] == ["gemini"]
    assert script_fixture.calls == 1

    persisted = await client.get(f"/api/v1/scripts/item/{item_id}")
    assert persisted.status_code == 200, persisted.text
    persisted_script = persisted.json()
    assert persisted_script["id"] == script["id"]
    assert persisted_script["is_approved"] is False
    assert persisted_script["generation_metadata"]["provider"] == "gemini"
    assert persisted_script["generation_metadata"]["fallback_used"] is False


@pytest.mark.asyncio
async def test_gemini_failure_returns_recovery_guidance_without_persisting_a_draft(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "script-test-gemini-key")
    engine = AIProviderEngine()
    calls = []

    async def fail_once(request):
        calls.append(request)
        return AIResponse(
            text="",
            provider="gemini",
            model=settings.GEMINI_MODEL,
            task=request.task,
            success=False,
            failure_category="rate_limit",
            error_message="Gemini HTTP 429: Resource exhausted.",
        )

    monkeypatch.setattr(engine.gemini_adapter, "generate_structured", fail_once)
    monkeypatch.setitem(app.dependency_overrides, get_ai_provider_engine, lambda: engine)
    item_id, _claim_text = await _create_approved_item(
        client,
        db_session,
        "SQLite WAL concurrency failure path",
        "SQLite documentation says readers and writers can proceed concurrently.",
    )

    response = await client.post(
        "/api/v1/scripts/generate",
        json={"content_item_id": item_id, "target_duration_sec": 60},
    )

    assert response.status_code == 429
    assert "quota" in response.json()["detail"].casefold()
    assert "No script draft was persisted." in response.json()["detail"]
    assert len(calls) == 1
    lookup = await client.get(f"/api/v1/scripts/item/{item_id}")
    assert lookup.status_code == 404
