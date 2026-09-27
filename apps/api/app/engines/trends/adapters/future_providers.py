from typing import List, Optional
from app.engines.trends.adapters.base import BaseSignalAdapter
from app.engines.trends.contracts import TopicSignal


class SearchTrendSignalAdapter(BaseSignalAdapter):
    """Stub adapter for future search trend providers (e.g. Google Trends / SerpApi)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    @property
    def source_type(self) -> str:
        return "search_trends"

    async def fetch_signals(self, window_hours: int = 72) -> List[TopicSignal]:
        # Pluggable future integration without unstable scraping
        return []


class RedditSignalAdapter(BaseSignalAdapter):
    """Stub adapter for future Reddit discussions within the niche."""

    @property
    def source_type(self) -> str:
        return "reddit"

    async def fetch_signals(self, window_hours: int = 72) -> List[TopicSignal]:
        return []


class HackerNewsSignalAdapter(BaseSignalAdapter):
    """Stub adapter for future Hacker News submissions and discussions."""

    @property
    def source_type(self) -> str:
        return "hackernews"

    async def fetch_signals(self, window_hours: int = 72) -> List[TopicSignal]:
        return []


class GitHubSignalAdapter(BaseSignalAdapter):
    """Stub adapter for future GitHub repository momentum and trending releases."""

    @property
    def source_type(self) -> str:
        return "github"

    async def fetch_signals(self, window_hours: int = 72) -> List[TopicSignal]:
        return []


class YouTubeDiscoverySignalAdapter(BaseSignalAdapter):
    """Stub adapter for future YouTube trending search & discovery."""

    @property
    def source_type(self) -> str:
        return "youtube"

    async def fetch_signals(self, window_hours: int = 72) -> List[TopicSignal]:
        return []
