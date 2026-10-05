import re
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
from app.engines.scene_studio.contracts import (
    DecompositionRequest,
    SceneDraftInput,
    SectionInput,
    StoryboardSceneVerdict,
    StoryboardValidationResult,
)
from app.models.scene import VisualPriority, SceneStatus


class SceneStudioEngine(BaseEngine):
    """Scene Studio Engine.

    Decomposes verified, evidence-backed scripts into timed storyboard scenes with strict
    evidence-first visual priority hierarchy.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)
        self._execution_history: Dict[str, Any] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("SceneStudioEngine rules cannot be empty.")
        if "visual_priority_hierarchy" not in self.rules:
            raise ValueError("visual_priority_hierarchy must be defined in rules.")
        if "pacing" not in self.rules:
            raise ValueError("pacing must be defined in rules.")

    def health(self) -> EngineHealth:
        return EngineHealth(
            status="healthy",
            message="Scene Studio Engine operational with evidence-first visual priority.",
            details={
                "visual_hierarchy_levels": len(self.rules.get("visual_priority_hierarchy", [])),
                "words_per_second": self.rules.get("pacing", {}).get("words_per_second", 2.4),
                "require_empirical_visual_for_claims": self.rules.get("enforcement", {}).get(
                    "require_empirical_visual_for_claims", True
                ),
            },
        )

    def _determine_visual_type(
        self,
        section: SectionInput,
        chunk_text: str,
    ) -> tuple[str, Optional[str]]:
        """Determines optimal visual type following the 7-level visual priority hierarchy."""
        corpus = f"{section.heading} {section.visual_cue or ''} {chunk_text}".lower()

        # CTA / outro override -> Level 6 (Motion Graphic / Call to Action)
        if section.section_type in ("cta", "outro") or any(w in corpus for w in ["subscribe", "follow us", "link below", "channel"]):
            return VisualPriority.ORIGINAL_MOTION_GRAPHIC, None

        # Level 1: Real Screen Recording (Live UI demonstrations, interactive demos, hooks showing working app)
        if (
            "screen recording" in corpus
            or "screen record" in corpus
            or "demo" in corpus
            or "watch this" in corpus
            or "live interface" in corpus
            or (section.section_type == "hook" and not any(w in corpus for w in ["benchmark", "chart", "graph", "metric"]))
        ):
            return VisualPriority.REAL_SCREEN_RECORDING, None

        # Level 2: Benchmark / Chart (Empirical measurement, speed comparisons, test metrics)
        has_numbers = bool(re.search(r"\b\d+(\.\d+)?(%|x|ms|s|gb|mb|tokens)\b", corpus))
        if (
            section.section_type in ("evidence", "result")
            or section.linked_claim_ids
            or "benchmark" in corpus
            or "chart" in corpus
            or "latency" in corpus
            or has_numbers
        ):
            ref = section.linked_claim_ids[0] if section.linked_claim_ids else "claim-metric"
            return VisualPriority.BENCHMARK_CHART, ref

        # Level 3: Code / Terminal (Code execution, bash/cli commands, configuration)
        if any(w in corpus for w in ["terminal", "bash", "cli", "python", "git", "command", "$", "clone", "code", "npm", "docker"]):
            return VisualPriority.CODE_TERMINAL, None

        # Level 4: Workflow Diagram (Architecture diagrams, pipelines, system flows)
        if any(w in corpus for w in ["workflow", "architecture", "diagram", "pipeline", "schema", "flowchart"]):
            return VisualPriority.WORKFLOW_DIAGRAM, None

        # Level 5: Product Screenshot (Static UI, documentation, dashboards)
        if any(w in corpus for w in ["screenshot", "dashboard", "overview", "page", "docs"]):
            return VisualPriority.PRODUCT_SCREENSHOT, None

        # Level 6: Original Motion Graphic (Transitions, kinetic typography, emphasis)
        if section.section_type in ("interpretation", "transition") or any(w in corpus for w in ["key takeaway", "remember"]):
            return VisualPriority.ORIGINAL_MOTION_GRAPHIC, None

        # Level 7: Fallback to Generated Visual only when nothing specific matches
        return VisualPriority.GENERATED_VISUAL, None

    def _generate_on_screen_text(self, text: str) -> Optional[str]:
        """Extracts high-impact punchy on-screen caption from narration chunk."""
        # Find key metrics or concise punchy phrases
        metric_match = re.search(r"(\b\d+(\.\d+)?(%|x|\s*faster|\s*tokens/s|\s*ms)\b)", text, re.I)
        if metric_match:
            return metric_match.group(0).upper()

        words = text.strip().split()
        if len(words) <= 5:
            return text.strip().upper()
        # Take first 3-5 words
        return " ".join(words[:4]).upper() + "..."

    def decompose_script(self, request: DecompositionRequest) -> List[SceneDraftInput]:
        """Decomposes script sections into storyboard scenes respecting visual hierarchy."""
        wps = float(self.rules.get("pacing", {}).get("words_per_second", 2.4))
        min_duration = float(self.rules.get("pacing", {}).get("min_scene_duration_sec", 1.5))
        scenes: List[SceneDraftInput] = []

        for section in request.sections:
            narration = section.narration.strip()
            if not narration:
                continue

            # Split narration into sentence chunks
            raw_sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+", narration) if s.strip()
            ]
            if not raw_sentences:
                raw_sentences = [narration]

            for s_idx, sentence in enumerate(raw_sentences):
                word_count = len(sentence.split())
                timing = round(max(min_duration, word_count / wps), 1)

                v_type, evidence_ref = self._determine_visual_type(section, sentence)
                on_screen = self._generate_on_screen_text(sentence)

                # Transition logic: First scene cut, middle scene whip_pan or cut, CTA zoom_in
                if section.section_type == "cta":
                    transition = "zoom_in"
                elif s_idx == 0 and len(scenes) > 0:
                    transition = "whip_pan"
                else:
                    transition = "cut"

                scenes.append(
                    SceneDraftInput(
                        narration=sentence,
                        timing_estimate=timing,
                        on_screen_text=on_screen,
                        visual_type=v_type,
                        visual_source=None,
                        evidence_reference=evidence_ref,
                        transition=transition,
                        status=SceneStatus.DRAFT,
                        notes=f"Decomposed from [{section.section_type.upper()}] {section.heading}",
                    )
                )

        return scenes

    def validate_storyboard(
        self,
        scenes: List[Dict[str, Any]],
        target_duration: float = 60.0,
    ) -> StoryboardValidationResult:
        """Validates timing, visual evidence priority, and asset rights status across scenes."""
        warnings: List[str] = []
        recommendations: List[str] = []
        scene_verdicts: List[StoryboardSceneVerdict] = []

        total_duration = sum(float(s.get("timing_estimate") or 0.0) for s in scenes)
        max_short_sec = float(self.rules.get("pacing", {}).get("max_short_duration_sec", 60.0))

        is_timing_valid = True
        if target_duration <= 60.0 and total_duration > max_short_sec:
            is_timing_valid = False
            warnings.append(
                f"Storyboard total duration ({total_duration:.1f}s) exceeds the strict 60.0s YouTube Shorts / TikTok limit by {total_duration - max_short_sec:.1f}s."
            )
            recommendations.append(
                "Trim 10-15% of narration text or combine redundant scenes to bring pacing under 58 seconds."
            )

        empirical_count = 0
        missing_assets = 0
        blocked_rights = 0
        rank_map = VisualPriority.RANK_MAP

        for idx, s in enumerate(scenes, start=1):
            v_type = s.get("visual_type", VisualPriority.GENERATED_VISUAL)
            rank = rank_map.get(v_type, 7)
            is_empirical = rank in (1, 2, 3)
            if is_empirical:
                empirical_count += 1

            s_warnings: List[str] = []
            rights_status = s.get("rights_status")
            if rights_status == "DO_NOT_USE":
                blocked_rights += 1
                s_warnings.append("Asset Rights record is marked DO_NOT_USE. Media cannot be included in render.")
            elif rights_status == "UNKNOWN":
                s_warnings.append("Asset Rights record is UNKNOWN. Verification recommended before export.")

            if not s.get("visual_source"):
                missing_assets += 1

            # Warn on low-priority generated visual if narration mentions empirical metrics
            narration = s.get("narration", "").lower()
            if rank == 7 and any(w in narration for w in ["benchmark", "tested", "latency", "failure rate", "%"]):
                s_warnings.append(
                    "Narration contains empirical benchmark claim, but visual type is set to generic GENERATED_VISUAL (Rank 7). Prefer Benchmark Chart (Rank 2) or Code Terminal (Rank 3)."
                )

            scene_verdicts.append(
                StoryboardSceneVerdict(
                    scene_order=idx,
                    visual_type=v_type,
                    visual_priority_rank=rank,
                    is_empirical=is_empirical,
                    timing_estimate=float(s.get("timing_estimate") or 0.0),
                    has_evidence_link=bool(s.get("evidence_reference")),
                    rights_status=rights_status,
                    warnings=s_warnings,
                )
            )

        total_scenes = len(scenes)
        empirical_ratio = round((empirical_count / total_scenes * 100) if total_scenes > 0 else 0.0, 1)

        if empirical_ratio < 40.0:
            warnings.append(
                f"Empirical visual ratio is only {empirical_ratio}%. Studio guidelines require >= 50% empirical visuals (screen recordings, charts, terminal) to avoid generic video slop."
            )
            recommendations.append("Upgrade product screenshots or generated visuals to live terminal runs or benchmark charts.")

        all_valid = (is_timing_valid and blocked_rights == 0 and len(warnings) == 0)

        return StoryboardValidationResult(
            total_scenes=total_scenes,
            total_duration_sec=round(total_duration, 1),
            target_duration_sec=target_duration,
            is_timing_valid=is_timing_valid,
            empirical_visual_ratio=empirical_ratio,
            missing_assets_count=missing_assets,
            blocked_rights_count=blocked_rights,
            all_valid=all_valid,
            warnings=warnings,
            recommendations=recommendations,
            scenes=scene_verdicts,
        )

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        payload = context.parameters or {}

        scenes = payload.get("scenes", [])
        target_duration = float(payload.get("target_duration", 60.0))

        validation = self.validate_storyboard(scenes, target_duration)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        end_time = datetime.now(timezone.utc)

        self._execution_history[context.run_id] = validation

        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            success=validation.all_valid,
            started_at=start_time,
            ended_at=end_time,
            duration_ms=duration_ms,
            input_count=validation.total_scenes,
            output_count=validation.total_scenes,
            rejected_count=validation.blocked_rights_count,
            summary=f"Storyboard validation: {validation.total_scenes} scenes, {validation.total_duration_sec}s duration, {validation.empirical_visual_ratio}% empirical visuals.",
            outputs=[validation.model_dump()],
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        context.dry_run = True
        result = await self.run(context)
        result.summary = f"[DRY RUN] {result.summary}"
        return result

    def explain(self, result_id: str) -> EngineExplanation:
        history: Optional[StoryboardValidationResult] = self._execution_history.get(result_id)
        factors = [
            {"factor": "visual_priority_hierarchy", "value": "Real Screen > Chart > Terminal > Diagram > Screenshot > Motion Graphic > Generated Visual"},
            {"factor": "words_per_second", "value": self.rules.get("pacing", {}).get("words_per_second", 2.4)},
            {"factor": "max_short_duration_sec", "value": self.rules.get("pacing", {}).get("max_short_duration_sec", 60.0)},
        ]
        if history:
            summary = f"Validation for {result_id}: {history.total_scenes} scenes, valid={history.all_valid}, empirical_ratio={history.empirical_visual_ratio}%"
        else:
            summary = f"Storyboard explanation for {result_id}."
        return EngineExplanation(
            result_id=result_id,
            summary=summary,
            factors=factors,
        )
