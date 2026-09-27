import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineHealth,
    EngineResult,
)
from app.models.engine_run import EngineRunRecord


class EngineRegistry:
    def __init__(self):
        self._engines: Dict[str, BaseEngine] = {}

    def register(self, engine: BaseEngine, replace: bool = False) -> None:
        if engine.id in self._engines and not replace:
            raise ValueError(f"Engine '{engine.id}' is already registered.")
        engine.validate_config()
        self._engines[engine.id] = engine

    def unregister(self, engine_id: str) -> None:
        if engine_id in self._engines:
            del self._engines[engine_id]

    def get(self, engine_id: str) -> Optional[BaseEngine]:
        return self._engines.get(engine_id)

    def list_all(self) -> List[BaseEngine]:
        return list(self._engines.values())

    def health_all(self) -> Dict[str, EngineHealth]:
        return {eid: engine.health() for eid, engine in self._engines.items()}

    def validate_dependencies(self, engine_id: str) -> List[str]:
        """Validate that all declared dependencies of an engine exist and are registered.
        Returns a list of missing dependency IDs, or an empty list if valid.
        """
        engine = self.get(engine_id)
        if not engine:
            raise ValueError(f"Engine '{engine_id}' not found.")

        missing = []
        for dep in engine.manifest.dependencies:
            if dep not in self._engines:
                missing.append(dep)
        return missing

    async def execute_engine(
        self,
        engine_id: str,
        context: Optional[EngineContext] = None,
        dry_run: bool = False,
        session: Optional[AsyncSession] = None,
    ) -> EngineResult:
        """Run or dry-run an engine with dependency validation, timing, and database audit logging."""
        engine = self.get(engine_id)
        if not engine:
            raise ValueError(f"Engine '{engine_id}' not found.")

        missing_deps = self.validate_dependencies(engine_id)
        if missing_deps:
            raise RuntimeError(
                f"Cannot execute '{engine_id}': missing dependencies {missing_deps}."
            )

        if context is None:
            context = EngineContext(
                run_id=str(uuid.uuid4())[:8],
                dry_run=dry_run,
                trigger="manual",
            )
        else:
            context.dry_run = dry_run

        start_time = datetime.now(timezone.utc)
        t0 = time.perf_counter()

        try:
            if dry_run:
                result = await engine.dry_run(context)
            else:
                result = await engine.run(context)
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((time.perf_counter() - t0) * 1000)
            result = EngineResult(
                engine_id=engine.id,
                engine_version=engine.version,
                run_id=context.run_id,
                success=False,
                started_at=start_time,
                ended_at=end_time,
                duration_ms=duration_ms,
                summary=f"Execution error: {str(e)}",
                errors=[str(e)],
            )

        # Log run in database if session is provided
        if session:
            record = EngineRunRecord(
                engine_id=result.engine_id,
                engine_version=result.engine_version,
                run_id=result.run_id,
                trigger=context.trigger,
                status="dry_run" if dry_run else ("completed" if result.success else "failed"),
                started_at=result.started_at,
                ended_at=result.ended_at,
                duration_ms=result.duration_ms,
                input_count=result.input_count,
                output_count=result.output_count,
                rejected_count=result.rejected_count,
                error_count=result.error_count,
                cost=result.cost,
                summary=result.summary,
                parameters=context.parameters,
                errors=result.errors,
                explanations=result.explanations,
            )
            session.add(record)
            await session.commit()

        return result


# Global instance
engine_registry = EngineRegistry()
