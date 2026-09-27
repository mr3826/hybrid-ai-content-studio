import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.database import AsyncSessionLocal
from app.engines.brand.contracts import (
    BrandQAInput,
    BrandQAVerdict,
    BrandViolation,
)
from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.models.brand import (
    BrandExemplar,
    BrandProfile,
    SINGLETON_BRAND_ID,
)
from sqlalchemy import select


class BrandEngine(BaseEngine):
    """Brand Engine: Enforces brand DNA, voice, tone, vocabulary rules, and QA gates."""

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).resolve().parent
        super().__init__(engine_dir=engine_dir)
        self._execution_history: Dict[str, BrandQAVerdict] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("BrandEngine rules cannot be empty.")
        if "thresholds" not in self.rules:
            raise ValueError("BrandEngine rules missing 'thresholds' block.")
        if "min_pass_score" not in self.rules["thresholds"]:
            raise ValueError("BrandEngine rules missing 'min_pass_score'.")
        if "weights" not in self.rules:
            raise ValueError("BrandEngine rules missing 'weights' block.")
        if "penalties" not in self.rules:
            raise ValueError("BrandEngine rules missing 'penalties' block.")

    def health(self) -> EngineHealth:
        try:
            self.validate_config()
            return EngineHealth(
                status="healthy",
                message="BrandEngine is operational with valid brand QA rules.",
                details={
                    "version": self.version,
                    "min_pass_score": self.rules.get("thresholds", {}).get("min_pass_score", 70.0),
                },
            )
        except Exception as e:
            return EngineHealth(
                status="failing",
                message=f"BrandEngine health check failed: {str(e)}",
                details={"error": str(e)},
            )

    async def _get_brand_data(
        self, override: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Fetch active singleton BrandProfile and exemplars from SQLite, or fallback."""
        if override:
            return override.get("profile", override), override.get("exemplars", [])

        profile_data: Optional[Dict[str, Any]] = None
        exemplars_data: List[Dict[str, Any]] = []

        try:
            async with AsyncSessionLocal() as session:
                stmt = select(BrandProfile).where(BrandProfile.id == SINGLETON_BRAND_ID)
                result = await session.execute(stmt)
                brand = result.scalar_one_or_none()
                if brand:
                    profile_data = {
                        "brand_name": brand.brand_name,
                        "brand_promise": brand.brand_promise,
                        "audience": brand.audience,
                        "tone": brand.tone or [],
                        "voice_rules": brand.voice_rules or [],
                        "preferred_vocabulary": brand.preferred_vocabulary or [],
                        "avoid_vocabulary": brand.avoid_vocabulary or [],
                        "banned_cliches": brand.banned_cliches or [],
                        "claim_rules": brand.claim_rules or [],
                        "cta_style": brand.cta_style or "",
                    }

                ex_stmt = select(BrandExemplar)
                ex_res = await session.execute(ex_stmt)
                for ex in ex_res.scalars().all():
                    exemplars_data.append({
                        "id": ex.id,
                        "category": ex.category,
                        "title": ex.title,
                        "content": ex.content,
                        "platform": ex.platform,
                    })
        except Exception:
            pass

        if not profile_data:
            # Fallback default configuration
            profile_data = {
                "brand_name": "Practical AI Studio",
                "brand_promise": "Tested AI tools, automated workflows, and honest benchmarks without hype.",
                "audience": "Engineers, builders, and technical knowledge workers.",
                "tone": ["evidence-driven", "concise", "practical", "calm", "transparent"],
                "voice_rules": [
                    "Show the terminal or interface; do not merely talk about it.",
                    "State costs, latency, and failure rates explicitly.",
                    "Never declare a tool 'game-changing' or 'revolutionary'.",
                ],
                "preferred_vocabulary": ["workflow", "benchmark", "latency", "trade-off", "failure rate", "reproducible"],
                "avoid_vocabulary": ["game-changer", "insane", "mind-blowing", "unbelievable", "passive income"],
                "banned_cliches": [
                    "in today's fast-paced world",
                    "without further ado",
                    "let's dive right in",
                    "dive right into",
                ],
                "claim_rules": [
                    "Every speed or accuracy claim must cite a benchmark run or primary source.",
                    "Include pricing tiers and hidden API token limits.",
                ],
                "cta_style": "Direct, educational, and low-friction.",
            }

        return profile_data, exemplars_data

    def _match_term(self, term: str, text: str) -> bool:
        cleaned_term = term.strip().lower()
        if not cleaned_term:
            return False
        if " " in cleaned_term or "/" in cleaned_term or "-" in cleaned_term or "." in cleaned_term:
            return cleaned_term in text.lower()
        pattern = r"\b" + re.escape(cleaned_term) + r"\b"
        return bool(re.search(pattern, text.lower()))

    def evaluate_item(
        self,
        item: BrandQAInput,
        brand: Dict[str, Any],
        exemplars: List[Dict[str, Any]],
    ) -> BrandQAVerdict:
        thresholds = self.rules.get("thresholds", {})
        weights = self.rules.get("weights", {})
        penalties = self.rules.get("penalties", {})
        rewards = self.rules.get("rewards", {})

        min_pass_score = float(thresholds.get("min_pass_score", 70.0))
        max_crit_violations = int(thresholds.get("max_critical_violations", 0))

        banned_cliche_penalty = float(penalties.get("banned_cliche_penalty", 30.0))
        avoid_word_penalty = float(penalties.get("avoid_word_penalty", 25.0))
        hype_exclamation_penalty = float(penalties.get("hype_exclamation_penalty", 10.0))
        all_caps_penalty = float(penalties.get("all_caps_penalty", 10.0))
        unsupported_claim_penalty = float(penalties.get("unsupported_claim_penalty", 15.0))
        preferred_word_reward = float(rewards.get("preferred_word_reward", 10.0))

        combined_text = f"{item.title} {item.body} {item.hook or ''} {item.cta or ''}".strip()
        corpus = combined_text.lower()

        violations: List[BrandViolation] = []
        factors: List[Dict[str, Any]] = []

        # 1. Banned Clichés Check
        banned_cliches = brand.get("banned_cliches", [])
        matched_cliches: List[str] = []
        for cliche in banned_cliches:
            # Strip trailing ellipsis for matching
            search_cliche = re.sub(r"\.\.\.+$", "", cliche).strip()
            if self._match_term(search_cliche, corpus):
                matched_cliches.append(cliche)
                violations.append(BrandViolation(
                    rule_type="banned_cliche",
                    severity="critical",
                    matched_phrase=cliche,
                    message=f"Banned cliché '{cliche}' violates studio editorial policy.",
                    suggestion="Remove cliché and start directly with the empirical observation or terminal command.",
                ))

        cliche_score = max(0.0, 100.0 - (len(matched_cliches) * banned_cliche_penalty))
        factors.append({
            "dimension": "cliche",
            "score": cliche_score,
            "matched_cliches": matched_cliches,
            "penalty_applied": len(matched_cliches) * banned_cliche_penalty,
        })

        # 2. Avoid vs Preferred Vocabulary
        avoid_vocabulary = brand.get("avoid_vocabulary", [])
        matched_avoid: List[str] = []
        for avoid in avoid_vocabulary:
            if self._match_term(avoid, corpus):
                matched_avoid.append(avoid)
                violations.append(BrandViolation(
                    rule_type="avoid_vocabulary",
                    severity="critical",
                    matched_phrase=avoid,
                    message=f"Blacklisted vocabulary word '{avoid}' violates technical credibility rules.",
                    suggestion=f"Replace '{avoid}' with an objective benchmark metric or verified trade-off.",
                ))

        preferred_vocabulary = brand.get("preferred_vocabulary", [])
        matched_preferred: List[str] = []
        for pref in preferred_vocabulary:
            if self._match_term(pref, corpus):
                matched_preferred.append(pref)

        base_vocab = 100.0 - (len(matched_avoid) * avoid_word_penalty)
        vocab_boost = min(20.0, len(matched_preferred) * preferred_word_reward)
        vocab_score = max(0.0, min(100.0, base_vocab + vocab_boost))

        factors.append({
            "dimension": "vocabulary",
            "score": vocab_score,
            "matched_avoid": matched_avoid,
            "matched_preferred": matched_preferred,
        })

        # 3. Tone & Hype Analysis
        tone_score = 100.0

        # Exclamation point check (calm tone)
        exclamation_count = combined_text.count("!")
        if exclamation_count > 1:
            excess = exclamation_count - 1
            deduction = excess * hype_exclamation_penalty
            tone_score = max(0.0, tone_score - deduction)
            violations.append(BrandViolation(
                rule_type="excessive_hype",
                severity="warning",
                matched_phrase=f"{exclamation_count} exclamation points",
                message=f"Found {exclamation_count} exclamation points. Studio tone requires calm, neutral punctuation.",
                suggestion="Replace exclamation points with periods.",
            ))

        # Check for ALL CAPS words (excluding common acronyms)
        common_acronyms = {"AI", "LLM", "API", "CPU", "GPU", "IDE", "CUDA", "JSON", "HTTP", "REST", "TTS", "BGM", "WAL"}
        words = re.findall(r"\b[A-Z]{3,}\b", combined_text)
        all_caps_violations = [w for w in words if w not in common_acronyms]
        if all_caps_violations:
            tone_score = max(0.0, tone_score - (len(all_caps_violations) * all_caps_penalty))
            violations.append(BrandViolation(
                rule_type="tone_mismatch",
                severity="warning",
                matched_phrase=", ".join(all_caps_violations),
                message="ALL CAPS shouting words detected.",
                suggestion="Use normal casing for technical emphasis.",
            ))

        factors.append({
            "dimension": "tone",
            "score": tone_score,
            "exclamation_count": exclamation_count,
            "all_caps": all_caps_violations,
        })

        # 4. Claims and Evidence Verification
        claim_score = 100.0
        claim_patterns = [
            r"\b(\d+x\s+faster)\b",
            r"\b(\d+%\s*(faster|boost|improvement|reduction|gain))\b",
            r"\b(fastest|most\s+powerful|zero\s+errors)\b",
        ]
        unsupported_claims: List[str] = []
        evidence_keywords = ["benchmark", "measured", "tested", "latency", "source", "test", "empirical"]

        for pat in claim_patterns:
            matches = re.findall(pat, combined_text, flags=re.IGNORECASE)
            for m in matches:
                phrase = m[0] if isinstance(m, tuple) else m
                # Check if evidence keyword exists in corpus
                has_evidence = any(ew in corpus for ew in evidence_keywords)
                if not has_evidence:
                    unsupported_claims.append(phrase)
                    violations.append(BrandViolation(
                        rule_type="unsupported_claim",
                        severity="warning",
                        matched_phrase=phrase,
                        message=f"Performance claim '{phrase}' is made without citing a benchmark run or test data.",
                        suggestion="Explicitly cite the benchmark test or hardware setup supporting this claim.",
                    ))
                    claim_score = max(0.0, claim_score - unsupported_claim_penalty)

        factors.append({
            "dimension": "claim",
            "score": claim_score,
            "unsupported_claims": unsupported_claims,
        })

        # 5. Redundancy & Repetition Check
        repetition_score = 100.0
        sentences = [s.strip() for s in re.split(r"[.!?]", combined_text) if len(s.strip()) > 15]
        if len(sentences) > len(set(sentences)):
            repetition_score = 60.0
            violations.append(BrandViolation(
                rule_type="redundancy",
                severity="suggestion",
                matched_phrase="duplicate sentence",
                message="Duplicate sentences detected in script draft.",
                suggestion="Prune redundant sentences to keep script concise and punchy.",
            ))

        factors.append({
            "dimension": "repetition",
            "score": repetition_score,
        })

        # 6. Approved Exemplar Search
        exemplar_matches: List[Dict[str, Any]] = []
        for ex in exemplars:
            # Score relevance to draft title/body
            ex_words = set(ex.get("content", "").lower().split())
            draft_words = set(corpus.split())
            overlap = len(ex_words.intersection(draft_words))
            if overlap >= 3:
                exemplar_matches.append({
                    "id": ex.get("id"),
                    "category": ex.get("category"),
                    "title": ex.get("title"),
                    "content": ex.get("content")[:120] + "...",
                    "overlap_tokens": overlap,
                })
        exemplar_matches.sort(key=lambda x: x["overlap_tokens"], reverse=True)
        exemplar_matches = exemplar_matches[:3]

        # 7. Overall Weighted Adherence Score
        w_tone = float(weights.get("tone", 0.25))
        w_vocab = float(weights.get("vocabulary", 0.25))
        w_cliche = float(weights.get("cliche", 0.25))
        w_claim = float(weights.get("claim", 0.15))
        w_rep = float(weights.get("repetition", 0.10))

        overall_score = round(
            (tone_score * w_tone)
            + (vocab_score * w_vocab)
            + (cliche_score * w_cliche)
            + (claim_score * w_claim)
            + (repetition_score * w_rep),
            1,
        )

        critical_violations = [v for v in violations if v.severity == "critical"]
        on_brand = (overall_score >= min_pass_score) and (len(critical_violations) <= max_crit_violations)

        suggested_fixes = [v.suggestion for v in violations if v.suggestion]

        verdict_id = f"bqv-{uuid.uuid4().hex[:12]}"
        verdict = BrandQAVerdict(
            id=verdict_id,
            input_id=item.id,
            on_brand=on_brand,
            overall_score=overall_score,
            tone_score=tone_score,
            vocabulary_score=vocab_score,
            cliche_score=cliche_score,
            claim_score=claim_score,
            repetition_score=repetition_score,
            violations=violations,
            matched_preferred_words=matched_preferred,
            matched_avoid_words=matched_avoid,
            matched_cliches=matched_cliches,
            suggested_fixes=suggested_fixes,
            exemplar_matches=exemplar_matches,
            factors=factors,
        )
        self._execution_history[verdict.id] = verdict
        return verdict

    async def run(self, context: EngineContext) -> EngineResult:
        start_time = datetime.now(timezone.utc)
        t0 = time.perf_counter()

        brand_override = context.parameters.get("brand_profile")
        brand, exemplars = await self._get_brand_data(brand_override)

        raw_inputs = []
        if "input" in context.parameters:
            raw_inputs.append(context.parameters["input"])
        elif "items" in context.parameters:
            raw_inputs.extend(context.parameters["items"])
        elif "drafts" in context.parameters:
            raw_inputs.extend(context.parameters["drafts"])
        else:
            raw_inputs.append({
                "id": "draft-01",
                "title": "Benchmarking Local Qwen 2.5 Coder vs Claude 3.7",
                "body": "In this benchmark, we measured the latency and failure rate of local models. The trade-off is clear when looking at reproducible tokens per second.",
                "hook": "Here is what happens when you run coding benchmarks locally.",
                "cta": "Inspect the reproduction script linked below.",
            })

        verdicts: List[BrandQAVerdict] = []
        rejected_count = 0
        explanations: List[Dict[str, Any]] = []

        for raw in raw_inputs:
            item = BrandQAInput(**raw) if isinstance(raw, dict) else raw
            verdict = self.evaluate_item(item, brand, exemplars)
            verdicts.append(verdict)
            if not verdict.on_brand:
                rejected_count += 1

            explanations.append({
                "verdict_id": verdict.id,
                "input_id": verdict.input_id,
                "on_brand": verdict.on_brand,
                "overall_score": verdict.overall_score,
                "violations_count": len(verdict.violations),
                "matched_cliches": verdict.matched_cliches,
                "matched_avoid": verdict.matched_avoid_words,
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
            summary=f"Brand QA evaluated {len(verdicts)} draft(s): {passed_count} on-brand, {rejected_count} rejected.",
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

        status_text = "ON-BRAND" if verdict.on_brand else "BRAND VIOLATION"
        return EngineExplanation(
            result_id=result_id,
            summary=f"Verdict {result_id} is {status_text} with overall score {verdict.overall_score}/100 and {len(verdict.violations)} violation(s).",
            factors=verdict.factors,
        )
