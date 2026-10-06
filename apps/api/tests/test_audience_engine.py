import pytest
from app.engines.audience.engine import AudienceEngine
from app.engines.audience.analyzer import AudienceAnalyzer
from app.engines.audience.contracts import UTMBuilderRequest
from app.engines.core.base import EngineContext


def test_audience_engine_init_and_health():
    """Verify AudienceEngine correctly initializes rules and returns healthy state."""
    engine = AudienceEngine()
    assert engine.id == "audience"
    assert engine.version == "1.0.0"
    health = engine.health()
    assert health.status == "healthy"
    assert health.details["target_conversion_rate_pct"] == 3.0
    assert health.details["default_lead_value_usd"] == 15.0


def test_audience_analyzer_utm_building():
    """Verify deterministic UTM parameter construction and markdown formatting."""
    analyzer = AudienceAnalyzer(rules={
        "utm_defaults": {
            "medium_mapping": {
                "youtube": "video_description",
                "tiktok": "bio_link",
            },
            "campaign_prefix": "sc_",
        }
    })

    req = UTMBuilderRequest(
        base_url="https://studio.example.com/starter-kit?existing=param",
        platform="youtube",
        lead_magnet_slug="starter-kit",
        content_slug="video-ep-12",
        campaign_name="launch_2026",
    )

    res = analyzer.build_utm_tracking_url(
        req,
        magnet_title="Complete AI Starter Kit",
        cta_copy="Download the blueprint free at {url}",
    )

    assert "utm_source=youtube" in res.tracking_url
    assert "utm_medium=video_description" in res.tracking_url
    assert "utm_campaign=sc_launch_2026" in res.tracking_url
    assert "utm_content=video-ep-12" in res.tracking_url
    assert "existing=param" in res.tracking_url
    assert res.formatted_markdown_link == f"[Complete AI Starter Kit]({res.tracking_url})"
    assert res.copy_paste_cta == f"Download the blueprint free at {res.tracking_url}"


def test_audience_analyzer_metrics_calculation():
    """Verify conversion rate math and subscriber economics calculations."""
    analyzer = AudienceAnalyzer(rules={
        "target_conversion_rate_pct": 3.0,
        "critical_conversion_rate_pct": 1.0,
        "excellent_conversion_rate_pct": 5.0,
    })

    metrics = analyzer.calculate_conversion_metrics(
        clicks=200,
        signups=10,
        customers=2,
        revenue_usd=98.0,
        estimated_value_usd=25.0,
    )

    assert metrics["conversion_rate_pct"] == 5.0
    assert metrics["customer_conversion_rate_pct"] == 20.0
    assert metrics["estimated_asset_value_usd"] == 250.0  # 10 * 25.0
    assert metrics["performance_tier"] == "EXCELLENT"

    zero_traffic = analyzer.calculate_conversion_metrics(clicks=0, signups=0)
    assert zero_traffic["performance_tier"] == "NO_TRAFFIC"


@pytest.mark.asyncio
async def test_audience_engine_run_and_explain():
    """Verify execution of audience engine run, dry_run and explain methods."""
    engine = AudienceEngine()

    magnets = [
        {
            "id": "mag-1",
            "title": "FastAPI Checklist",
            "slug": "fastapi-checklist",
            "magnet_type": "checklist",
            "status": "ACTIVE",
            "estimated_value_usd": 15.0,
        }
    ]
    conversions = [
        {
            "id": "conv-1",
            "lead_magnet_id": "mag-1",
            "platform": "youtube",
            "clicks": 100,
            "signups": 8,
            "customers": 1,
            "revenue_usd": 49.0,
        }
    ]

    ctx = EngineContext(
        run_id="run-aud-1",
        parameters={
            "magnets": magnets,
            "conversions": conversions,
        },
    )

    result = await engine.run(ctx)
    assert result.success is True
    assert result.engine_id == "audience"
    assert result.output_count == 1
    summary = result.outputs[0]
    assert summary["total_clicks"] == 100
    assert summary["total_signups"] == 8
    assert summary["overall_conversion_rate_pct"] == 8.0
    assert summary["estimated_total_list_value_usd"] == 120.0  # 8 * 15.0

    dry_res = await engine.dry_run(ctx)
    assert "[Dry-Run]" in dry_res.summary

    exp = engine.explain("run-aud-1")
    assert exp.result_id == "run-aud-1"
    assert len(exp.factors) == 3
