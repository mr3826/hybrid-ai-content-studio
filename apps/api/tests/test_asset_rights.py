import pytest
from app.engines.asset_rights.contracts import AssetInput
from app.engines.asset_rights.engine import AssetRightsEngine
from app.engines.core.base import EngineContext
from app.models.asset_rights import AssetRightsStatus, CommercialUseStatus


def test_asset_rights_engine_initialization_and_health():
    engine = AssetRightsEngine()
    assert engine.id == "asset_rights"
    assert engine.name == "Asset Rights Engine"
    health = engine.health()
    assert health.status == "healthy"
    assert health.details["safe_licenses_count"] > 0
    assert health.details["prohibited_licenses_count"] > 0


def test_asset_rights_verified_safe_licenses():
    engine = AssetRightsEngine()

    safe_cases = [
        ("Channel Logo", "Self-Created", "image"),
        ("JetBrains Mono", "OFL-1.1", "font"),
        ("Public Domain Icon", "CC0", "icon"),
        ("Open Source Helper", "MIT", "code"),
        ("Commercial Stock Footage", "Royalty-Free Commercial", "video"),
    ]

    for title, license_type, asset_type in safe_cases:
        asset = AssetInput(
            title=title,
            asset_type=asset_type,
            source="Test Provider",
            license_type=license_type,
        )
        verdict = engine.evaluate_asset(asset)
        assert verdict.status == AssetRightsStatus.VERIFIED
        assert verdict.is_safe is True
        assert verdict.commercial_use_allowed is True
        assert verdict.attribution_required is False


def test_asset_rights_attribution_mandated_licenses():
    engine = AssetRightsEngine()

    # Case 1: CC-BY with attribution text provided
    asset1 = AssetInput(
        title="Background Music",
        asset_type="bgm",
        source="Free Music Archive",
        license_type="CC-BY-4.0",
        attribution_required=True,
        attribution_text="Music by Kevin MacLeod (CC-BY 4.0)",
    )
    verdict1 = engine.evaluate_asset(asset1)
    assert verdict1.status == AssetRightsStatus.REQUIRES_ATTRIBUTION
    assert verdict1.is_safe is True
    assert verdict1.commercial_use_allowed is True
    assert verdict1.attribution_required is True
    assert len(verdict1.warnings) == 0

    # Case 2: CC-BY without attribution text provided -> warning
    asset2 = AssetInput(
        title="Background Music Uncredited",
        asset_type="bgm",
        source="Free Music Archive",
        license_type="CC-BY-4.0",
    )
    verdict2 = engine.evaluate_asset(asset2)
    assert verdict2.status == AssetRightsStatus.REQUIRES_ATTRIBUTION
    assert verdict2.is_safe is True
    assert verdict2.attribution_required is True
    assert any("no attribution text" in w.lower() for w in verdict2.warnings)


def test_asset_rights_prohibited_non_commercial_licenses():
    engine = AssetRightsEngine()

    prohibited_cases = [
        ("NC Sound Effect", "CC-BY-NC-4.0"),
        ("Editorial Photo", "Editorial Use Only"),
        ("Protected Media", "All Rights Reserved"),
        ("Non Commercial Asset", "non-commercial only"),
    ]

    for title, license_type in prohibited_cases:
        asset = AssetInput(
            title=title,
            asset_type="audio",
            source="Web Source",
            license_type=license_type,
        )
        verdict = engine.evaluate_asset(asset)
        assert verdict.status == AssetRightsStatus.DO_NOT_USE
        assert verdict.is_safe is False
        assert verdict.commercial_use_allowed is False
        assert len(verdict.warnings) > 0


def test_asset_rights_unknown_licenses():
    engine = AssetRightsEngine()

    asset = AssetInput(
        title="Mystery Screenshot",
        asset_type="image",
        source="Random Discord Server",
        license_type="Unknown",
    )
    verdict = engine.evaluate_asset(asset)
    assert verdict.status == AssetRightsStatus.UNKNOWN
    assert verdict.is_safe is False
    assert any("unrecognized or undocumented" in w.lower() for w in verdict.warnings)


def test_asset_rights_evaluate_batch():
    engine = AssetRightsEngine()

    batch = [
        AssetInput(title="Verified Asset", asset_type="image", source="Internal", license_type="Self-Created"),
        AssetInput(title="Attribution Asset", asset_type="bgm", source="FMA", license_type="CC-BY-4.0", attribution_text="Credit"),
        AssetInput(title="Unknown Asset", asset_type="video", source="Reddit", license_type="Unknown"),
        AssetInput(title="Blocked Asset", asset_type="audio", source="Pirate site", license_type="CC-BY-NC"),
    ]

    batch_verdict = engine.evaluate_batch(batch)
    assert batch_verdict.total_assets == 4
    assert batch_verdict.safe_count == 2
    assert batch_verdict.warning_count >= 1
    assert batch_verdict.blocked_count == 1
    assert batch_verdict.all_safe is False


@pytest.mark.asyncio
async def test_asset_rights_engine_run_and_explain():
    engine = AssetRightsEngine()
    context = EngineContext(
        run_id="run-rights-1",
        parameters={
            "assets": [
                {"title": "Safe Asset", "asset_type": "font", "source": "Google Fonts", "license_type": "OFL-1.1"},
                {"title": "Prohibited Asset", "asset_type": "image", "source": "Flickr", "license_type": "CC-BY-NC"},
            ]
        },
    )

    result = await engine.run(context)
    assert result.engine_id == "asset_rights"
    assert result.input_count == 2
    assert result.output_count == 1  # 1 safe asset
    assert result.rejected_count == 1  # 1 blocked asset
    assert result.success is False  # Contains blocked asset

    explanation = engine.explain("run-rights-1")
    assert explanation.result_id == "run-rights-1"
    assert "safe" in explanation.summary.lower() or "blocked" in explanation.summary.lower()
