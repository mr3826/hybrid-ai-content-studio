from abc import ABC, abstractmethod
from typing import Any, Dict
from app.engines.ai.contracts import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    AnalyzeRequest,
    AIResponse,
)


class BaseAIAdapter(ABC):
    """Abstract base adapter for LLM providers."""

    def __init__(self, provider_id: str, default_model: str, cost_rates: Dict[str, float]):
        self.provider_id = provider_id
        self.default_model = default_model
        self.cost_rates = cost_rates

    @abstractmethod
    async def generate_text(self, request: TextGenerationRequest) -> AIResponse:
        """Generate unstructured text response."""
        pass

    @abstractmethod
    async def generate_structured(self, request: StructuredGenerationRequest) -> AIResponse:
        """Generate schema-validated JSON output."""
        pass

    @abstractmethod
    async def analyze(self, request: AnalyzeRequest) -> AIResponse:
        """Analyze content against criteria."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify API connectivity and authentication."""
        pass

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD based on token counts."""
        prompt_rate = self.cost_rates.get("prompt_per_million", 0.0) / 1_000_000.0
        completion_rate = self.cost_rates.get("completion_per_million", 0.0) / 1_000_000.0
        return round((prompt_tokens * prompt_rate) + (completion_tokens * completion_rate), 6)
