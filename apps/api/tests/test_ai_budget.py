import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.engines.ai.contracts import StructuredGenerationRequest
from app.engines.ai.engine import AIProviderEngine


@pytest.mark.asyncio
async def test_daily_budget_blocks_live_provider_call(db_session: AsyncSession, monkeypatch):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "MAX_AI_COST_PER_DAY", 0.0)
    engine = AIProviderEngine()
    request = StructuredGenerationRequest(
        prompt="Write a short evidence-based explanation.",
        response_schema={"type": "object", "properties": {}, "additionalProperties": True},
        max_tokens=128,
        metadata={"project_id": "budget-test-family", "project_spend_usd": 0.0},
    )

    response = await engine.generate_structured(request, session=db_session)

    assert response.success is False
    assert "Daily AI budget would be exceeded" in (response.error_message or "")


@pytest.mark.asyncio
async def test_project_budget_uses_family_spend_override_without_provider_call(
    db_session: AsyncSession, monkeypatch
):
    monkeypatch.setattr(settings, "AI_MOCK_MODE", False)
    monkeypatch.setattr(settings, "MAX_AI_COST_PER_DAY", 10.0)
    monkeypatch.setattr(settings, "MAX_GENERATION_COST_PER_PROJECT", 0.01)
    engine = AIProviderEngine()
    request = StructuredGenerationRequest(
        prompt="Write a short evidence-based explanation.",
        response_schema={"type": "object", "properties": {}, "additionalProperties": True},
        max_tokens=128,
        metadata={"project_id": "budget-test-family", "project_spend_usd": 0.01},
    )

    response = await engine.generate_structured(request, session=db_session)

    assert response.success is False
    assert "Content-family AI budget would be exceeded" in (response.error_message or "")
