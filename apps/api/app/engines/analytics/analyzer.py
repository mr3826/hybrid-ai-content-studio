from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import csv
import io

from app.engines.analytics.contracts import (
    ContentROIAnalysis,
    HookPerformanceInsight,
    PlatformBreakdown,
    SnapshotResponse,
)


class AnalyticsAnalyzer:
    """Core calculation logic for creator performance analytics, retention benchmarks,
    hook power evaluations, and creator economics.
    """

    def __init__(self, rules: Optional[Dict[str, Any]] = None):
        self.rules = rules or {}
        self.engagement_benchmarks = self.rules.get("engagement_benchmarks", {
            "poor": 1.5,
            "acceptable": 3.0,
            "good": 5.0,
            "exceptional": 8.0,
        })
        self.hook_benchmarks = self.rules.get("hook_retention_benchmarks", {
            "critical_drop": 40.0,
            "acceptable": 55.0,
            "strong": 70.0,
            "viral": 80.0,
        })
        self.cost_defaults = self.rules.get("cost_defaults", {
            "creator_hourly_rate_usd": 50.0,
            "default_production_minutes": 45.0,
        })

    def calculate_engagement_rate(self, views: int, likes: int, comments: int, shares: int, saves: int) -> float:
        """Calculates total engagement percentage over view count."""
        if views <= 0:
            return 0.0
        total_engagements = likes + comments + shares + saves
        return round((total_engagements / views) * 100.0, 2)

    def evaluate_hook(
        self,
        content_item_id: str,
        content_title: str,
        hook_text: str,
        platform: str,
        views: int,
        hook_retention_3s_pct: float,
        hook_retention_30s_pct: Optional[float] = None,
    ) -> HookPerformanceInsight:
        """Evaluates 3-second hook retention against creator benchmarks."""
        viral_thresh = self.hook_benchmarks.get("viral", 80.0)
        strong_thresh = self.hook_benchmarks.get("strong", 70.0)
        acceptable_thresh = self.hook_benchmarks.get("acceptable", 55.0)

        if hook_retention_3s_pct >= viral_thresh:
            verdict = "VIRAL"
            recommendation = (
                "Outstanding hook velocity. First 3 seconds created immediate intrigue and high visual hold. "
                "Archive this hook formula into brand exemplars."
            )
        elif hook_retention_3s_pct >= strong_thresh:
            verdict = "STRONG"
            recommendation = (
                "Strong retention past the initial dropoff zone. Clean premise delivery and clear value promise."
            )
        elif hook_retention_3s_pct >= acceptable_thresh:
            verdict = "ACCEPTABLE"
            recommendation = (
                "Satisfactory hold rate. Consider tightening the initial 2-second visual cut and trimming preamble text."
            )
        else:
            verdict = "CRITICAL_DROP"
            recommendation = (
                "Severe dropoff in first 3 seconds. The premise was either too slow or lacked emotional/curiosity trigger. "
                "Test high-contrast visual openers or direct question hooks."
            )

        return HookPerformanceInsight(
            content_item_id=content_item_id,
            content_title=content_title,
            hook_text=hook_text or "(No script hook text logged)",
            platform=platform,
            views=views,
            hook_retention_3s_pct=round(hook_retention_3s_pct, 1),
            hook_retention_30s_pct=round(hook_retention_30s_pct, 1) if hook_retention_30s_pct is not None else None,
            verdict=verdict,
            recommendation=recommendation,
        )

    def calculate_roi(
        self,
        content_item_id: str,
        content_title: str,
        total_views: int,
        total_revenue_usd: float,
        ai_cost_usd: float = 0.05,
        production_minutes: Optional[float] = None,
    ) -> ContentROIAnalysis:
        """Calculates creator content return on investment considering AI and labor costs."""
        minutes = production_minutes if production_minutes is not None else self.cost_defaults.get("default_production_minutes", 45.0)
        rate = self.cost_defaults.get("creator_hourly_rate_usd", 50.0)
        creator_cost = round((minutes / 60.0) * rate, 2)
        total_cost = round(ai_cost_usd + creator_cost, 2)

        net_profit = round(total_revenue_usd - total_cost, 2)
        roi_multiplier = round(total_revenue_usd / max(total_cost, 0.01), 2)
        rpm = round((total_revenue_usd / max(total_views, 1)) * 1000.0, 2)

        if roi_multiplier >= 3.0:
            status = "HIGH_ROI"
        elif roi_multiplier >= 1.2:
            status = "PROFITABLE"
        elif roi_multiplier >= 0.9:
            status = "BREAK_EVEN"
        else:
            status = "NEGATIVE"

        return ContentROIAnalysis(
            content_item_id=content_item_id,
            content_title=content_title,
            ai_cost_usd=round(ai_cost_usd, 3),
            creator_time_minutes=round(minutes, 1),
            creator_cost_usd=creator_cost,
            total_cost_usd=total_cost,
            total_revenue_usd=round(total_revenue_usd, 2),
            total_views=total_views,
            net_profit_usd=net_profit,
            roi_multiplier=roi_multiplier,
            revenue_per_1k_views_rpm=rpm,
            status=status,
        )

    def aggregate_platforms(self, snapshots: List[Dict[str, Any]]) -> List[PlatformBreakdown]:
        """Groups and aggregates metrics across publication platforms."""
        platforms_map: Dict[str, Dict[str, Any]] = {}

        for s in snapshots:
            p = s.get("platform", "other").lower()
            if p not in platforms_map:
                platforms_map[p] = {
                    "platform": p,
                    "total_posts": 0,
                    "total_views": 0,
                    "total_likes": 0,
                    "total_comments": 0,
                    "total_shares": 0,
                    "total_revenue": 0.0,
                    "retention_sum": 0.0,
                    "retention_count": 0,
                    "engagement_sum": 0.0,
                }
            entry = platforms_map[p]
            entry["total_posts"] += 1
            views = s.get("views", 0)
            entry["total_views"] += views
            likes = s.get("likes", 0)
            comments = s.get("comments", 0)
            shares = s.get("shares", 0)
            saves = s.get("saves", 0)
            entry["total_likes"] += likes
            entry["total_comments"] += comments
            entry["total_shares"] += shares
            entry["total_revenue"] += s.get("revenue_estimated_usd", 0.0)

            ret = s.get("retention_rate_pct", 0.0)
            if ret > 0:
                entry["retention_sum"] += ret
                entry["retention_count"] += 1

            eng = self.calculate_engagement_rate(views, likes, comments, shares, saves)
            entry["engagement_sum"] += eng

        breakdowns: List[PlatformBreakdown] = []
        for p, data in platforms_map.items():
            posts = max(data["total_posts"], 1)
            avg_eng = round(data["engagement_sum"] / posts, 2)
            avg_ret = round(data["retention_sum"] / max(data["retention_count"], 1), 1) if data["retention_count"] > 0 else 0.0

            breakdowns.append(PlatformBreakdown(
                platform=p,
                total_posts=data["total_posts"],
                total_views=data["total_views"],
                total_likes=data["total_likes"],
                total_comments=data["total_comments"],
                total_shares=data["total_shares"],
                total_revenue=round(data["total_revenue"], 2),
                avg_engagement_rate=avg_eng,
                avg_retention_rate=avg_ret,
            ))

        return sorted(breakdowns, key=lambda x: x.total_views, reverse=True)

    def parse_csv(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parses CSV text into normalized publication metric dictionaries."""
        reader = csv.DictReader(io.StringIO(csv_content))
        normalized_records: List[Dict[str, Any]] = []

        for row in reader:
            # Normalize headers
            cleaned_row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items() if k}

            content_item_id = cleaned_row.get("content_item_id") or cleaned_row.get("item_id") or cleaned_row.get("content_id")
            if not content_item_id:
                continue

            platform = cleaned_row.get("platform", "youtube").lower()
            label = cleaned_row.get("snapshot_label") or cleaned_row.get("label", "24h")

            try:
                views = int(cleaned_row.get("views", 0) or 0)
            except ValueError:
                views = 0

            try:
                impressions = int(cleaned_row.get("impressions", 0) or 0)
            except ValueError:
                impressions = 0

            try:
                likes = int(cleaned_row.get("likes", 0) or 0)
            except ValueError:
                likes = 0

            try:
                comments = int(cleaned_row.get("comments", 0) or 0)
            except ValueError:
                comments = 0

            try:
                shares = int(cleaned_row.get("shares", 0) or 0)
            except ValueError:
                shares = 0

            try:
                saves = int(cleaned_row.get("saves", 0) or 0)
            except ValueError:
                saves = 0

            try:
                clicks = int(cleaned_row.get("clicks", 0) or 0)
            except ValueError:
                clicks = 0

            try:
                subs = int(cleaned_row.get("subscribers_gained", 0) or cleaned_row.get("subs", 0) or 0)
            except ValueError:
                subs = 0

            try:
                watch_time = float(cleaned_row.get("watch_time_seconds", 0.0) or 0.0)
            except ValueError:
                watch_time = 0.0

            try:
                avd = float(cleaned_row.get("average_view_duration_seconds", 0.0) or cleaned_row.get("avd", 0.0) or 0.0)
            except ValueError:
                avd = 0.0

            try:
                ret = float(cleaned_row.get("retention_rate_pct", 0.0) or cleaned_row.get("retention", 0.0) or 0.0)
            except ValueError:
                ret = 0.0

            hook_3s = None
            if "hook_retention_3s_pct" in cleaned_row and cleaned_row["hook_retention_3s_pct"]:
                try:
                    hook_3s = float(cleaned_row["hook_retention_3s_pct"])
                except ValueError:
                    hook_3s = None

            hook_30s = None
            if "hook_retention_30s_pct" in cleaned_row and cleaned_row["hook_retention_30s_pct"]:
                try:
                    hook_30s = float(cleaned_row["hook_retention_30s_pct"])
                except ValueError:
                    hook_30s = None

            try:
                revenue = float(cleaned_row.get("revenue_estimated_usd", 0.0) or cleaned_row.get("revenue", 0.0) or 0.0)
            except ValueError:
                revenue = 0.0

            notes = cleaned_row.get("notes")

            normalized_records.append({
                "content_item_id": content_item_id,
                "platform": platform,
                "snapshot_label": label,
                "views": views,
                "impressions": impressions,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "saves": saves,
                "clicks": clicks,
                "subscribers_gained": subs,
                "watch_time_seconds": watch_time,
                "average_view_duration_seconds": avd,
                "retention_rate_pct": ret,
                "hook_retention_3s_pct": hook_3s,
                "hook_retention_30s_pct": hook_30s,
                "revenue_estimated_usd": revenue,
                "notes": notes,
                "source": "CSV_IMPORT",
            })

        return normalized_records
