import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.engines.core.base import (
    BaseEngine,
    EngineContext,
    EngineExplanation,
    EngineHealth,
    EngineResult,
)
from app.engines.niche_guard.contracts import NicheGuardInput
from app.engines.niche_guard.engine import NicheGuardEngine
from app.engines.rss.adapters import (
    calculate_fingerprint,
    calculate_title_similarity,
    canonicalize_url,
    fetch_feed_resilient,
    normalize_title,
    parse_feed_xml,
)
from app.engines.rss.contracts import (
    CandidateSourceInfo,
    DiscoveryCandidate,
    ParsedFeedItem,
    RssEngineExplainability,
    RssEngineRunResult,
    RssFeedHealth,
    SourceFeedInput,
)
from app.models.rss import DiscoveredCandidate as DiscoveredCandidateModel
from app.models.rss import RssFeed as RssFeedModel


class RssEngine(BaseEngine):
    """RSS Discovery Engine: Ingests, normalizes, deduplicates, groups across sources,
    filters by freshness, and evaluates against Niche Guard with zero AI calls.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        if engine_dir is None:
            engine_dir = Path(__file__).resolve().parent
        super().__init__(engine_dir=engine_dir)
        self.niche_guard = NicheGuardEngine()
        self._last_run_result: Optional[RssEngineRunResult] = None
        self._history: Dict[str, EngineResult] = {}

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("RssEngine rules cannot be empty.")
        if "network" not in self.rules:
            raise ValueError("RssEngine rules missing 'network' block.")
        if "filtering" not in self.rules:
            raise ValueError("RssEngine rules missing 'filtering' block.")
        if "deduplication" not in self.rules:
            raise ValueError("RssEngine rules missing 'deduplication' block.")

    def health(self) -> EngineHealth:
        try:
            self.validate_config()
            return EngineHealth(
                status="healthy",
                message="RssEngine is operational with valid network, filtering, and deduplication rules.",
                details={
                    "version": self.version,
                    "rules_version": self.rules_version,
                    "max_item_age_hours": self.rules.get("filtering", {}).get("max_item_age_hours", 72),
                    "title_similarity_threshold": self.rules.get("deduplication", {}).get("title_similarity_threshold", 0.82),
                },
            )
        except Exception as exc:
            return EngineHealth(
                status="failing",
                message=f"RssEngine health check failed: {str(exc)}",
                details={"error": str(exc)},
            )

    async def _load_feeds(self, context: EngineContext) -> List[SourceFeedInput]:
        """Load feeds from context or active database records."""
        # 1. Check if feeds were explicitly provided in parameters
        custom_feeds = context.parameters.get("feeds")
        if custom_feeds and isinstance(custom_feeds, list):
            return [
                SourceFeedInput(**f) if isinstance(f, dict) else f
                for f in custom_feeds
            ]

        # 2. Query from database
        feeds: List[SourceFeedInput] = []
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(RssFeedModel).where(RssFeedModel.enabled.is_(True))
                result = await session.execute(stmt)
                db_feeds = result.scalars().all()
                for f in db_feeds:
                    feeds.append(
                        SourceFeedInput(
                            id=f.id,
                            name=f.name,
                            url=f.url,
                            category=f.category,
                            trust_weight=f.trust_weight,
                            enabled=f.enabled,
                        )
                    )
        except Exception:
            pass

        return feeds

    async def _load_existing_db_candidates(self) -> List[Dict[str, Any]]:
        """Load recent candidates from DB to deduplicate across runs."""
        candidates = []
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(DiscoveredCandidateModel).order_by(
                    DiscoveredCandidateModel.created_at.desc()
                ).limit(500)
                result = await session.execute(stmt)
                for c in result.scalars().all():
                    candidates.append({
                        "id": c.id,
                        "canonical_url": c.canonical_url,
                        "title": c.title,
                        "normalized_title": c.normalized_title,
                        "summary": c.summary,
                        "content_fingerprint": c.content_fingerprint,
                        "primary_source": c.primary_source,
                        "published_at": c.published_at,
                        "first_seen_at": c.first_seen_at,
                        "last_seen_at": c.last_seen_at,
                        "source_count": c.source_count,
                        "sources": c.sources,
                        "authority_score": c.authority_score,
                        "pillar": c.pillar,
                        "niche_score": c.niche_score,
                        "is_in_niche": c.is_in_niche,
                        "status": c.status,
                    })
        except Exception:
            pass
        return candidates

    async def _execute_discovery(
        self, context: EngineContext, dry_run: bool = False
    ) -> RssEngineRunResult:
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc)

        # 1. Config rules
        net_rules = self.rules.get("network", {})
        filter_rules = self.rules.get("filtering", {})
        dedupe_rules = self.rules.get("deduplication", {})

        timeout_sec = float(net_rules.get("timeout_seconds", 10.0))
        max_retries = int(net_rules.get("max_retries", 3))
        max_age_hours = float(filter_rules.get("max_item_age_hours", 72.0))
        title_threshold = float(dedupe_rules.get("title_similarity_threshold", 0.82))

        # 2. Load feeds
        feeds = await self._load_feeds(context)

        # 3. Check for injected XML fixtures (useful for offline tests and benchmarks)
        xml_fixtures: Dict[str, str] = context.parameters.get("xml_fixtures", {})

        feeds_polled = len(feeds)
        feeds_successful = 0
        feeds_failed = 0
        items_parsed = 0
        rejected_old = 0
        rejected_off_niche = 0
        cross_source_grouped = 0

        feed_health_list: List[RssFeedHealth] = []
        raw_items: List[ParsedFeedItem] = []

        # 4. Ingest each feed with failure isolation
        for feed in feeds:
            feed_id = feed.id or str(uuid.uuid4())
            xml_content: Optional[str] = None
            error_msg: Optional[str] = None

            if feed.url in xml_fixtures or feed.name in xml_fixtures:
                xml_content = xml_fixtures.get(feed.url) or xml_fixtures.get(feed.name)
                success = True
            else:
                success, xml_content, error_msg = await fetch_feed_resilient(
                    url=feed.url,
                    timeout=timeout_sec,
                    max_retries=max_retries,
                )

            if success and xml_content:
                try:
                    parsed = parse_feed_xml(
                        xml_content=xml_content,
                        feed_source_name=feed.name,
                        feed_id=feed_id,
                        default_trust=feed.trust_weight,
                    )
                    raw_items.extend(parsed)
                    items_parsed += len(parsed)
                    feeds_successful += 1

                    feed_health_list.append(
                        RssFeedHealth(
                            feed_id=feed_id,
                            name=feed.name,
                            url=feed.url,
                            status="healthy",
                            last_success_at=now.isoformat(),
                            failure_count=0,
                        )
                    )

                    # Update database if not dry_run
                    if not dry_run and feed.id:
                        async with AsyncSessionLocal() as session:
                            db_feed = await session.get(RssFeedModel, feed.id)
                            if db_feed:
                                db_feed.last_success_at = now
                                db_feed.failure_count = 0
                                db_feed.last_error = None
                                await session.commit()
                except Exception as parse_exc:
                    feeds_failed += 1
                    error_msg = f"Parsing error: {str(parse_exc)}"
                    feed_health_list.append(
                        RssFeedHealth(
                            feed_id=feed_id,
                            name=feed.name,
                            url=feed.url,
                            status="failing",
                            last_failure_at=now.isoformat(),
                            failure_count=1,
                            last_error=error_msg,
                        )
                    )
            else:
                feeds_failed += 1
                feed_health_list.append(
                    RssFeedHealth(
                        feed_id=feed_id,
                        name=feed.name,
                        url=feed.url,
                        status="failing",
                        last_failure_at=now.isoformat(),
                        failure_count=1,
                        last_error=error_msg or "Unknown network error",
                    )
                )
                if not dry_run and feed.id:
                    async with AsyncSessionLocal() as session:
                        db_feed = await session.get(RssFeedModel, feed.id)
                        if db_feed:
                            db_feed.last_failure_at = now
                            db_feed.failure_count = (db_feed.failure_count or 0) + 1
                            db_feed.last_error = error_msg
                            await session.commit()

        # 5. Load active niche taxonomy for Niche Guard evaluation
        niche_data = await self.niche_guard._get_active_niche_data()

        # 6. Load existing candidates from DB to ensure idempotency across runs
        db_candidates = await self._load_existing_db_candidates()

        # In-memory candidate dictionary indexed by canonical_url
        candidates_by_url: Dict[str, DiscoveryCandidate] = {}
        # Also store candidate references by fingerprint and normalized title
        candidates_by_fingerprint: Dict[str, DiscoveryCandidate] = {}

        # Prepopulate with existing DB candidates
        for c in db_candidates:
            c_obj = DiscoveryCandidate(
                id=c["id"],
                canonical_url=c["canonical_url"],
                title=c["title"],
                normalized_title=c["normalized_title"],
                summary=c["summary"],
                content_fingerprint=c["content_fingerprint"],
                primary_source=c["primary_source"],
                published_at=c["published_at"],
                first_seen_at=c["first_seen_at"],
                last_seen_at=c["last_seen_at"],
                source_count=c["source_count"],
                sources=[
                    CandidateSourceInfo(**s) if isinstance(s, dict) else s
                    for s in c["sources"]
                ],
                authority_score=c["authority_score"],
                pillar=c.get("pillar"),
                niche_score=c["niche_score"],
                is_in_niche=c["is_in_niche"],
                status=c["status"],
            )
            candidates_by_url[c_obj.canonical_url] = c_obj
            candidates_by_fingerprint[c_obj.content_fingerprint] = c_obj

        # 7. Process items: Freshness, Canonical URL, Deduplication, Cross-Source Grouping, Niche Guard
        candidates_modified_or_new: List[DiscoveryCandidate] = []

        for item in raw_items:
            # Freshness check
            item_pub = item.published_at
            if item_pub.tzinfo is None:
                item_pub = item_pub.replace(tzinfo=timezone.utc)
            age_hours = (now - item_pub).total_seconds() / 3600.0
            if age_hours > max_age_hours:
                rejected_old += 1
                continue

            can_url = canonicalize_url(item.link)
            norm_title = normalize_title(item.title)
            fingerprint = calculate_fingerprint(item.title, item.summary)

            # Check for existing match:
            matched_candidate: Optional[DiscoveryCandidate] = None

            # a. Exact canonical URL match
            if can_url in candidates_by_url:
                matched_candidate = candidates_by_url[can_url]
            # b. Exact content fingerprint match
            elif fingerprint in candidates_by_fingerprint:
                matched_candidate = candidates_by_fingerprint[fingerprint]
            # c. Near-title similarity match
            else:
                for candidate in candidates_by_url.values():
                    sim = calculate_title_similarity(candidate.title, item.title)
                    if sim >= title_threshold:
                        matched_candidate = candidate
                        break

            new_source_entry = CandidateSourceInfo(
                feed_id=item.feed_id,
                feed_name=item.feed_name,
                url=item.link,
                trust_weight=item.trust_weight,
                published_at=item_pub.isoformat(),
            )

            if matched_candidate is not None:
                # Merge cross-source mention!
                existing_urls = {s.url for s in matched_candidate.sources}
                existing_feeds = {s.feed_name for s in matched_candidate.sources}

                # Only increment source_count if this is a distinct feed or URL
                if item.feed_name not in existing_feeds or item.link not in existing_urls:
                    matched_candidate.source_count += 1
                    matched_candidate.sources.append(new_source_entry)
                    # Recompute authority mix
                    total_weight = sum(s.trust_weight for s in matched_candidate.sources)
                    matched_candidate.authority_score = round(
                        total_weight / len(matched_candidate.sources), 3
                    )
                    cross_source_grouped += 1

                matched_candidate.last_seen_at = now
                if matched_candidate not in candidates_modified_or_new:
                    candidates_modified_or_new.append(matched_candidate)
            else:
                # New Candidate!
                candidate_id = str(uuid.uuid4())
                new_candidate = DiscoveryCandidate(
                    id=candidate_id,
                    canonical_url=can_url,
                    title=item.title,
                    normalized_title=norm_title,
                    summary=item.summary,
                    content_fingerprint=fingerprint,
                    primary_source=item.feed_name,
                    published_at=item_pub,
                    first_seen_at=now,
                    last_seen_at=now,
                    source_count=1,
                    sources=[new_source_entry],
                    authority_score=item.trust_weight,
                )

                # Evaluate with Niche Guard
                guard_input = NicheGuardInput(
                    title=new_candidate.title,
                    text=new_candidate.summary,
                    tags=[],
                )
                verdict = self.niche_guard.evaluate_item(guard_input, niche_data)
                new_candidate.is_in_niche = verdict.passed
                new_candidate.niche_score = verdict.score
                new_candidate.pillar = verdict.primary_pillar
                new_candidate.niche_verdict = verdict.model_dump(mode="json")

                if not verdict.passed:
                    new_candidate.status = "rejected"
                    new_candidate.rejection_reason = (
                        verdict.reason or "Rejected by Niche Guard"
                    )
                    rejected_off_niche += 1
                else:
                    new_candidate.status = "candidate"

                candidates_by_url[can_url] = new_candidate
                candidates_by_fingerprint[fingerprint] = new_candidate
                candidates_modified_or_new.append(new_candidate)

        # 8. Persist to database if not dry_run
        if not dry_run and candidates_modified_or_new:
            try:
                async with AsyncSessionLocal() as session:
                    for cand in candidates_modified_or_new:
                        # Check if already in DB
                        db_cand = await session.get(DiscoveredCandidateModel, cand.id)
                        if db_cand:
                            db_cand.source_count = cand.source_count
                            db_cand.sources = [s.model_dump(mode="json") for s in cand.sources]
                            db_cand.authority_score = cand.authority_score
                            db_cand.last_seen_at = cand.last_seen_at
                        else:
                            new_row = DiscoveredCandidateModel(
                                id=cand.id,
                                canonical_url=cand.canonical_url,
                                title=cand.title,
                                normalized_title=cand.normalized_title,
                                summary=cand.summary,
                                content_fingerprint=cand.content_fingerprint,
                                primary_source=cand.primary_source,
                                published_at=cand.published_at,
                                first_seen_at=cand.first_seen_at,
                                last_seen_at=cand.last_seen_at,
                                source_count=cand.source_count,
                                sources=[s.model_dump(mode="json") for s in cand.sources],
                                authority_score=cand.authority_score,
                                pillar=cand.pillar,
                                niche_score=cand.niche_score,
                                is_in_niche=cand.is_in_niche,
                                niche_verdict=cand.niche_verdict,
                                status=cand.status,
                                raw_data=cand.raw_data,
                            )
                            session.add(new_row)
                    await session.commit()
            except Exception:
                pass

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        rejected_off_niche = sum(1 for c in candidates_modified_or_new if c.status == "rejected")

        run_result = RssEngineRunResult(
            feeds_polled=feeds_polled,
            feeds_successful=feeds_successful,
            feeds_failed=feeds_failed,
            items_parsed=items_parsed,
            candidates_produced=len(candidates_modified_or_new),
            rejected_old=rejected_old,
            rejected_off_niche=rejected_off_niche,
            cross_source_grouped=cross_source_grouped,
            candidates=candidates_modified_or_new,
            feed_health=feed_health_list,
            duration_ms=round(duration_ms, 2),
        )

        self._last_run_result = run_result
        return run_result

    async def run(self, context: EngineContext) -> EngineResult:
        """Execute full RSS discovery run, updating database and emitting audit records."""
        start_time = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        result = await self._execute_discovery(context, dry_run=False)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        end_time = datetime.now(timezone.utc)

        explanations = [
            {
                "candidate_id": c.id,
                "title": c.title,
                "status": c.status,
                "is_in_niche": c.is_in_niche,
                "niche_score": c.niche_score,
                "pillar": c.pillar,
                "source_count": c.source_count,
                "authority_score": c.authority_score,
                "sources": [s.feed_name for s in c.sources],
                "reason": c.rejection_reason if not c.is_in_niche else "Passed Niche Guard",
            }
            for c in result.candidates
        ]
        errors = [h.last_error for h in result.feed_health if h.last_error]

        engine_result = EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            rules_version=self.rules_version,
            project_id=context.project_id,
            run_id=context.run_id,
            success=result.feeds_failed == 0,
            started_at=start_time,
            ended_at=end_time,
            duration_ms=duration_ms,
            input_count=result.items_parsed,
            output_count=result.candidates_produced,
            rejected_count=result.rejected_old + result.rejected_off_niche,
            error_count=result.feeds_failed,
            cost=0.0,
            summary=(
                f"Discovered {result.candidates_produced} candidates from {result.feeds_successful}/{result.feeds_polled} feeds "
                f"({result.cross_source_grouped} cross-source grouped, {result.rejected_off_niche} off-niche rejected, {result.rejected_old} old rejected)."
            ),
            outputs=[c.model_dump(mode="json") for c in result.candidates],
            errors=errors,
            explanations=explanations,
        )
        self._history[context.run_id] = engine_result
        return engine_result

    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Preview discovery candidate generation without writing changes to the database."""
        start_time = datetime.now(timezone.utc)
        t0 = time.perf_counter()
        result = await self._execute_discovery(context, dry_run=True)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        end_time = datetime.now(timezone.utc)

        explanations = [
            {
                "candidate_id": c.id,
                "title": c.title,
                "status": c.status,
                "is_in_niche": c.is_in_niche,
                "niche_score": c.niche_score,
                "pillar": c.pillar,
                "source_count": c.source_count,
                "authority_score": c.authority_score,
                "sources": [s.feed_name for s in c.sources],
                "reason": c.rejection_reason if not c.is_in_niche else "Passed Niche Guard",
            }
            for c in result.candidates
        ]
        errors = [h.last_error for h in result.feed_health if h.last_error]

        engine_result = EngineResult(
            engine_id=self.id,
            engine_version=self.version,
            rules_version=self.rules_version,
            project_id=context.project_id,
            run_id=context.run_id,
            success=result.feeds_failed == 0,
            started_at=start_time,
            ended_at=end_time,
            duration_ms=duration_ms,
            input_count=result.items_parsed,
            output_count=result.candidates_produced,
            rejected_count=result.rejected_old + result.rejected_off_niche,
            error_count=result.feeds_failed,
            cost=0.0,
            summary=(
                f"[DRY RUN PREVIEW] Discovered {result.candidates_produced} candidates "
                f"({result.cross_source_grouped} cross-source grouped, {result.rejected_off_niche} off-niche, {result.rejected_old} old)."
            ),
            outputs=[c.model_dump(mode="json") for c in result.candidates],
            errors=errors,
            explanations=explanations,
        )
        self._history[context.run_id] = engine_result
        return engine_result

    def explain(self, result_id: Any) -> EngineExplanation:
        """Provide detailed human explainability of discovery decisions."""
        rid = result_id.run_id if hasattr(result_id, "run_id") else str(result_id)
        cached = self._history.get(rid)

        if not cached:
            return EngineExplanation(
                result_id=rid,
                summary=f"No run record found for '{rid}'.",
                factors=[],
            )

        factors = [
            {"factor": "feeds_polled", "value": cached.input_count},
            {"factor": "candidates_produced", "value": cached.output_count},
            {"factor": "rejected_items", "value": cached.rejected_count},
            {"factor": "feeds_failed", "value": cached.error_count},
        ]

        return EngineExplanation(
            result_id=rid,
            summary=cached.summary,
            factors=factors,
        )
