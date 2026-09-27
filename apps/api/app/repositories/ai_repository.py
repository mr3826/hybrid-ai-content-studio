import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai import AIInvocationLog
from app.repositories.base import BaseRepository


class AIRepository(BaseRepository[AIInvocationLog]):
    """Repository managing AI invocation logs, telemetry, and budget calculations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def log_invocation(
        self,
        provider: str,
        model: str,
        task: str,
        prompt_version: str = "1.0.0",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        cost: float = 0.0,
        latency_ms: float = 0.0,
        success: bool = True,
        error_message: Optional[str] = None,
        fallback_used: bool = False,
        fallback_reason: Optional[str] = None,
        primary_provider: Optional[str] = None,
        primary_error: Optional[str] = None,
        prompt_hash: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> AIInvocationLog:
        """Create and persist an AI invocation log record."""
        log = AIInvocationLog(
            id=str(uuid.uuid4()),
            provider=provider,
            model=model,
            task=task,
            prompt_version=prompt_version,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            primary_provider=primary_provider,
            primary_error=primary_error,
            prompt_hash=prompt_hash,
            extra_metadata=extra_metadata or {},
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def list_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        provider: Optional[str] = None,
        task: Optional[str] = None,
        success: Optional[bool] = None,
        fallback_used: Optional[bool] = None,
    ) -> List[AIInvocationLog]:
        """List historical AI invocation telemetry logs."""
        query = select(AIInvocationLog).order_by(desc(AIInvocationLog.created_at))

        if provider:
            query = query.where(AIInvocationLog.provider == provider)
        if task:
            query = query.where(AIInvocationLog.task == task)
        if success is not None:
            query = query.where(AIInvocationLog.success == success)
        if fallback_used is not None:
            query = query.where(AIInvocationLog.fallback_used == fallback_used)

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_daily_spend(self, target_date: Optional[datetime] = None) -> float:
        """Calculate total USD spent on AI invocations for the current UTC day."""
        now = target_date or datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        query = select(func.sum(AIInvocationLog.cost)).where(
            AIInvocationLog.created_at >= start_of_day,
            AIInvocationLog.success == True,
        )
        result = await self.session.execute(query)
        spend = result.scalar()
        return float(spend or 0.0)

    async def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """Compute aggregate AI metrics over a historical time window."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Aggregate totals
        totals_query = select(
            func.count(AIInvocationLog.id).label("total_calls"),
            func.sum(AIInvocationLog.cost).label("total_cost"),
            func.sum(AIInvocationLog.prompt_tokens).label("total_prompt_tokens"),
            func.sum(AIInvocationLog.completion_tokens).label("total_completion_tokens"),
            func.sum(AIInvocationLog.total_tokens).label("total_tokens"),
            func.avg(AIInvocationLog.latency_ms).label("avg_latency_ms"),
        ).where(AIInvocationLog.created_at >= since)

        totals_res = await self.session.execute(totals_query)
        totals_row = totals_res.one()

        total_calls = totals_row.total_calls or 0
        total_cost = float(totals_row.total_cost or 0.0)
        total_prompt_tokens = totals_row.total_prompt_tokens or 0
        total_completion_tokens = totals_row.total_completion_tokens or 0
        total_tokens = totals_row.total_tokens or 0
        avg_latency_ms = float(totals_row.avg_latency_ms or 0.0)

        # Success count
        success_query = select(func.count(AIInvocationLog.id)).where(
            AIInvocationLog.created_at >= since,
            AIInvocationLog.success == True,
        )
        success_res = await self.session.execute(success_query)
        success_count = success_res.scalar() or 0

        # Fallback count
        fallback_query = select(func.count(AIInvocationLog.id)).where(
            AIInvocationLog.created_at >= since,
            AIInvocationLog.fallback_used == True,
        )
        fallback_res = await self.session.execute(fallback_query)
        fallback_count = fallback_res.scalar() or 0

        # Provider breakdown
        prov_query = select(
            AIInvocationLog.provider,
            func.count(AIInvocationLog.id).label("calls"),
            func.sum(AIInvocationLog.cost).label("cost"),
            func.sum(AIInvocationLog.total_tokens).label("tokens"),
        ).where(AIInvocationLog.created_at >= since).group_by(AIInvocationLog.provider)

        prov_res = await self.session.execute(prov_query)
        provider_breakdown = [
            {
                "provider": row.provider,
                "calls": row.calls,
                "cost": float(row.cost or 0.0),
                "tokens": row.tokens or 0,
            }
            for row in prov_res.all()
        ]

        # Task breakdown
        task_query = select(
            AIInvocationLog.task,
            func.count(AIInvocationLog.id).label("calls"),
            func.sum(AIInvocationLog.cost).label("cost"),
        ).where(AIInvocationLog.created_at >= since).group_by(AIInvocationLog.task)

        task_res = await self.session.execute(task_query)
        task_breakdown = [
            {
                "task": row.task,
                "calls": row.calls,
                "cost": float(row.cost or 0.0),
            }
            for row in task_res.all()
        ]

        today_spend = await self.get_daily_spend()

        return {
            "period_days": days,
            "total_calls": total_calls,
            "success_count": success_count,
            "failure_count": total_calls - success_count,
            "success_rate": round((success_count / total_calls * 100) if total_calls > 0 else 100.0, 1),
            "fallback_count": fallback_count,
            "fallback_rate": round((fallback_count / total_calls * 100) if total_calls > 0 else 0.0, 1),
            "total_cost": round(total_cost, 4),
            "daily_spend_today": round(today_spend, 4),
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "avg_latency_ms": round(avg_latency_ms, 1),
            "provider_breakdown": provider_breakdown,
            "task_breakdown": task_breakdown,
        }
