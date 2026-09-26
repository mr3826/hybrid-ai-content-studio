from typing import Dict, List, Optional
from app.engines.core.base import BaseEngine, EngineHealth


class EngineRegistry:
    def __init__(self):
        self._engines: Dict[str, BaseEngine] = {}

    def register(self, engine: BaseEngine) -> None:
        if engine.id in self._engines:
            raise ValueError(f"Engine '{engine.id}' is already registered.")
        self._engines[engine.id] = engine

    def get(self, engine_id: str) -> Optional[BaseEngine]:
        return self._engines.get(engine_id)

    def list_all(self) -> List[BaseEngine]:
        return list(self._engines.values())

    def health_all(self) -> Dict[str, EngineHealth]:
        return {eid: engine.health() for eid, engine in self._engines.items()}


# Global instance
engine_registry = EngineRegistry()
