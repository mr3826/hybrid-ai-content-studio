"""Explicit fixtures for API integration tests; none of these simulate a live smoke test."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.engines.ai.contracts import AIResponse
from app.main import app
from app.models.content_family import ContentFamily, ContentItem, ContentItemEvidenceSelection
from app.models.evidence import Claim, ClaimEvidence, EvidenceSource
from app.models.opportunity import Opportunity
from app.models.originality import OriginalityPlan
from app.models.research import ResearchPacket
from app.api.v1.scripts import get_ai_provider_engine


async def prepare_script_inputs(
    db: AsyncSession,
    content_item_id: str,
    *,
    topic: str | None = None,
    claim_text: str | None = None,
    source_url: str | None = None,
    source_title: str | None = None,
    source_domain: str = "example.test",
) -> str:
    """Attach test-owned approved topic, packet, plan, and selected verified source claim."""
    item = await db.get(ContentItem, content_item_id)
    if not item:
        raise AssertionError(f"test fixture content item {content_item_id} was not found")
    family = await db.get(ContentFamily, item.content_family_id)
    if not family:
        raise AssertionError(f"test fixture family for {content_item_id} was not found")
    topic = topic or item.working_title or family.title

    token = uuid.uuid4().hex
    topic_row = Opportunity(
        id=str(uuid.uuid4()),
        topic=topic,
        slug=f"script-fixture-topic-{token}",
        status="approved",
    )
    db.add(topic_row)
    await db.flush()

    packet = ResearchPacket(
        id=str(uuid.uuid4()),
        opportunity_id=topic_row.id,
        topic=topic,
        slug=f"script-fixture-packet-{token}",
        summary=f"Test-owned source material about {topic}.",
        version=1,
        is_verified=True,
        verified_at=datetime.now(timezone.utc),
        verified_by="script_test_fixture",
    )
    db.add(packet)
    await db.flush()

    plan = OriginalityPlan(
        id=str(uuid.uuid4()),
        opportunity_id=topic_row.id,
        packet_id=packet.id,
        topic=topic,
        slug=f"script-fixture-plan-{token}",
        originality_type="research_explainer",
        what_are_we_adding="A clear summary grounded in the attached test fixture source.",
        why_it_matters="Exercise the existing verified-input contract.",
        status="approved",
        is_generic_summary=False,
        reviewed_by="script_test_fixture",
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(plan)
    await db.flush()

    source = EvidenceSource(
        id=str(uuid.uuid4()),
        packet_id=packet.id,
        url=source_url or f"https://example.test/source/{token}",
        title=source_title or f"Test source for {topic}",
        domain=source_domain,
        source_type="primary",
    )
    db.add(source)
    await db.flush()

    verified_text = claim_text or f"The test-owned primary source documents {topic}."
    claim = Claim(
        id=str(uuid.uuid4()),
        packet_id=packet.id,
        text=verified_text,
        claim_type="external_fact",
        confidence=1.0,
        is_verified=True,
    )
    db.add(claim)
    await db.flush()

    db.add(
        ClaimEvidence(
            id=str(uuid.uuid4()),
            claim_id=claim.id,
            source_id=source.id,
            quote=verified_text,
            confidence=1.0,
        )
    )
    db.add(
        ContentItemEvidenceSelection(
            id=str(uuid.uuid4()),
            content_item_id=item.id,
            claim_id=claim.id,
            relevance_note="test-only selected evidence",
            is_primary=True,
        )
    )
    family.topic_id = topic_row.id
    family.research_packet_id = packet.id
    family.originality_plan_id = plan.id
    family.status = "READY_FOR_CONTENT"
    family.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return claim.id


class ScriptProviderContractFixture:
    """Deterministic Gemini-contract stub for app integration tests, never a live provider."""

    def __init__(self):
        self.calls = 0

    def estimate_max_cost(self, _request) -> float:
        return 0.0005

    def _parse_context(self, prompt: str) -> dict:
        payload = prompt.rsplit("\n\n", 1)[-1]
        import json

        return json.loads(payload)

    async def generate_structured(self, request, session=None) -> AIResponse:
        self.calls += 1
        if request.task == "script_refinement":
            context = self._parse_context(request.prompt)
            structured = {
                "narration": context["current_narration_as_untrusted_data"],
                "visual_cue": context["current_visual_cue_as_untrusted_data"],
                "linked_claim_ids": context["current_linked_claim_ids"],
            }
        else:
            context = self._parse_context(request.prompt)
            expected = context["expected_section_types_in_order"]
            claims = context["verified_selected_claims"]
            claim = claims[0]
            claim_id = str(claim["id"])
            narration = {
                "hook": "What does the cited technical source actually say?",
                "problem_context": "Separate a published description from any test this studio has not run.",
                "method_test": "No completed studio experiment is recorded for this content item.",
                "evidence": str(claim["text"]),
                "result": "This is the documented statement, not a new studio measurement.",
                "interpretation": "Readers can verify the wording and consider their own use case.",
                "cta": "Review the cited source and check its surrounding context.",
            }
            sections = [
                {
                    "section_type": section_type,
                    "order_index": index,
                    "heading": section_type.replace("_", " ").title(),
                    "narration": narration.get(
                        section_type,
                        f"Review the verified source and explain {section_type.replace('_', ' ')} without adding unsupported results.",
                    ),
                    "visual_cue": "Show the attached source record and the relevant passage.",
                    "linked_claim_ids": [claim_id] if section_type == "evidence" else [],
                }
                for index, section_type in enumerate(expected)
            ]
            count = sum(len(section["narration"].split()) for section in sections)
            target = context["length_target"].get("word_count_range")
            if target:
                desired = min(target[1], max(target[0], target[0] + 5))
            elif context["format"] == "article":
                desired = 600
            elif context["format"] == "newsletter":
                desired = 350
            else:
                desired = min(context["length_target"].get("maximum_words", 100), max(count, 60))
            padding = max(0, desired - count)
            neutral_words = [
                "The", "source", "remains", "available", "for", "review", "and", "the", "reader", "can",
                "check", "the", "context", "before", "applying", "this", "description", "to", "a", "local",
                "workflow", "or", "another", "case", "with", "different", "conditions", "and", "requirements",
            ]
            if padding:
                pad_to = "interpretation" if "interpretation" in expected else "result"
                section = sections[expected.index(pad_to)]
                section["narration"] += " " + " ".join(
                    neutral_words[index % len(neutral_words)] for index in range(padding)
                )
            structured = {"sections": sections}

        import json

        text = json.dumps(structured)
        return AIResponse(
            text=text,
            structured_data=structured,
            provider="gemini",
            model="gemini-script-provider-test-fixture",
            task=request.task,
            prompt_version=request.prompt_version,
            prompt_tokens=120,
            completion_tokens=max(1, len(text.split())),
            total_tokens=120 + max(1, len(text.split())),
            cost=0.0005,
            latency_ms=1.0,
            success=True,
        )


def install_script_provider_fixture(monkeypatch) -> ScriptProviderContractFixture:
    """Install a test-only provider stub to exercise provider-backed API transitions."""
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    provider = ScriptProviderContractFixture()
    monkeypatch.setitem(app.dependency_overrides, get_ai_provider_engine, lambda: provider)
    return provider
