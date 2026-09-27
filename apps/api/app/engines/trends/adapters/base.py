from abc import ABC, abstractmethod
from typing import List
from app.engines.trends.contracts import TopicSignal


class BaseSignalAdapter(ABC):
    """Abstract interface for all trend signal adapters."""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Returns the source identifier (e.g. 'rss', 'manual', 'reddit')."""
        pass

    @abstractmethod
    async def fetch_signals(self, window_hours: int = 72) -> List[TopicSignal]:
        """Fetch normalized topic signals within the specified time window."""
        pass
