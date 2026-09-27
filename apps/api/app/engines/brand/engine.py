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
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Fetch active singleton BrandProfile, exemplars, and brand memory from SQLite, or fallback."""
        if override:
            return (
                override.get("profile", override),
                override.get("exemplars", []),
                override.get("memory", []),
            )

        profile_data: Optional[Dict[str, Any]] = None
        exemplars_data: List[Dict[str, Any]] = []
        memory_data: List[Dict[str, Any]] = []

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
                        "default_lead_magnet": brand.default_lead_magnet or "",
                        "newsletter_cta": brand.newsletter_cta or "",
                        "digital_product_cta": brand.digital_product_cta or "",
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

                from app.models.brand import BrandMemoryItem
                mem_stmt = select(BrandMemoryItem).order_by(BrandMemoryItem.last_used_at.desc())
                mem_res = await session.execute(mem_stmt)
                for mem in mem_res.scalars().all():
                    memory_data.append({
                        "id": mem.id,
                        "memory_type": mem.memory_type,
                        "content": mem.content,
                        "usage_count": mem.usage_count,
                        "last_used_at": mem.last_used_at.isoformat() if mem.last_used_at else None,
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
                "default_lead_magnet": "",
                "newsletter_cta": "",
                "digital_product_cta": "",
            }

        return profile_data, exemplars_data, memory_data

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
        memory: Optional[List[Dict[str, Any]]] = None,
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
        repetition_warnings: List[str] = []
        matched_memory_items: List[Dict[str, Any]] = []

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

        # 3. Tone & Hype Analysis (Dimension: Tone)
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

        # Check tone drift (emotional/aggressive hyperbole)
        tone_drift_keywords = ["destroy", "crush", "insane", "crazy", "stupid", "magic", "miracle"]
        matched_drift = [k for k in tone_drift_keywords if self._match_term(k, corpus)]
        if matched_drift:
            tone_score = max(0.0, tone_score - (len(matched_drift) * 15.0))
            violations.append(BrandViolation(
                rule_type="tone_drift",
                severity="warning",
                matched_phrase=", ".join(matched_drift),
                message=f"Tone drift detected: emotional/hyperbolic phrasing '{', '.join(matched_drift)}' violates calm, evidence-driven policy.",
                suggestion="Replace emotional hype with objective, measurable technical observations.",
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

        # 5. Redundancy & Repetition Check (Dimension: Repetition)
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

        # Persistent Brand Memory Repetition Lookups
        if memory:
            # A. Hook pattern repetition
            if item.hook:
                hook_clean = item.hook.strip().lower()
                hook_tokens = set(re.findall(r"\b\w+\b", hook_clean))
                for m in memory:
                    if m.get("memory_type") == "hook":
                        m_content = m.get("content", "").strip().lower()
                        mem_tokens = set(re.findall(r"\b\w+\b", m_content))
                        overlap = len(hook_tokens.intersection(mem_tokens))
                        similarity = overlap / max(1, len(hook_tokens))
                        if similarity >= 0.7 or hook_clean == m_content:
                            count = m.get("usage_count", 1)
                            warn = f"Hook pattern matches previously used hook (used {count}x): '{m.get('content', '')[:60]}'"
                            repetition_warnings.append(warn)
                            repetition_score = max(0.0, repetition_score - min(30.0, count * 10.0))
                            matched_memory_items.append(m)
                            violations.append(BrandViolation(
                                rule_type="hook_repetition",
                                severity="warning",
                                matched_phrase=item.hook,
                                message=warn,
                                suggestion="Rotate hook angle: lead with an unexpected benchmark anomaly, failure rate, or cost comparison.",
                            ))
                            break

            # B. Topic recency
            for m in memory:
                if m.get("memory_type") == "topic":
                    m_content = m.get("content", "").strip()
                    if m_content and self._match_term(m_content, corpus):
                        count = m.get("usage_count", 1)
                        warn = f"Topic '{m_content}' was covered recently (usage: {count}x)."
                        repetition_warnings.append(warn)
                        matched_memory_items.append(m)
                        if count >= 3:
                            repetition_score = max(0.0, repetition_score - 10.0)
                            violations.append(BrandViolation(
                                rule_type="topic_recency",
                                severity="warning",
                                matched_phrase=m_content,
                                message=warn,
                                suggestion="Consider an adjacent topic or fresh angle rather than retreading the same subject.",
                            ))

            # C. CTA repetition
            if item.cta:
                for m in memory:
                    if m.get("memory_type") == "cta":
                        m_content = m.get("content", "").strip()
                        if m_content and self._match_term(m_content, item.cta):
                            count = m.get("usage_count", 1)
                            if count >= 3:
                                warn = f"CTA pattern '{item.cta[:40]}' has been used {count}x; consider rotating."
                                repetition_warnings.append(warn)
                                repetition_score = max(0.0, repetition_score - 10.0)
                                matched_memory_items.append(m)
                                break

            # D. Conclusion repetition
            for m in memory:
                if m.get("memory_type") == "conclusion":
                    m_content = m.get("content", "").strip()
                    if m_content and self._match_term(m_content, corpus):
                        count = m.get("usage_count", 1)
                        warn = f"Conclusion structure matches previously used conclusion (used {count}x)."
                        repetition_warnings.append(warn)
                        repetition_score = max(0.0, repetition_score - 10.0)
                        matched_memory_items.append(m)
                        break

        factors.append({
            "dimension": "repetition",
            "score": repetition_score,
            "repetition_warnings": repetition_warnings,
            "matched_memory_count": len(matched_memory_items),
        })

        # 6. Audience Fit (Dimension: Audience Fit)
        aud_text = brand.get("audience", "")
        aud_keywords = [w.lower() for w in re.findall(r"\b\w+\b", aud_text) if len(w) > 4]
        matched_aud = [k for k in aud_keywords if k in corpus]
        aud_score = 75.0
        if matched_aud:
            aud_score = min(100.0, 75.0 + len(matched_aud) * 8.0)

        # Incompatible novice/get-rich phrasing check
        novice_signals = ["for complete beginners", "no coding required", "no technical knowledge", "anyone can do it in 2 minutes"]
        for ns in novice_signals:
            if ns in corpus:
                aud_score = max(0.0, aud_score - 25.0)
                violations.append(BrandViolation(
                    rule_type="audience_mismatch",
                    severity="warning",
                    matched_phrase=ns,
                    message="Audience mismatch: Low-friction hype phrasing violates target audience standards (technical builders).",
                    suggestion="Frame concepts around architectural tradeoffs and developer workflow.",
                ))
        audience_fit_score = round(aud_score, 1)
        factors.append({
            "dimension": "audience_fit",
            "score": audience_fit_score,
            "matched_keywords": matched_aud,
        })

        # 7. CTA Fit (Dimension: CTA Fit)
        cta_score = 85.0
        if item.cta:
            # Check configured monetization CTAs
            known_ctas = [
                brand.get("default_lead_magnet", ""),
                brand.get("newsletter_cta", ""),
                brand.get("digital_product_cta", ""),
            ]
            if any(k and (k.lower() in item.cta.lower() or item.cta.lower() in k.lower()) for k in known_ctas):
                cta_score = 100.0

            # Hype / Urgency pressure check
            pressure_words = ["buy now", "last chance", "don't miss out", "before it's gone", "hurry"]
            for pw in pressure_words:
                if pw in item.cta.lower():
                    cta_score = max(0.0, cta_score - 25.0)
                    violations.append(BrandViolation(
                        rule_type="cta_hype",
                        severity="warning",
                        matched_phrase=pw,
                        message="High-pressure conversion wording violates calm, educational CTA policy.",
                        suggestion="Use a direct, low-friction educational invitation (e.g. check reproduction notebook).",
                    ))
        cta_fit_score = round(cta_score, 1)
        factors.append({
            "dimension": "cta_fit",
            "score": cta_fit_score,
        })

        # 8. Platform Fit (Dimension: Platform Fit)
        plat_score = 90.0
        if item.platform in ["youtube_shorts", "tiktok"]:
            if not item.hook:
                plat_score = max(0.0, plat_score - 25.0)
                violations.append(BrandViolation(
                    rule_type="missing_hook",
                    severity="warning",
                    matched_phrase="",
                    message="Short-form video drafts require an explicit opening hook in the first sentence.",
                    suggestion="Add a punchy opening hook (e.g. state benchmark or test setup).",
                ))
            word_count = len(combined_text.split())
            if word_count > 320:
                plat_score = max(0.0, plat_score - 20.0)
                violations.append(BrandViolation(
                    rule_type="platform_duration_exceeded",
                    severity="warning",
                    matched_phrase=f"{word_count} words",
                    message=f"Draft word count ({word_count} words) exceeds recommended 60-second pacing (150-240 words).",
                    suggestion="Trim draft to under 240 words for short-form format.",
                ))
        platform_fit_score = round(plat_score, 1)
        factors.append({
            "dimension": "platform_fit",
            "score": platform_fit_score,
            "platform": item.platform,
        })

        # 9. Approved Exemplar Search
        exemplar_matches: List[Dict[str, Any]] = []
        for ex in exemplars:
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

        # 10. The 6 Formal QA Dimensions & Overall Adherence Score
        dimensions = {
            "Tone": tone_score,
            "Vocabulary": vocab_score,
            "Repetition": repetition_score,
            "Audience Fit": audience_fit_score,
            "CTA Fit": cta_fit_score,
            "Platform Fit": platform_fit_score,
        }

        overall_score = round(
            (tone_score * 0.20)
            + (vocab_score * 0.25)
            + (repetition_score * 0.15)
            + (audience_fit_score * 0.15)
            + (cta_fit_score * 0.10)
            + (platform_fit_score * 0.15),
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
            repetition_score=repetition_score,
            audience_fit_score=audience_fit_score,
            cta_fit_score=cta_fit_score,
            platform_fit_score=platform_fit_score,
            dimensions=dimensions,
            cliche_score=cliche_score,
            claim_score=claim_score,
            repetition_warnings=repetition_warnings,
            matched_memory_items=matched_memory_items,
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
        brand, exemplars, memory = await self._get_brand_data(brand_override)

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
            verdict = self.evaluate_item(item, brand, exemplars, memory)
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
