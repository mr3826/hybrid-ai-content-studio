from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.engines.trends.adapters.base import BaseSignalAdapter
from app.engines.trends.adapters.rss_signals import extract_entities_and_keywords
from app.engines.trends.contracts import TopicSignal


class ManualSignalAdapter(BaseSignalAdapter):
    """Adapter for user-injected trend signals or custom observations."""

    def __init__(self, manual_signals: Optional[List[TopicSignal]] = None):
        self._signals: List[TopicSignal] = manual_signals or []

    @property
    def source_type(self) -> str:
        return "manual"

    def add_signal(
        self,
        title: str,
        source_name: str = "Manual Entry",
        summary: str = "",
        url: Optional[str] = None,
        pillar: Optional[str] = None,
        trust_weight: float = 0.9,
    ) -> TopicSignal:
        entities = extract_entities_and_keywords(f"{title} {summary}")
        sig = TopicSignal(
            signal_id=str(uuid.uuid4()),
            source_type="manual",
            source_name=source_name,
            title=title,
            url=url,
            summary=summary,
            published_at=datetime.now(timezone.utc),
            entities=entities,
            pillar=pillar,
            trust_weight=trust_weight,
            is_in_niche=True,
            metadata={"source": "manual_user_input"},
        )
        self._signals.append(sig)
        return sig

    async def fetch_signals(self, window_hours: int = 72) -> List[TopicSignal]:
        return list(self._signals)
