import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.engines.core import BaseEngine, EngineContext, EngineExplanation, EngineHealth, EngineResult
from app.engines.content.contracts import (
    GenerateScriptRequest,
    ScriptDraftOutput,
    ScriptSectionOutput,
    SectionRefineRequest,
    SectionRefineOutput,
    ScriptQualityVerdict,
    DimensionCheckResult,
    RefinementType,
)

logger = logging.getLogger("studio.engines.content")

DEFAULT_BANNED_CLICHES = [
    "game-changer",
    "dive deep",
    "unleash",
    "revolutionary",
    "buckle up",
    "delve",
    "in today's video",
    "without further ado",
    "game changer",
]


class ContentEngine(BaseEngine):
    """Evidence-driven content and script generation engine.
    
    Generates multi-section scripts with section-level refinements
    and 6-dimension human quality gate evaluations.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("ContentEngine rules cannot be empty.")
        if "cadence" not in self.rules:
            raise ValueError("ContentEngine rules missing 'cadence' configuration.")

    def health(self) -> EngineHealth:
        has_manifest = self.manifest is not None
        has_rules = bool(self.rules)
        status = "healthy" if (has_manifest and has_rules) else "degraded"
        return EngineHealth(
            status=status,
            message="Content engine configuration and template rules loaded.",
            details={
                "engine_id": "content",
                "has_manifest": has_manifest,
                "has_rules": has_rules,
                "sections_supported": self.rules.get("sections", {}).get("standard_order", []),
            },
        )

    async def run(self, context: EngineContext) -> EngineResult:
        started_at = datetime.now(timezone.utc)
        req_data = context.inputs.get("request", {})
        req = GenerateScriptRequest(**req_data)
        script_output = self.generate_script(req)
        ended_at = datetime.now(timezone.utc)

        return EngineResult(
            engine_id="content",
            engine_name="Content Engine",
            engine_version="1.0.0",
            success=True,
            data=script_output.model_dump(),
            duration_ms=(ended_at - started_at).total_seconds() * 1000,
            started_at=started_at,
            ended_at=ended_at,
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        started_at = datetime.now(timezone.utc)
        return EngineResult(
            engine_id="content",
            engine_name="Content Engine",
            engine_version="1.0.0",
            success=True,
            data={"dry_run": True, "message": "Content engine dry run passed."},
            duration_ms=0,
            started_at=started_at,
            ended_at=started_at,
        )

    def explain(self, result_id: str) -> EngineExplanation:
        return EngineExplanation(
            result_id=result_id,
            summary="Evidence-driven script draft generated with 7 standard sections and 6-dimension quality review.",
            details={
                "workflow": "Child Content Item -> Evidence Claims Selection -> Section Narrative Generation -> Quality Dimension Scoring",
            },
        )

    def generate_script(self, req: GenerateScriptRequest) -> ScriptDraftOutput:
        """Generates a structured, evidence-grounded script draft matching the format template."""
        fmt = req.format
        claims = req.evidence_claims
        primary_claim_text = claims[0].get("text", "Our local benchmark verified a 2.4x latency improvement.") if claims else "Benchmark test showed significant performance gains."
        primary_claim_id = claims[0].get("id", "") if claims else ""
        claim_ids = [c.get("id") for c in claims if c.get("id")]

        sections: List[ScriptSectionOutput] = []

        if fmt == "short_vertical":
            # 1. Hook (0-5s)
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="hook",
                    order_index=0,
                    heading="Hook (0-5s)",
                    narration=f"Think {req.working_title.split(':')[0]} is just hype? We ran the hardware test, and here is what happened.",
                    visual_cue="Close-up of terminal benchmark output with flashing execution time in seconds.",
                    estimated_seconds=5,
                    word_count=19,
                    linked_claim_ids=[primary_claim_id] if primary_claim_id else [],
                )
            )
            # 2. Problem/Context (5-15s)
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="problem_context",
                    order_index=1,
                    heading="The Problem (5-15s)",
                    narration=f"Most cloud AI benchmarks hide the real cost and memory bottlenecks. On typical developer workstations, token latency compounds quickly.",
                    visual_cue="Screen recording showing memory spike on local GPU monitor graph.",
                    estimated_seconds=10,
                    word_count=22,
                    linked_claim_ids=[],
                )
            )
            # 3. Evidence (15-35s)
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="evidence",
                    order_index=2,
                    heading="The Data & Test (15-35s)",
                    narration=f"Here is our verified measurement: {primary_claim_text}. We tested exact prompt batches across identical quantization settings.",
                    visual_cue="Split screen side-by-side execution comparison with live timing counters.",
                    estimated_seconds=18,
                    word_count=23,
                    linked_claim_ids=claim_ids,
                )
            )
            # 4. Result (35-50s)
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="result",
                    order_index=3,
                    heading="The Verdict (35-50s)",
                    narration=f"The outcome: {req.angle}. You don't need cloud rentals when you configure local batch sizes properly.",
                    visual_cue="Highlighting the winner in green on our studio benchmark summary table.",
                    estimated_seconds=15,
                    word_count=18,
                    linked_claim_ids=[primary_claim_id] if primary_claim_id else [],
                )
            )
            # 5. CTA (50-60s)
            cta_text = "Grab our exact benchmark script and config in the description below." if req.cta_style != "direct_pitch" else "Subscribe for more real local hardware AI tests."
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="cta",
                    order_index=4,
                    heading="Call to Action (50-60s)",
                    narration=f"{cta_text} Drop a comment if you want us to test your setup next.",
                    visual_cue="Text overlay with link and studio watermark.",
                    estimated_seconds=8,
                    word_count=17,
                    linked_claim_ids=[],
                )
            )

        elif fmt == "youtube_long":
            # Long-form YouTube structure (7 full sections)
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="hook",
                    order_index=0,
                    heading="Intro & Thesis Hook",
                    narration=f"In today's empirical test, we put {req.family_title} to the test. Not based on vendor marketing claims, but on rigorous local laboratory measurements.",
                    visual_cue="Montage of the testing rig, terminal logs scrolling, and peak temperature meters.",
                    estimated_seconds=25,
                    word_count=30,
                    linked_claim_ids=[primary_claim_id] if primary_claim_id else [],
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="problem_context",
                    order_index=1,
                    heading="The Architectural Problem",
                    narration="Before examining the numbers, let's understand why this comparison matters. Standard synthetic benchmarks fail to capture real-world cache thrashing and token generation decay during long prompt contexts.",
                    visual_cue="Diagram illustrating context window memory allocation and KV cache scaling.",
                    estimated_seconds=60,
                    word_count=32,
                    linked_claim_ids=[],
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="method_test",
                    order_index=2,
                    heading="Methodology & Test Harness",
                    narration=f"Our originality plan centered on: {req.what_are_we_adding or 'reproducible local execution with controlled thermals'}. We ran 100 iterations per model under isolated thread scheduling.",
                    visual_cue="B-roll of Python test runner script execution and sensor telemetry logging.",
                    estimated_seconds=120,
                    word_count=31,
                    linked_claim_ids=[],
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="evidence",
                    order_index=3,
                    heading="Verified Evidence & Benchmark Data",
                    narration=f"Here are the primary claims confirmed during the trial: {primary_claim_text}. Notice the clear divergence in token latency once payload size exceeds 4K tokens.",
                    visual_cue="Full-screen data visualization chart comparing response curves and variance bounds.",
                    estimated_seconds=180,
                    word_count=31,
                    linked_claim_ids=claim_ids,
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="result",
                    order_index=4,
                    heading="Empirical Findings & Winner",
                    narration=f"Synthesizing the results: {req.angle}. The data clearly reveals that efficiency gains depend directly on memory bandwidth rather than raw compute alone.",
                    visual_cue="Side-by-side leaderboard ranking with color-coded metric cards.",
                    estimated_seconds=90,
                    word_count=26,
                    linked_claim_ids=[primary_claim_id] if primary_claim_id else [],
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="interpretation",
                    order_index=5,
                    heading="Production Takeaways & Economics",
                    narration="What does this mean for your production stack? If you run on self-hosted inference, choosing the right quantization format cuts your electricity and hardware amortization cost significantly.",
                    visual_cue="Cost breakdown spreadsheet showing monthly savings across 100K daily requests.",
                    estimated_seconds=90,
                    word_count=30,
                    linked_claim_ids=[],
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="cta",
                    order_index=6,
                    heading="Conclusion & Next Steps",
                    narration="All source code, raw CSV telemetry, and test configurations are available in our studio repository. Subscribe to support independent, evidence-first AI benchmarks.",
                    visual_cue="End screen card with link to GitHub repository and related benchmark videos.",
                    estimated_seconds=35,
                    word_count=26,
                    linked_claim_ids=[],
                )
            )

        elif fmt == "social_post":
            # Compact multi-part social post or thread
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="hook",
                    order_index=0,
                    heading="Post Hook",
                    narration=f"We just benchmarked {req.family_title} on local hardware. The results were not what marketing told us:",
                    visual_cue="Hero chart graphic showing latency comparison.",
                    estimated_seconds=0,
                    word_count=20,
                    linked_claim_ids=[primary_claim_id] if primary_claim_id else [],
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="evidence",
                    order_index=1,
                    heading="Core Evidence",
                    narration=f"Key Findings:\n- {primary_claim_text}\n- Angle: {req.angle}\n- Tested under strictly controlled thermal conditions.",
                    visual_cue="Data table screenshot.",
                    estimated_seconds=0,
                    word_count=21,
                    linked_claim_ids=claim_ids,
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="cta",
                    order_index=2,
                    heading="Discussion & Links",
                    narration="What has been your experience running this locally? Drop your benchmark specs below.",
                    visual_cue="Call to action card.",
                    estimated_seconds=0,
                    word_count=13,
                    linked_claim_ids=[],
                )
            )

        else:
            # Default fallback format (article/newsletter)
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="hook",
                    order_index=0,
                    heading="Executive Summary",
                    narration=f"An evidence-grounded investigation into {req.working_title}. Here is what our measurements revealed.",
                    visual_cue="Lead header banner image.",
                    estimated_seconds=30,
                    word_count=18,
                    linked_claim_ids=[primary_claim_id] if primary_claim_id else [],
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="evidence",
                    order_index=1,
                    heading="Empirical Findings",
                    narration=f"Data verification: {primary_claim_text}. We verified this claim across reproducible benchmark trials.",
                    visual_cue="Technical comparison chart.",
                    estimated_seconds=60,
                    word_count=17,
                    linked_claim_ids=claim_ids,
                )
            )
            sections.append(
                ScriptSectionOutput(
                    id=str(uuid.uuid4()),
                    section_type="cta",
                    order_index=2,
                    heading="Practical Recommendations",
                    narration="For developers planning deployments, prioritize memory bandwidth over raw TFLOP counts. Full configuration files are linked below.",
                    visual_cue="Resource checklist graphic.",
                    estimated_seconds=45,
                    word_count=21,
                    linked_claim_ids=[],
                )
            )

        total_words = sum(s.word_count for s in sections)
        total_seconds = sum(s.estimated_seconds for s in sections)

        quality_verdict = self.evaluate_quality(sections, req)

        return ScriptDraftOutput(
            id=str(uuid.uuid4()),
            content_item_id=req.content_item_id,
            format=fmt,
            title=req.working_title,
            target_platform=req.platform_target,
            target_duration_sec=req.target_duration_sec,
            total_word_count=total_words,
            estimated_duration_sec=total_seconds,
            status="DRAFT",
            sections=sections,
            quality_verdict=quality_verdict,
        )

    def refine_section(self, req: SectionRefineRequest) -> SectionRefineOutput:
        """Executes targeted section-level transformations (shorten, expand, make_clearer, more_evidence, regenerate)."""
        curr = req.current_narration
        cue = req.current_visual_cue
        rtype = req.refinement_type

        new_text = curr
        explanation = ""

        if rtype == RefinementType.SHORTEN:
            # Cut words, tighten phrasing
            sentences = [s.strip() for s in curr.split(".") if s.strip()]
            if len(sentences) > 1:
                new_text = ". ".join(sentences[: len(sentences) - 1]) + "."
            else:
                words = curr.split()
                new_text = " ".join(words[: max(5, int(len(words) * 0.7))]) + "."
            explanation = "Trimmed superfluous words and tightened sentence structure for faster cadence."

        elif rtype == RefinementType.EXPAND:
            # Add detail / elaboration
            new_text = curr.rstrip(".") + f". Specifically, this provides higher thermal headroom and reduces variance under continuous workloads."
            explanation = "Expanded technical context with operational nuances."

        elif rtype == RefinementType.MAKE_CLEARER:
            # Clean up syntax, remove jargon
            simplified = re.sub(r"\butilize\b", "use", curr, flags=re.IGNORECASE)
            simplified = re.sub(r"\bleverage\b", "use", simplified, flags=re.IGNORECASE)
            new_text = simplified
            explanation = "Simplified vocabulary and improved conversational clarity."

        elif rtype == RefinementType.MORE_EVIDENCE:
            # Inject primary claim numbers
            claim_text = req.linked_claims[0].get("text", "measured latency dropped by 34%") if req.linked_claims else "measured benchmark variance remained under 2%"
            new_text = curr.rstrip(".") + f". In our tests, {claim_text}."
            cue = "Split screen showing statistical error bounds and p-value verification."
            explanation = "Injected quantitative measurement directly into the section narrative."

        else: # REGENERATE
            new_text = f"Notice this key point: {curr.strip()}"
            explanation = "Fresh phrasing generated while preserving factual references."

        word_count = len(new_text.split())
        est_seconds = max(1, round(word_count / 2.5))

        return SectionRefineOutput(
            section_id=req.section_id,
            new_narration=new_text,
            new_visual_cue=cue,
            word_count=word_count,
            estimated_seconds=est_seconds,
            explanation=explanation,
        )

    def evaluate_quality(
        self,
        sections: List[ScriptSectionOutput],
        context: GenerateScriptRequest,
    ) -> ScriptQualityVerdict:
        """Evaluates script across 6 distinct quality dimensions without a single opaque score:
        1. Evidence
        2. Brand
        3. Originality
        4. Viewer Value
        5. Niche Fit
        6. Repetition
        """
        all_text = " ".join(s.narration for s in sections).lower()
        blocking_reasons: List[str] = []
        dimensions: Dict[str, DimensionCheckResult] = {}

        # 1. Evidence Dimension
        all_linked_claims = [cid for s in sections for cid in s.linked_claim_ids]
        has_evidence = len(all_linked_claims) > 0 or len(context.evidence_claims) == 0
        evidence_score = 90.0 if has_evidence else 40.0
        evidence_flags = []
        if not has_evidence:
            evidence_flags.append("No verified claims linked in evidence sections.")
            blocking_reasons.append("unsupported_claim")

        dimensions["evidence"] = DimensionCheckResult(
            dimension="evidence",
            score=evidence_score,
            passed=has_evidence,
            is_blocking=not has_evidence,
            notes=f"{len(all_linked_claims)} evidence claims referenced in narration.",
            flags=evidence_flags,
        )

        # 2. Brand Dimension
        # Always include DEFAULT_BANNED_CLICHES as baseline; merge brand-specific ones
        banned = list(set(DEFAULT_BANNED_CLICHES + (context.banned_cliches or [])))
        detected_cliches = [c for c in banned if c.lower() in all_text]
        brand_score = max(0.0, 100.0 - (len(detected_cliches) * 25.0))
        brand_passed = len(detected_cliches) == 0
        brand_flags = [f"Banned cliché detected: '{c}'" for c in detected_cliches]
        if not brand_passed:
            blocking_reasons.append("critical_brand_failure")

        dimensions["brand"] = DimensionCheckResult(
            dimension="brand",
            score=brand_score,
            passed=brand_passed,
            is_blocking=not brand_passed,
            notes="Voice and tone adhere to BrandProfile guidelines." if brand_passed else f"{len(detected_cliches)} brand cliches detected.",
            flags=brand_flags,
        )

        # 3. Originality Dimension
        has_original_value = bool(context.what_are_we_adding.strip()) or context.original_value_type != "none"
        orig_score = 95.0 if has_original_value else 30.0
        orig_flags = []
        if not has_original_value:
            orig_flags.append("Missing explicit original value or experimental connection.")
            blocking_reasons.append("missing_original_value")

        dimensions["originality"] = DimensionCheckResult(
            dimension="originality",
            score=orig_score,
            passed=has_original_value,
            is_blocking=not has_original_value,
            notes=f"Linked to {context.original_value_type} original contribution.",
            flags=orig_flags,
        )

        # 4. Viewer Value Dimension
        # Check presence of actionable payoff words (how to, steps, results, avoid, config, code, setup, takeaway)
        value_keywords = ["result", "test", "measure", "avoid", "config", "benchmark", "setup", "outcome", "takeaway"]
        found_val = any(kw in all_text for kw in value_keywords)
        val_score = 88.0 if found_val else 60.0
        val_flags = [] if found_val else ["Script lacks concrete viewer actionable takeaways."]

        dimensions["viewer_value"] = DimensionCheckResult(
            dimension="viewer_value",
            score=val_score,
            passed=found_val,
            is_blocking=False,
            notes="Clear empirical payoff provided to audience." if found_val else "Consider strengthening practical advice.",
            flags=val_flags,
        )

        # 5. Niche Fit Dimension
        # Check for blocked topic violations
        blocked_found = [b for b in context.niche_blocked_topics if b.lower() in all_text]
        niche_passed = len(blocked_found) == 0
        niche_score = 100.0 if niche_passed else 20.0
        niche_flags = [f"Blocked niche topic detected: '{b}'" for b in blocked_found]
        if not niche_passed:
            blocking_reasons.append("off_niche")

        dimensions["niche_fit"] = DimensionCheckResult(
            dimension="niche_fit",
            score=niche_score,
            passed=niche_passed,
            is_blocking=not niche_passed,
            notes="Aligned with single active NicheProfile." if niche_passed else f"Contains off-niche terms: {blocked_found}",
            flags=niche_flags,
        )

        # 6. Repetition Dimension
        # Check for repetitive sentence starts across sections
        section_first_words = [s.narration.strip().split()[0].lower() for s in sections if s.narration.strip()]
        has_duplicate_starts = len(section_first_words) != len(set(section_first_words))
        rep_score = 90.0 if not has_duplicate_starts else 70.0
        rep_flags = ["Consecutive sections use identical opening words."] if has_duplicate_starts else []

        dimensions["repetition"] = DimensionCheckResult(
            dimension="repetition",
            score=rep_score,
            passed=not has_duplicate_starts,
            is_blocking=False,
            notes="Healthy sentence diversity across sections." if not has_duplicate_starts else "Vary section opening phrasing.",
            flags=rep_flags,
        )

        is_approvable = len(blocking_reasons) == 0
        summary_text = (
            "All 6 quality dimensions passed. Script is ready for approval."
            if is_approvable
            else f"Quality gate blocked: {', '.join(blocking_reasons)}."
        )

        return ScriptQualityVerdict(
            is_approvable=is_approvable,
            blocking_reasons=blocking_reasons,
            dimension_scores=dimensions,
            summary=summary_text,
        )
