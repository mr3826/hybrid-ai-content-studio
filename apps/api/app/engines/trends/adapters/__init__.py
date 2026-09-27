from app.engines.trends.adapters.base import BaseSignalAdapter
from app.engines.trends.adapters.rss_signals import RssSignalAdapter, extract_entities_and_keywords
from app.engines.trends.adapters.manual_signals import ManualSignalAdapter
from app.engines.trends.adapters.future_providers import (
    SearchTrendSignalAdapter,
    RedditSignalAdapter,
    HackerNewsSignalAdapter,
    GitHubSignalAdapter,
    YouTubeDiscoverySignalAdapter,
)

__all__ = [
    "BaseSignalAdapter",
    "RssSignalAdapter",
    "extract_entities_and_keywords",
    "ManualSignalAdapter",
    "SearchTrendSignalAdapter",
    "RedditSignalAdapter",
    "HackerNewsSignalAdapter",
    "GitHubSignalAdapter",
    "YouTubeDiscoverySignalAdapter",
]
