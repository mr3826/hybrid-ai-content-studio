import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.database import AsyncSessionLocal
from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.niche_guard.contracts import (
    NicheGuardFactor,
    NicheGuardInput,
    NicheGuardVerdict,
)
from app.models.niche import NicheProfile, SINGLETON_NICHE_ID
from sqlalchemy import select


class NicheGuardEngine(BaseEngine):
    """Niche Guard Engine: Deterministic filtering against the single active niche profile."""

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).resolve().parent
        super().__init__(engine_dir=engine_dir)
        self._execution_history: Dict[str, NicheGuardVerdict] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("NicheGuardEngine rules cannot be empty.")
        if "thresholds" not in self.rules:
            raise ValueError("NicheGuardEngine rules missing 'thresholds' block.")
        if "min_pass_score" not in self.rules["thresholds"]:
            raise ValueError("NicheGuardEngine rules missing 'min_pass_score'.")
        if "weights" not in self.rules:
            raise ValueError("NicheGuardEngine rules missing 'weights' block.")

    def health(self) -> EngineHealth:
        try:
            self.validate_config()
            return EngineHealth(
                status="healthy",
                message="NicheGuardEngine is operational with valid taxonomy rules.",
                details={
                    "version": self.version,
                    "min_pass_score": self.rules.get("thresholds", {}).get("min_pass_score", 55.0),
                },
            )
        except Exception as e:
            return EngineHealth(
                status="failing",
                message=f"NicheGuardEngine health check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _get_active_niche_data(self, override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch active singleton NicheProfile from SQLite or use provided override."""
        if override:
            return override

        try:
            async with AsyncSessionLocal() as session:
                stmt = select(NicheProfile).where(NicheProfile.id == SINGLETON_NICHE_ID)
                result = await session.execute(stmt)
                niche = result.scalar_one_or_none()
                if niche:
                    return {
                        "name": niche.name,
                        "one_sentence_definition": niche.one_sentence_definition,
                        "allowed_topics": niche.allowed_topics or [],
                        "adjacent_topics": niche.adjacent_topics or [],
                        "blocked_topics": niche.blocked_topics or [],
                        "must_have_signals": niche.must_have_signals or [],
                        "negative_keywords": niche.negative_keywords or [],
                        "content_pillars": niche.content_pillars or [],
                        "primary_problems": niche.primary_problems or [],
                    }
        except Exception:
            pass

        # Fallback minimal niche taxonomy if DB not populated yet
        return {
            "name": "AI Engineering & Coding Automation",
            "allowed_topics": [
                "coding agents", "local LLMs", "developer tools",
                "AI engineering", "IDE integrations", "evals and benchmarks", "workflow automation"
            ],
            "adjacent_topics": ["software architecture", "DevOps", "vector databases", "open source models"],
            "blocked_topics": [
                "crypto/web3 trading", "general consumer gadgets",
                "passive income schemes", "clickbait AI news without code/tests"
            ],
            "must_have_signals": ["code repository", "reproducible benchmark", "documentation or paper", "practical tool release"],
            "negative_keywords": ["get rich quick", "secret trick", "replaced all coders", "100x money"],
            "content_pillars": [
                {"name": "Coding Agent Stress Tests", "keywords": ["agent", "benchmark", "coding"]},
                {"name": "Local Models & Tooling", "keywords": ["ollama", "vllm", "local", "deepseek"]},
                {"name": "Production Automation Recipes", "keywords": ["automation", "recipe", "workflow"]},
            ],
            "primary_problems": ["API costs", "benchmark claims", "local LLM integration"],
        }

    def _match_term(self, term: str, text: str) -> bool:
        """Check if term occurs in text with case-insensitive boundary/phrase matching."""
        cleaned_term = term.strip().lower()
        if not cleaned_term:
            return False
        # Direct substring matching for multi-word or special-character terms
        if " " in cleaned_term or "/" in cleaned_term or "-" in cleaned_term or "." in cleaned_term:
            return cleaned_term in text.lower()
        # Word boundary search for single word terms
        pattern = r"\b" + re.escape(cleaned_term) + r"\b"
        return bool(re.search(pattern, text.lower()))

    def evaluate_item(self, item: NicheGuardInput, niche: Dict[str, Any]) -> NicheGuardVerdict:
        """Deterministically evaluate text against active niche rules."""
        thresholds = self.rules.get("thresholds", {})
        weights = self.rules.get("weights", {})
        behavior = self.rules.get("behavior", {})

        min_pass_score = float(thresholds.get("min_pass_score", 55.0))
        neg_penalty = float(thresholds.get("negative_keyword_penalty", 25.0))
        adjacent_penalty = float(thresholds.get("adjacent_penalty", 10.0))
        missing_must_have_pen = float(thresholds.get("missing_must_have_penalty", 15.0))

        instant_block_blocked = behavior.get("instant_block_on_blocked_topic", True)
        require_allowed_or_pillar = behavior.get("require_allowed_or_pillar", True)

        # Build combined search corpus
        combined_text = f"{item.title} {item.text} {' '.join(item.tags)}".strip()
        corpus = combined_text.lower()

        factors: List[NicheGuardFactor] = []
        raw_score = 0.0

        # 1. Blocked Topics Check (Instant Rejection)
        blocked_topics = niche.get("blocked_topics", [])
        blocked_detected: List[str] = []
        for bt in blocked_topics:
            if self._match_term(bt, corpus):
                blocked_detected.append(bt)

        if blocked_detected and instant_block_blocked:
            verdict_id = f"ngv-{uuid.uuid4().hex[:12]}"
            factors.append(NicheGuardFactor(
                criterion="blocked_topics",
                points=-100.0,
                detail=f"Content matched strictly blocked topic(s): {', '.join(blocked_detected)}",
                matched_items=blocked_detected,
            ))
            verdict = NicheGuardVerdict(
                id=verdict_id,
                input_id=item.id,
                passed=False,
                score=0.0,
                reason=f"Rejected: strictly blocked topic detected [{', '.join(blocked_detected)}].",
                primary_pillar=None,
                is_adjacent=False,
                is_blocked=True,
                audience_relevance=0.0,
                blocked_topics_detected=blocked_detected,
                factors=factors,
            )
            self._execution_history[verdict.id] = verdict
            return verdict

        # 2. Content Pillars Matching
        pillars = niche.get("content_pillars", [])
        matched_pillars: List[str] = []
        pillar_match_max = float(weights.get("pillar_match_max", 35.0))
        pillar_unit_weight = float(weights.get("pillar_unit_weight", 20.0))

        for p in pillars:
            p_name = p.get("name") if isinstance(p, dict) else str(p)
            matched = False
            if self._match_term(p_name, corpus):
                matched = True
            elif isinstance(p, dict) and "keywords" in p:
                for kw in p["keywords"]:
                    if self._match_term(kw, corpus):
                        matched = True
                        break
            if not matched:
                # Tokenize pillar name into meaningful words (length > 3)
                name_words = [w.lower() for w in re.findall(r"\b\w+\b", p_name) if len(w) > 3]
                if name_words:
                    matched_words = sum(1 for nw in name_words if nw in corpus)
                    if matched_words >= 2 or (len(name_words) == 1 and matched_words == 1):
                        matched = True
            if matched:
                matched_pillars.append(p_name)

        pillar_points = min(pillar_match_max, len(matched_pillars) * pillar_unit_weight)
        if pillar_points > 0:
            raw_score += pillar_points
            factors.append(NicheGuardFactor(
                criterion="content_pillars",
                points=pillar_points,
                detail=f"Matched {len(matched_pillars)} content pillar(s): {', '.join(matched_pillars)}",
                matched_items=matched_pillars,
            ))

        # 3. Allowed Topics Matching
        allowed_topics = niche.get("allowed_topics", [])
        matched_allowed: List[str] = []
        allowed_max = float(weights.get("allowed_topic_max", 40.0))
        allowed_unit = float(weights.get("allowed_topic_unit_weight", 15.0))

        for topic in allowed_topics:
            if self._match_term(topic, corpus):
                matched_allowed.append(topic)

        allowed_points = min(allowed_max, len(matched_allowed) * allowed_unit)
        if allowed_points > 0:
            raw_score += allowed_points
            factors.append(NicheGuardFactor(
                criterion="allowed_topics",
                points=allowed_points,
                detail=f"Matched {len(matched_allowed)} allowed topic(s): {', '.join(matched_allowed)}",
                matched_items=matched_allowed,
            ))

        # 4. Adjacent Topics Check
        adjacent_topics = niche.get("adjacent_topics", [])
        matched_adjacent: List[str] = []
        for adj in adjacent_topics:
            if self._match_term(adj, corpus):
                matched_adjacent.append(adj)

        if matched_adjacent:
            # If no core allowed topic matched, adjacent gives partial credit but incurs penalty
            if len(matched_allowed) == 0:
                raw_score += 15.0
                raw_score -= adjacent_penalty
                factors.append(NicheGuardFactor(
                    criterion="adjacent_topics_without_core",
                    points=15.0 - adjacent_penalty,
                    detail=f"Matched adjacent topic(s) [{', '.join(matched_adjacent)}] without core allowed topics (-{adjacent_penalty} penalty)",
                    matched_items=matched_adjacent,
                ))
            else:
                factors.append(NicheGuardFactor(
                    criterion="adjacent_topics_context",
                    points=5.0,
                    detail=f"Matched adjacent context: {', '.join(matched_adjacent)}",
                    matched_items=matched_adjacent,
                ))
                raw_score += 5.0

        # 5. Must-Have Signals
        must_haves = niche.get("must_have_signals", [])
        matched_must_haves: List[str] = []
        must_have_max = float(weights.get("must_have_signal_max", 15.0))
        must_have_unit = float(weights.get("must_have_unit_weight", 8.0))

        for mh in must_haves:
            if self._match_term(mh, corpus):
                matched_must_haves.append(mh)

        if matched_must_haves:
            mh_points = min(must_have_max, len(matched_must_haves) * must_have_unit)
            raw_score += mh_points
            factors.append(NicheGuardFactor(
                criterion="must_have_signals",
                points=mh_points,
                detail=f"Validated {len(matched_must_haves)} must-have signal(s): {', '.join(matched_must_haves)}",
                matched_items=matched_must_haves,
            ))
        elif must_haves and len(matched_allowed) > 0:
            # Configured must-haves present in niche, but none found
            raw_score -= missing_must_have_pen
            factors.append(NicheGuardFactor(
                criterion="missing_must_have_signals",
                points=-missing_must_have_pen,
                detail=f"Missing required verifiable signals (-{missing_must_have_pen})",
                matched_items=[],
            ))

        # 6. Primary Problems / Audience Needs
        problems = niche.get("primary_problems", [])
        matched_problems: List[str] = []
        problem_max = float(weights.get("primary_problem_max", 10.0))
        problem_unit = float(weights.get("primary_problem_unit_weight", 5.0))

        for prob in problems:
            # Check keywords inside the problem phrase
            prob_keywords = [w for w in prob.split() if len(w) > 4]
            for kw in prob_keywords:
                if self._match_term(kw, corpus):
                    matched_problems.append(kw)
                    break

        if matched_problems:
            prob_points = min(problem_max, len(matched_problems) * problem_unit)
            raw_score += prob_points
            factors.append(NicheGuardFactor(
                criterion="audience_problems",
                points=prob_points,
                detail=f"Addressed audience problem keywords: {', '.join(set(matched_problems))}",
                matched_items=list(set(matched_problems)),
            ))

        # 7. Negative Keywords (Penalties)
        neg_keywords = niche.get("negative_keywords", [])
        matched_neg: List[str] = []
        for nk in neg_keywords:
            if self._match_term(nk, corpus):
                matched_neg.append(nk)

        if matched_neg:
            total_neg_penalty = len(matched_neg) * neg_penalty
            raw_score -= total_neg_penalty
            factors.append(NicheGuardFactor(
                criterion="negative_keywords",
                points=-total_neg_penalty,
                detail=f"Matched negative keyword(s): {', '.join(matched_neg)} (-{total_neg_penalty} points)",
                matched_items=matched_neg,
            ))

        final_score = max(0.0, min(100.0, round(raw_score, 1)))

        # Determine pass/fail
        passed = True
        reasons: List[str] = []

        if require_allowed_or_pillar and len(matched_allowed) == 0 and len(matched_pillars) == 0:
            passed = False
            reasons.append("Does not match any defined content pillars or core allowed topics")

        if final_score < min_pass_score:
            passed = False
            reasons.append(f"Score {final_score} is below cutoff {min_pass_score}")

        if passed:
            summary_reason = (
                f"Approved: Relevance score {final_score}/100 meets requirements "
                f"({len(matched_pillars)} pillar(s), {len(matched_allowed)} topic(s))."
            )
        else:
            summary_reason = f"Rejected: {'; '.join(reasons)}."

        # Audience Relevance Evaluation
        target_audience_desc = niche.get("audience", "")
        audience_words = [w.lower() for w in re.findall(r"\b\w+\b", target_audience_desc) if len(w) > 4]
        matched_aud_words = [w for w in audience_words if w in corpus]
        if not audience_words:
            aud_rel_score = 75.0 if passed else round(final_score * 0.5, 1)
        else:
            base_aud = 50.0 if passed else 20.0
            aud_rel_score = min(100.0, round(base_aud + (len(matched_aud_words) * 20.0) + (len(matched_problems) * 10.0), 1))

        factors.append(NicheGuardFactor(
            criterion="audience_relevance",
            points=round(aud_rel_score * 0.1, 1),
            detail=f"Audience relevance evaluated at {aud_rel_score}% based on persona target keywords and problem fit.",
            matched_items=matched_aud_words,
        ))

        verdict_id = f"ngv-{uuid.uuid4().hex[:12]}"
        verdict = NicheGuardVerdict(
            id=verdict_id,
            input_id=item.id,
            passed=passed,
            score=final_score,
            reason=summary_reason,
            primary_pillar=matched_pillars[0] if matched_pillars else None,
            is_adjacent=bool(matched_adjacent and not matched_allowed),
            is_blocked=False,
            audience_relevance=aud_rel_score,
            pillar_matches=matched_pillars,
            matched_allowed_topics=matched_allowed,
            matched_adjacent_topics=matched_adjacent,
            matched_must_have_signals=matched_must_haves,
            matched_negative_keywords=matched_neg,
            blocked_topics_detected=[],
            factors=factors,
        )
        self._execution_history[verdict.id] = verdict
        return verdict

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = datetime.now(timezone.utc)
        t0 = time.perf_counter()

        niche_override = context.parameters.get("niche_profile")
        niche = await self._get_active_niche_data(niche_override)

        raw_inputs = []
        if "input" in context.parameters:
            raw_inputs.append(context.parameters["input"])
        elif "items" in context.parameters:
            raw_inputs.extend(context.parameters["items"])
        elif "candidates" in context.parameters:
            raw_inputs.extend(context.parameters["candidates"])
        else:
            # Default demo sample
            raw_inputs.append({
                "id": "sample-01",
                "title": "Benchmarking Claude 3.7 vs DeepSeek V3 for Local Coding Agents",
                "text": "Empirical comparison of token latency, IDE integrations, and coding benchmarks on local repos.",
                "tags": ["coding agents", "local LLMs", "evals and benchmarks"],
            })

        verdicts: List[NicheGuardVerdict] = []
        rejected_count = 0
        explanations: List[Dict[str, Any]] = []

        for raw in raw_inputs:
            item = NicheGuardInput(**raw) if isinstance(raw, dict) else raw
            verdict = self.evaluate_item(item, niche)
            verdicts.append(verdict)
            if not verdict.passed:
                rejected_count += 1

            explanations.append({
                "verdict_id": verdict.id,
                "input_id": verdict.input_id,
                "passed": verdict.passed,
                "score": verdict.score,
                "reason": verdict.reason,
                "blocked": verdict.blocked_topics_detected,
                "pillars": verdict.pillar_matches,
                "allowed": verdict.matched_allowed_topics,
            })

        duration_ms = int((time.perf_counter() - t0) * 1000)
        end_time = datetime.now(timezone.utc)
        passed_count = len(verdicts) - rejected_count

        return EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            run_id=context.run_id,
            success=True,
            started_at=start_time,
            ended_at=end_time,
            duration_ms=duration_ms,
            input_count=len(verdicts),
            output_count=passed_count,
            rejected_count=rejected_count,
            error_count=0,
            cost=0.0,
            summary=f"Niche Guard evaluated {len(verdicts)} item(s): {passed_count} passed, {rejected_count} rejected.",
            outputs=[v.model_dump() for v in verdicts],
            explanations=explanations,
        )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        context.dry_run = True
        result = await self.run(context)
        result.summary = f"[DRY RUN] {result.summary}"
        return result

    def explain(self, result_id: str) -> EngineExplanation:
        verdict = self._execution_history.get(result_id)
        if not verdict:
            return EngineExplanation(
                result_id=result_id,
                summary=f"No execution history found for verdict '{result_id}'.",
                factors=[],
            )

        factors_data = [f.model_dump() for f in verdict.factors]
        status_text = "PASSED" if verdict.passed else "REJECTED"
        return EngineExplanation(
            result_id=result_id,
            summary=f"Verdict {result_id} {status_text} with score {verdict.score}/100. {verdict.reason}",
            factors=factors_data,
        )
