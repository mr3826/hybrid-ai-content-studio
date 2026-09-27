from typing import Generic, TypeVar, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository interface for SQLite-backed studio storage."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
