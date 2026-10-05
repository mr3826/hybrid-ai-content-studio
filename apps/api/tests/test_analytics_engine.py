import pytest
from app.engines.analytics.engine import AnalyticsEngine
from app.engines.analytics.analyzer import AnalyticsAnalyzer
from app.engines.core.base import EngineContext


def test_analytics_engine_manifest_and_health():
    engine = AnalyticsEngine()
    assert engine.id == "analytics"
    assert engine.name == "Analytics Engine"
    assert engine.version == "1.0.0"

    health = engine.health()
    assert health.status == "healthy"
    assert health.details["has_rules"] is True
    assert "youtube" in health.details["supported_platforms"]


def test_analytics_analyzer_engagement_calculation():
    analyzer = AnalyticsAnalyzer()
    # 1000 views, 50 likes, 10 comments, 5 shares, 5 saves = 70 engagements = 7.0%
    rate = analyzer.calculate_engagement_rate(views=1000, likes=50, comments=10, shares=5, saves=5)
    assert rate == 7.0

    # 0 views should return 0.0 without division by zero
    assert analyzer.calculate_engagement_rate(0, 0, 0, 0, 0) == 0.0


def test_analytics_analyzer_hook_benchmarks():
    analyzer = AnalyticsAnalyzer()

    # Viral hook (>= 80%)
    viral = analyzer.evaluate_hook(
        content_item_id="item-1",
        content_title="Viral Test",
        hook_text="Stop doing this common mistake!",
        platform="youtube",
        views=10000,
        hook_retention_3s_pct=84.5,
    )
    assert viral.verdict == "VIRAL"

    # Strong hook (70% - 79.9%)
    strong = analyzer.evaluate_hook(
        content_item_id="item-2",
        content_title="Strong Test",
        hook_text="Here is why your code breaks.",
        platform="tiktok",
        views=5000,
        hook_retention_3s_pct=72.0,
    )
    assert strong.verdict == "STRONG"

    # Acceptable hook (55% - 69.9%)
    acceptable = analyzer.evaluate_hook(
        content_item_id="item-3",
        content_title="Acceptable Test",
        hook_text="In this video we explore databases.",
        platform="facebook",
        views=2000,
        hook_retention_3s_pct=58.0,
    )
    assert acceptable.verdict == "ACCEPTABLE"

    # Critical drop (< 55%)
    drop = analyzer.evaluate_hook(
        content_item_id="item-4",
        content_title="Drop Test",
        hook_text="Hey guys welcome back to the channel today...",
        platform="youtube",
        views=1500,
        hook_retention_3s_pct=34.0,
    )
    assert drop.verdict == "CRITICAL_DROP"
    assert "dropoff" in drop.recommendation.lower()


def test_analytics_analyzer_roi_calculation():
    analyzer = AnalyticsAnalyzer()

    # 45 min production at $50/hr = $37.50 + $0.05 AI = $37.55 total cost
    # $150 revenue -> Net $112.45, ROI ~ 3.99x -> HIGH_ROI
    roi = analyzer.calculate_roi(
        content_item_id="item-1",
        content_title="High ROI Item",
        total_views=25000,
        total_revenue_usd=150.0,
        ai_cost_usd=0.05,
        production_minutes=45.0,
    )
    assert roi.status == "HIGH_ROI"
    assert roi.total_cost_usd == 37.55
    assert roi.net_profit_usd == 112.45
    assert roi.roi_multiplier >= 3.0
    assert roi.revenue_per_1k_views_rpm == 6.0

    # Low revenue -> NEGATIVE
    negative_roi = analyzer.calculate_roi(
        content_item_id="item-2",
        content_title="Unprofitable Item",
        total_views=100,
        total_revenue_usd=5.0,
        ai_cost_usd=0.05,
        production_minutes=60.0,
    )
    assert negative_roi.status == "NEGATIVE"
    assert negative_roi.net_profit_usd < 0


def test_analytics_analyzer_platform_aggregation():
    analyzer = AnalyticsAnalyzer()
    snapshots = [
        {"platform": "youtube", "views": 1000, "likes": 50, "comments": 10, "shares": 5, "saves": 5, "revenue_estimated_usd": 25.0, "retention_rate_pct": 65.0},
        {"platform": "youtube", "views": 2000, "likes": 100, "comments": 20, "shares": 10, "saves": 10, "revenue_estimated_usd": 50.0, "retention_rate_pct": 70.0},
        {"platform": "tiktok", "views": 5000, "likes": 300, "comments": 50, "shares": 40, "saves": 30, "revenue_estimated_usd": 15.0, "retention_rate_pct": 55.0},
    ]
    breakdowns = analyzer.aggregate_platforms(snapshots)
    assert len(breakdowns) == 2
    # Sorted by total views
    assert breakdowns[0].platform == "tiktok"
    assert breakdowns[0].total_views == 5000
    assert breakdowns[1].platform == "youtube"
    assert breakdowns[1].total_views == 3000
    assert breakdowns[1].total_revenue == 75.0


def test_analytics_analyzer_csv_parsing():
    analyzer = AnalyticsAnalyzer()
    csv_data = """content_item_id,platform,snapshot_label,views,likes,comments,shares,revenue_estimated_usd,hook_retention_3s_pct
item-101,youtube,24h,1200,60,12,6,15.50,74.5
item-102,tiktok,48h,4500,320,45,30,8.20,82.0
"""
    records = analyzer.parse_csv(csv_data)
    assert len(records) == 2
    assert records[0]["content_item_id"] == "item-101"
    assert records[0]["platform"] == "youtube"
    assert records[0]["views"] == 1200
    assert records[0]["likes"] == 60
    assert records[0]["hook_retention_3s_pct"] == 74.5
    assert records[0]["source"] == "CSV_IMPORT"

    assert records[1]["content_item_id"] == "item-102"
    assert records[1]["platform"] == "tiktok"
    assert records[1]["hook_retention_3s_pct"] == 82.0


@pytest.mark.asyncio
async def test_analytics_engine_run_and_explain():
    engine = AnalyticsEngine()
    ctx = EngineContext(
        run_id="run-test-123",
        parameters={
            "snapshots": [
                {
                    "content_item_id": "item-abc",
                    "content_title": "AI Workflow",
                    "hook_text": "Did you know this secret?",
                    "platform": "youtube",
                    "views": 3500,
                    "likes": 200,
                    "comments": 30,
                    "shares": 15,
                    "saves": 10,
                    "revenue_estimated_usd": 40.0,
                    "hook_retention_3s_pct": 76.0,
                }
            ]
        }
    )
    result = await engine.run(ctx)
    assert result.success is True
    assert result.outputs[0]["total_snapshots_analyzed"] == 1
    assert len(result.outputs[0]["hook_insights"]) == 1
    assert result.outputs[0]["hook_insights"][0]["verdict"] == "STRONG"

    explanation = engine.explain("run-123")
    assert explanation.result_id == "run-123"
    assert len(explanation.factors) >= 4
