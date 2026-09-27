import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.engines.trends.adapters.base import BaseSignalAdapter
from app.engines.trends.contracts import TopicSignal
from app.models.rss import DiscoveredCandidate

STOPWORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers",
    "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've",
    "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me",
    "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
    "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
    "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
    "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
    "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while",
    "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't",
    "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    "new", "latest", "first", "says", "said", "one", "two", "top", "best", "now", "today",
    "week", "month", "year", "post", "blog", "via", "report", "reports", "announced", "launches"
}


def extract_entities_and_keywords(text: str, max_keywords: int = 6) -> List[str]:
    """Extract prominent entities (proper nouns / capitalized phrases) and salient keywords
    deterministically without external paid NLP services.
    """
    if not text:
        return []

    # 1. Capture proper noun phrases (e.g. "DeepMind", "Gemini 2.5", "TypeScript", "NVIDIA RTX")
    proper_nouns = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b', text)
    cleaned_entities = []
    for pn in proper_nouns:
        pn_lower = pn.lower()
        if pn_lower not in STOPWORDS and len(pn) > 2 and not pn.isdigit():
            cleaned_entities.append(pn)

    # 2. Extract frequency distribution of non-stopword content words
    words = re.findall(r'\b[a-zA-Z0-9_\-]{3,}\b', text.lower())
    content_words = [w for w in words if w not in STOPWORDS and not w.isdigit()]

    # 3. Bigrams (two consecutive content words e.g. "quantum computing", "neural network")
    bigrams = []
    for i in range(len(content_words) - 1):
        bigram = f"{content_words[i]} {content_words[i+1]}"
        bigrams.append(bigram)

    # Count frequencies
    counts: Dict[str, int] = {}
    for ent in cleaned_entities:
        ent_key = ent.lower()
        counts[ent_key] = counts.get(ent_key, 0) + 3  # Bonus weight for capitalized entities

    for w in content_words:
        counts[w] = counts.get(w, 0) + 1

    for bg in bigrams:
        counts[bg] = counts.get(bg, 0) + 2

    # Sort descending by count and length
    sorted_items = sorted(counts.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)

    result: List[str] = []
    seen: Set[str] = set()

    for term, _ in sorted_items:
        # Avoid near-substring duplicates e.g. "quantum" if "quantum computing" is chosen
        if any(term in s or s in term for s in seen):
            continue
        seen.add(term)
        result.append(term)
        if len(result) >= max_keywords:
            break

    return result


class RssSignalAdapter(BaseSignalAdapter):
    """Derives trend topic signals from verified discovered candidate items."""

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session

    @property
    def source_type(self) -> str:
        return "rss"

    async def fetch_signals(self, window_hours: int = 72) -> List[TopicSignal]:
        """Fetch in-niche candidates published within window_hours and convert to TopicSignals."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        if self._session is not None:
            return await self._fetch_from_session(self._session, cutoff)

        async with AsyncSessionLocal() as session:
            return await self._fetch_from_session(session, cutoff)

    async def _fetch_from_session(self, session: AsyncSession, cutoff: datetime) -> List[TopicSignal]:
        stmt = (
            select(DiscoveredCandidate)
            .where(
                DiscoveredCandidate.is_in_niche.is_(True),
                DiscoveredCandidate.published_at >= cutoff,
            )
            .order_by(DiscoveredCandidate.published_at.desc())
        )
        res = await session.execute(stmt)
        candidates = list(res.scalars().all())
        return self.convert_candidates_to_signals(candidates)

    def convert_candidates_to_signals(self, candidates: List[DiscoveredCandidate]) -> List[TopicSignal]:
        signals: List[TopicSignal] = []

        for cand in candidates:
            entities = extract_entities_and_keywords(f"{cand.title} {cand.summary}")

            # If candidate was aggregated across multiple feeds, emit a signal for each source
            sources_list = cand.sources if cand.sources else [
                {
                    "feed_name": cand.primary_source,
                    "url": cand.canonical_url,
                    "trust_weight": cand.authority_score,
                    "published_at": cand.published_at.isoformat(),
                }
            ]

            for s_idx, src in enumerate(sources_list):
                feed_name = src.get("feed_name") or cand.primary_source
                url = src.get("url") or cand.canonical_url
                trust = float(src.get("trust_weight", cand.authority_score))
                pub_raw = src.get("published_at")
                if pub_raw:
                    try:
                        pub_time = datetime.fromisoformat(pub_raw)
                    except Exception:
                        pub_time = cand.published_at
                else:
                    pub_time = cand.published_at

                signal = TopicSignal(
                    signal_id=f"{cand.id}_src_{s_idx}",
                    source_type="rss",
                    source_name=feed_name,
                    title=cand.title,
                    url=url,
                    summary=cand.summary,
                    published_at=pub_time,
                    entities=entities,
                    pillar=cand.pillar,
                    trust_weight=trust,
                    is_in_niche=cand.is_in_niche,
                    metadata={
                        "candidate_id": cand.id,
                        "content_fingerprint": cand.content_fingerprint,
                        "authority_score": cand.authority_score,
                    },
                )
                signals.append(signal)

        return signals
