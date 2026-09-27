from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Any]):
    """Storage boundary for audio tracks, video clips, subtitles, and thumbnails."""

    async def register_asset(self, project_id: str, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        return asset_data

    async def list_assets_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        return []

    async def delete_asset(self, asset_id: str) -> bool:
        return True
