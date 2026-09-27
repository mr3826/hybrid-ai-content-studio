from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[Any]):
    """Storage boundary for platform metrics, performance signals, and feedback loops."""

    async def record_performance(self, post_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        return metrics

    async def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        return {"days": days, "total_views": 0, "top_performing_topics": []}
