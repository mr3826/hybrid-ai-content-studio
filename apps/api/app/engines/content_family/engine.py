from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineManifest,
    EngineResult,
)
from app.engines.content_family.contracts import (
    ChildItemProposal,
    EconomicsSummary,
    SuggestChildrenOutput,
    ValidationResult,
)


class ContentFamilyEngine(BaseEngine):
    """Content Family Engine.
    
    Replaces 'Project = one piece of content' with:
    'Content Family = one research/evidence/originality investment'
    which generates multiple tailored child items from the same underlying empirical investment.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("ContentFamilyEngine rules cannot be empty.")
        if "supported_formats" not in self.rules:
            raise ValueError("supported_formats must be defined in rules.yaml")

    def health(self) -> EngineHealth:
        has_manifest = self.manifest is not None
        has_rules = bool(self.rules)
        status = "healthy" if (has_manifest and has_rules) else "degraded"
        return EngineHealth(
            status=status,
            message="Content Family Engine operational with child suggestion, evidence inheritance, and economics tracking.",
            details={
                "has_manifest": has_manifest,
                "has_rules": has_rules,
                "supported_formats": len(self.rules.get("supported_formats", [])),
                "supported_platforms": len(self.rules.get("supported_platforms", [])),
            },
        )

    def suggest_children(
        self,
        family_title: str,
        topic: str,
        originality_type: str,
        what_are_we_adding: str,
        claims: Optional[List[Dict[str, Any]]] = None,
        brand_name: str = "Local AI Studio",
        content_pillar: str = "Core",
        recent_items: Optional[List[Dict[str, Any]]] = None,
    ) -> SuggestChildrenOutput:
        """Propose distinct, non-cloned child content items inheriting family evidence & originality."""
        claims = claims or []
        claim_summaries = [c.get("text", "") for c in claims[:4]]

        # Determine evidence focuses
        perf_claim = claim_summaries[0] if len(claim_summaries) > 0 else "Primary empirical performance"
        sec_claim = claim_summaries[1] if len(claim_summaries) > 1 else "Hardware cost & latency tradeoff"
        fail_claim = claim_summaries[2] if len(claim_summaries) > 2 else "Edge-case crash or VRAM limit"

        proposals = [
            # 1. YouTube Long
            ChildItemProposal(
                format="youtube_long",
                platform_target="youtube",
                working_title=f"{family_title}: Full Deep-Dive & Hardware Test",
                angle=f"Comprehensive end-to-end breakdown testing '{topic}' with verifiable local metrics and reproducible terminal setups.",
                hook_type="curiosity_gap",
                evidence_focus=[perf_claim, sec_claim, fail_claim],
                original_value_connection=f"Delivers the complete empirical test ({what_are_we_adding}) with all raw metrics and side-by-side comparison.",
                viewer_value="Viewers understand exactly how the tool performs on real hardware before installing or purchasing.",
            ),
            # 2. Short 1: Speed / Accuracy Winner
            ChildItemProposal(
                format="short_vertical",
                platform_target="youtube",
                working_title=f"{topic} Speed Test: The Winner",
                angle=f"Focused 45-second test spotlighting the single most impactful metric ({perf_claim}).",
                hook_type="bold_claim",
                evidence_focus=[perf_claim],
                original_value_connection=f"Visualizes the top-line measurement from our {originality_type}.",
                viewer_value="Immediate answer to which tool wins the headline performance race.",
            ),
            # 3. Short 2: Failure Analysis / Bottleneck
            ChildItemProposal(
                format="short_vertical",
                platform_target="instagram",
                working_title=f"Where {topic} Completely Breaks",
                angle=f"Revealing the documented bottleneck ({fail_claim}) and how to prevent local GPU OOM crashes.",
                hook_type="problem_agitation",
                evidence_focus=[fail_claim],
                original_value_connection=f"Exposes the edge cases and failure modes identified during testing.",
                viewer_value="Saves viewers hours of troubleshooting by exposing the unadvertised limitation.",
            ),
            # 4. Social Post / Cross-Platform Companion
            ChildItemProposal(
                format="social_post",
                platform_target="facebook",
                working_title=f"Benchmark Cheat-Sheet: {topic}",
                angle=f"Key quantitative takeaways comparing speed, cost ({sec_claim}), and practical tips.",
                hook_type="surprising_stat",
                evidence_focus=[sec_claim],
                original_value_connection=f"Summarizes the empirical findings in an easily scannable table/bullet list.",
                viewer_value="Quick-reference decision guide that can be saved and referenced during deployment.",
            ),
            # 5. Technical Newsletter / Article
            ChildItemProposal(
                format="newsletter",
                platform_target="cross_platform",
                working_title=f"Inside the Lab: How We Tested {topic}",
                angle="Behind-the-scenes engineering log with terminal commands, configuration files, and lessons learned.",
                hook_type="story_open",
                evidence_focus=[perf_claim, sec_claim],
                original_value_connection=f"Shares reproducible reproduction steps for the {originality_type}.",
                viewer_value="Step-by-step instructions to replicate our local benchmark setup at home.",
            ),
        ]

        # Prevent repetition if recent items are supplied
        if recent_items:
            existing_hooks = {item.get("hook_type") for item in recent_items}
            for p in proposals:
                if p.hook_type in existing_hooks and p.format == "short_vertical":
                    p.hook_type = "direct_value"

        return SuggestChildrenOutput(
            family_title=family_title,
            proposals=proposals,
            brand_applied=brand_name,
            pillar_applied=content_pillar,
        )

    def validate_family(
        self,
        title: str,
        topic_id: Optional[str] = None,
        research_packet_id: Optional[str] = None,
        originality_plan_id: Optional[str] = None,
        claims_count: int = 0,
    ) -> ValidationResult:
        """Validate that a Content Family is linked to evidence and originality."""
        errors: List[str] = []
        warnings: List[str] = []

        if not title or len(title.strip()) < 5:
            errors.append("Family title must be at least 5 characters long.")

        if not topic_id:
            warnings.append("No Opportunity topic linked to this Content Family.")

        if not research_packet_id:
            warnings.append("No Research Packet linked. Families should link verified research.")

        if not originality_plan_id:
            warnings.append("No Originality Plan linked. Content Family should define 'What are WE adding?'")

        if claims_count == 0:
            warnings.append("Parent family has 0 claims in Evidence Engine provenance graph.")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_child(
        self,
        child_format: str,
        platform_target: str,
        working_title: str,
        angle: str,
        hook_type: str,
        original_value_connection: str,
        claims_count: int = 0,
    ) -> ValidationResult:
        """Validate child item integrity, format compatibility, and originality inheritance."""
        errors: List[str] = []
        warnings: List[str] = []

        valid_formats = [f["id"] for f in self.rules.get("supported_formats", [])]
        if valid_formats and child_format not in valid_formats:
            errors.append(f"Format '{child_format}' is not one of supported formats: {valid_formats}")

        valid_platforms = self.rules.get("supported_platforms", [])
        if valid_platforms and platform_target not in valid_platforms:
            errors.append(f"Platform '{platform_target}' is not supported.")

        if not working_title or len(working_title.strip()) < 3:
            errors.append("Child working title is too brief.")

        min_angle_len = self.rules.get("originality_inheritance", {}).get("min_angle_length_chars", 15)
        if not angle or len(angle.strip()) < min_angle_len:
            errors.append(f"Child angle must be at least {min_angle_len} characters to avoid generic summary.")

        if not original_value_connection or len(original_value_connection.strip()) < 5:
            errors.append("Child must specify an explicit 'original_value_connection' to the parent family.")

        if claims_count == 0:
            warnings.append("Child item has 0 selected evidence claims. Factual grounding is recommended.")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def calculate_economics(
        self,
        shared_cost: float,
        shared_time: int,
        shared_compute: float,
        child_items: List[Dict[str, Any]],
    ) -> EconomicsSummary:
        """Calculate shared vs incremental costs and cost-per-child metrics."""
        total_incremental = sum(item.get("incremental_cost", 0.0) for item in child_items)
        total_child_time = sum(item.get("manual_time_minutes", 0) for item in child_items)
        total_child_compute = sum(item.get("local_compute_seconds", 0.0) for item in child_items)

        total_cost = shared_cost + total_incremental
        total_time = shared_time + total_child_time
        total_compute = shared_compute + total_child_compute

        item_count = len(child_items)
        cost_per_child = (total_cost / item_count) if item_count > 0 else total_cost

        return EconomicsSummary(
            shared_family_cost=round(shared_cost, 4),
            shared_manual_time_minutes=shared_time,
            shared_compute_seconds=round(shared_compute, 2),
            total_incremental_cost=round(total_incremental, 4),
            total_family_cost=round(total_cost, 4),
            cost_per_child=round(cost_per_child, 4),
            total_time_minutes=total_time,
            total_compute_seconds=round(total_compute, 2),
            roi_ratio=0.0,
        )

    async def run(self, context: EngineContext) -> EngineResult:
        """Execute content family planning logic."""
        start_time = datetime.now(timezone.utc)
        params = context.parameters or {}
        action = params.get("action", "suggest_children")

        if action == "suggest_children":
            res = self.suggest_children(
                family_title=params.get("family_title", "Untitled Family"),
                topic=params.get("topic", ""),
                originality_type=params.get("originality_type", "benchmark"),
                what_are_we_adding=params.get("what_are_we_adding", ""),
                claims=params.get("claims", []),
                brand_name=params.get("brand_name", "Local AI Studio"),
                content_pillar=params.get("content_pillar", "Core"),
            )
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            return EngineResult(
                engine_id=self.manifest.id,
                engine_version=self.manifest.version,
                rules_version=self.rules_version,
                run_id=context.run_id,
                success=True,
                started_at=start_time,
                ended_at=end_time,
                duration_ms=duration_ms,
                summary=f"Suggested {len(res.proposals)} tailored child items for '{res.family_title}'.",
                outputs=[res.model_dump()],
                output_count=len(res.proposals),
            )
        elif action == "validate_family":
            val = self.validate_family(
                title=params.get("title", ""),
                topic_id=params.get("topic_id"),
                research_packet_id=params.get("research_packet_id"),
                originality_plan_id=params.get("originality_plan_id"),
                claims_count=params.get("claims_count", 0),
            )
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            return EngineResult(
                engine_id=self.manifest.id,
                engine_version=self.manifest.version,
                rules_version=self.rules_version,
                run_id=context.run_id,
                success=val.is_valid,
                started_at=start_time,
                ended_at=end_time,
                duration_ms=duration_ms,
                summary=f"Validated family '{params.get('title')}': valid={val.is_valid}",
                outputs=[val.model_dump()],
                output_count=len(val.errors),
            )
        else:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            return EngineResult(
                engine_id=self.manifest.id,
                engine_version=self.manifest.version,
                rules_version=self.rules_version,
                run_id=context.run_id,
                success=True,
                started_at=start_time,
                ended_at=end_time,
                duration_ms=duration_ms,
                summary="No-op executed.",
                outputs=[{"status": "noop"}],
                output_count=0,
            )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        ctx = context.model_copy(update={"dry_run": True})
        return await self.run(ctx)

    def explain(self, target_id: str) -> EngineExplanation:
        return EngineExplanation(
            result_id=target_id,
            summary="Content Family Engine replaces single-piece content planning by generating multiple format-tailored child items from a single empirical research investment.",
            factors=[
                {
                    "name": "One Investment, Multiple Assets",
                    "description": "Amortizes heavy local benchmark and research costs across long-form video, vertical shorts, and newsletter companion pieces.",
                },
                {
                    "name": "Evidence Reference Inheritance",
                    "description": "Children select specific claim subsets from parent family without duplicating Claim records in the database.",
                },
                {
                    "name": "Originality Value Connection",
                    "description": "Each child asset preserves an explicit connection to 'What are WE adding?' so derivative pieces never degrade into generic summaries.",
                },
                {
                    "name": "Brand Variation & Anti-Clone Policy",
                    "description": "Varies hook types, angles, and platform adaptations to prevent spamming identical content across multiple channels.",
                },
            ],
        )
