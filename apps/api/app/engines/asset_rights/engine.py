import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.asset_rights.contracts import (
    AssetInput,
    AssetRightsVerdict,
    AssetRightsBatchVerdict,
)
from app.models.asset_rights import AssetRightsStatus, CommercialUseStatus


class AssetRightsEngine(BaseEngine):
    """Asset Rights Engine.

    Tracks copyright documentation, commercial use permissions, and attribution requirements
    for visual, audio, code, and font assets.
    Prevents unlicensed media from silently contaminating export packages.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)
        self._execution_history: Dict[str, Any] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("AssetRightsEngine rules cannot be empty.")
        if "safe_license_types" not in self.rules:
            raise ValueError("safe_license_types must be defined in asset rights rules.")

    def health(self) -> EngineHealth:
        return EngineHealth(
            status="healthy",
            message="Asset Rights Engine operational with license verification and provenance checks.",
            details={
                "safe_licenses_count": len(self.rules.get("safe_license_types", [])),
                "prohibited_licenses_count": len(self.rules.get("prohibited_license_types", [])),
                "strict_commercial": self.rules.get("strict_commercial_enforcement", True),
            },
        )

    def evaluate_asset(self, asset: AssetInput) -> AssetRightsVerdict:
        """Determines the legal risk and attribution status of a media asset."""
        safe_licenses = [s.lower() for s in self.rules.get("safe_license_types", [])]
        prohibited_licenses = [p.lower() for p in self.rules.get("prohibited_license_types", [])]
        attribution_licenses = [a.lower() for a in self.rules.get("attribution_license_types", [])]

        lic = (asset.license_type or "Unknown").strip().lower()
        warnings: List[str] = []
        is_safe = False
        commercial_allowed = False
        status = AssetRightsStatus.UNKNOWN

        # 1. Prohibited licenses (Non-commercial, strictly all rights reserved)
        is_prohibited = (
            any(p in lic for p in prohibited_licenses)
            or "non-commercial" in lic
            or "-nc" in lic
            or asset.commercial_use_status == CommercialUseStatus.PROHIBITED
        )

        if is_prohibited:
            status = AssetRightsStatus.DO_NOT_USE
            is_safe = False
            commercial_allowed = False
            warnings.append(
                f"License '{asset.license_type}' or commercial status prohibits commercial use. Do not use in public channel uploads."
            )
            explanation = "Asset is classified as DO_NOT_USE due to non-commercial restrictions or lack of distribution rights."
            return AssetRightsVerdict(
                title=asset.title,
                status=status,
                is_safe=is_safe,
                commercial_use_allowed=commercial_allowed,
                attribution_required=bool(asset.attribution_required),
                attribution_text=asset.attribution_text,
                warnings=warnings,
                explanation=explanation,
            )

        # 2. Attribution-mandated licenses (e.g. CC-BY, CC-BY-SA)
        if any(a in lic for a in attribution_licenses) or asset.attribution_required:
            status = AssetRightsStatus.REQUIRES_ATTRIBUTION
            is_safe = True
            commercial_allowed = True
            if not asset.attribution_text:
                warnings.append(
                    "Attribution is required for this license, but no attribution text/credit string has been declared."
                )
            explanation = (
                f"Asset is licensed under '{asset.license_type}' which requires explicit creator credit in video captions or description."
            )
            return AssetRightsVerdict(
                title=asset.title,
                status=status,
                is_safe=is_safe,
                commercial_use_allowed=commercial_allowed,
                attribution_required=True,
                attribution_text=asset.attribution_text,
                warnings=warnings,
                explanation=explanation,
            )

        # 3. Known Safe Licenses (CC0, MIT, Apache-2.0, Royalty-Free Commercial, Self-Created)
        if any(s in lic for s in safe_licenses) or asset.commercial_use_status == CommercialUseStatus.ALLOWED:
            status = AssetRightsStatus.VERIFIED
            is_safe = True
            commercial_allowed = True
            explanation = (
                f"Asset has verified commercial rights under '{asset.license_type}' provenance from '{asset.source}'."
            )
            return AssetRightsVerdict(
                title=asset.title,
                status=status,
                is_safe=is_safe,
                commercial_use_allowed=commercial_allowed,
                attribution_required=False,
                attribution_text=None,
                warnings=warnings,
                explanation=explanation,
            )

        # 4. Unknown / Undocumented
        status = AssetRightsStatus.UNKNOWN
        is_safe = False
        commercial_allowed = False
        warnings.append(
            f"Asset license '{asset.license_type}' is unrecognized or undocumented. Verification recommended before media finalization."
        )
        explanation = "Asset license and commercial terms could not be automatically verified. Flagged as UNKNOWN."

        return AssetRightsVerdict(
            title=asset.title,
            status=status,
            is_safe=is_safe,
            commercial_use_allowed=commercial_allowed,
            attribution_required=bool(asset.attribution_required),
            attribution_text=asset.attribution_text,
            warnings=warnings,
            explanation=explanation,
        )

    def evaluate_batch(self, assets: List[AssetInput]) -> AssetRightsBatchVerdict:
        """Evaluates rights across an array of assets (e.g. for a scene storyboard)."""
        verdicts = [self.evaluate_asset(a) for a in assets]
        safe_count = sum(1 for v in verdicts if v.is_safe)
        warning_count = sum(1 for v in verdicts if v.status == AssetRightsStatus.UNKNOWN or v.warnings)
        blocked_count = sum(1 for v in verdicts if v.status == AssetRightsStatus.DO_NOT_USE)

        summary = (
            f"Evaluated {len(assets)} asset(s): {safe_count} safe, "
            f"{warning_count} with warnings/unknown, {blocked_count} blocked (DO_NOT_USE)."
        )

        return AssetRightsBatchVerdict(
            total_assets=len(assets),
            safe_count=safe_count,
            warning_count=warning_count,
            blocked_count=blocked_count,
            all_safe=(blocked_count == 0 and warning_count == 0),
            verdicts=verdicts,
            summary=summary,
        )

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        payload = context.parameters or {}

        raw_assets = payload.get("assets", [])
        if not raw_assets and "input" in payload:
            raw_assets = [payload["input"]]
        elif not raw_assets and "items" in payload:
            raw_assets = payload["items"]

        if not raw_assets:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            end_time = datetime.now(timezone.utc)
            return EngineResult(
                engine_id=self.id,
                engine_version=self.version,
                run_id=context.run_id,
                success=True,
                started_at=start_time,
                ended_at=end_time,
                duration_ms=duration_ms,
                input_count=0,
                output_count=0,
                rejected_count=0,
                summary="No assets provided to evaluate.",
                outputs=[],
            )

        asset_inputs = [AssetInput(**a) if isinstance(a, dict) else a for a in raw_assets]
        batch_result = self.evaluate_batch(asset_inputs)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        end_time = datetime.now(timezone.utc)

        self._execution_history[context.run_id] = batch_result

        explanations = [
            {
                "title": v.title,
                "status": v.status,
                "is_safe": v.is_safe,
                "explanation": v.explanation,
                "warnings": v.warnings,
            }
            for v in batch_result.verdicts
        ]

        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            success=(batch_result.blocked_count == 0),
            started_at=start_time,
            ended_at=end_time,
            duration_ms=duration_ms,
            input_count=batch_result.total_assets,
            output_count=batch_result.safe_count,
            rejected_count=batch_result.blocked_count,
            summary=batch_result.summary,
            outputs=[v.model_dump() for v in batch_result.verdicts],
            explanations=explanations,
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        context.dry_run = True
        result = await self.run(context)
        result.summary = f"[DRY RUN] {result.summary}"
        return result

    def explain(self, result_id: str) -> EngineExplanation:
        history = self._execution_history.get(result_id)
        factors = [
            {"factor": "strict_commercial_enforcement", "value": self.rules.get("strict_commercial_enforcement", True)},
            {"factor": "safe_licenses", "value": self.rules.get("safe_license_types", [])},
            {"factor": "prohibited_licenses", "value": self.rules.get("prohibited_license_types", [])},
        ]
        if history:
            summary = f"Result {result_id}: {history.summary}"
        else:
            summary = f"Asset Rights evaluation explanation for {result_id}."
        return EngineExplanation(
            result_id=result_id,
            summary=summary,
            factors=factors,
        )
