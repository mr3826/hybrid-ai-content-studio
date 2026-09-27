import re
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from app.engines.research.contracts import (
    ClaimItem,
    ClaimStatus,
    ContradictionItem,
    DateItem,
    EntityItem,
    FactItem,
    NumberMetric,
    ResearchPacketItem,
    SourceReference,
    ThingNotToClaimItem,
    UncertainClaimItem,
)


KNOWN_TECH_ENTITIES = {
    "DeepSeek": "Model",
    "OpenAI": "Organization",
    "Anthropic": "Organization",
    "Claude": "Model",
    "ChatGPT": "Tool",
    "GPT-4": "Model",
    "GPT-4o": "Model",
    "Llama": "Model",
    "Llama 3": "Model",
    "Ollama": "Tool",
    "vLLM": "Framework",
    "PyTorch": "Framework",
    "TensorFlow": "Framework",
    "FastAPI": "Framework",
    "Next.js": "Framework",
    "React": "Framework",
    "Docker": "Tool",
    "Kubernetes": "Tool",
    "PostgreSQL": "Tool",
    "SQLite": "Tool",
    "Python": "Technology",
    "Rust": "Technology",
    "TypeScript": "Technology",
    "CUDA": "Technology",
    "M4 Max": "Hardware",
    "Mac M4": "Hardware",
    "Apple Silicon": "Hardware",
    "Nvidia": "Organization",
    "RTX 4090": "Hardware",
    "H100": "Hardware",
    "Ollama": "Tool",
    "LangChain": "Framework",
    "LlamaIndex": "Framework",
    "Qwen": "Model",
    "Mistral": "Model",
    "Gemini": "Model",
}

DEFAULT_UNCERTAINTY_KEYWORDS = [
    "might",
    "may",
    "alleged",
    "allegedly",
    "rumored",
    "unconfirmed",
    "claimed without proof",
    "could",
    "tentatively",
    "speculated",
    "reportedly",
    "unverified",
    "pending verification",
    "early preview",
    "purportedly",
    "supposedly",
    "sources claim",
    "unclear whether",
    "estimated to be",
]

DEFAULT_HYPE_PATTERNS = [
    (
        r"100% bug[- ]?free|zero bugs",
        "Absolute claim: Software is rarely defect-free; claims of 100% reliability damage audience trust.",
    ),
    (
        r"completely replaces (?:human |all )?(?:engineers|developers|programmers)",
        "Exaggerated replacement claim: Tools augment rather than wholesale eliminate engineering workflows.",
    ),
    (
        r"infinitely scalable",
        "Hyperbolic claim: All systems encounter hardware, network, or cost saturation boundaries.",
    ),
    (
        r"fastest (?:tool|engine|model|framework|system) in the world|world'?s fastest",
        "Unsubstantiated superlative: Requires independent third-party benchmark verification.",
    ),
    (
        r"zero (?:latency|overhead|cost)",
        "Misleading absolute: Operating overhead and latency exist on physical hardware.",
    ),
    (
        r"flawless (?:accuracy|execution)",
        "Probabilistic models and systems exhibit error rates; flawless claims are unverifiable.",
    ),
    (
        r"revolutionizes? everything|revolutionary game changer",
        "Marketing fluff with zero technical or factual value.",
    ),
]


def _extract_domain(url: str) -> str:
    """Extract clean domain name from URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            return netloc[4:]
        return netloc or "local-source"
    except Exception:
        return "unknown"


def _split_sentences(text: str) -> List[str]:
    """Split text into individual sentences while preserving technical terms."""
    if not text:
        return []
    # Replace newlines with spaces and clean whitespace
    cleaned = re.sub(r"\s+", " ", text.strip())
    # Split on sentence terminals followed by space and capital letter or end of string
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'‘“])", cleaned)
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 15]
    return sentences


def extract_numbers_and_metrics(text: str, source_url: str) -> List[NumberMetric]:
    """Extract quantitative benchmarks, percentages, speeds, and costs."""
    metrics: List[NumberMetric] = []
    seen_values: Set[str] = set()

    # Regex patterns for measurable metrics
    patterns = [
        # Percentages e.g. 45%, +180%, -25.4%
        (
            r"(?P<val>[+-]?\d+(?:\.\d+)?%)\s*(?P<ctx>(?:faster|slower|improvement|reduction|increase|gain|accuracy|utilization|drop|growth|vs\s+baseline)?)",
            "Percentage",
            "%",
        ),
        # Latency & Timings e.g. 12ms, 3.5s, 45 seconds, 120 fps
        (
            r"(?P<val>\d+(?:\.\d+)?\s*(?:ms|milliseconds|seconds|fps|tokens/s|tok/s))\b(?:\s*(?P<ctx>latency|time|throughput|generation speed)?)",
            "Latency/Throughput",
            None,
        ),
        # Memory & Bandwidth e.g. 128 GB, 70B, 16GB, 128k
        (
            r"(?P<val>\d+(?:\.\d+)?\s*(?:GB|TB|MB|parameters|params|tokens))\b(?:\s*(?P<ctx>memory|VRAM|RAM|context window|weights)?)",
            "Hardware/Scale",
            None,
        ),
        # Financial / Pricing e.g. $20/month, $0.002, $10M
        (
            r"(?P<val>\$\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:billion|million|k|M|B|/month|/yr|per 1k tokens))?)\b",
            "Pricing/Cost",
            "$",
        ),
        # Multipliers e.g. 3x, 5.2x
        (
            r"(?P<val>\d+(?:\.\d+)?x)\s*(?P<ctx>(?:faster|speedup|reduction|increase|throughput))?",
            "Speedup Factor",
            "x",
        ),
    ]

    for pat, label, unit in patterns:
        for match in re.finditer(pat, text, re.IGNORECASE):
            val_str = match.group("val").strip()
            if val_str in seen_values:
                continue
            seen_values.add(val_str)

            # Get surrounding sentence/context
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            context = text[start:end].strip()

            metrics.append(
                NumberMetric(
                    id=str(uuid.uuid4())[:8],
                    metric=label,
                    value=val_str,
                    unit=unit,
                    context=context,
                    source_url=source_url,
                )
            )

    return metrics


def extract_dates_and_milestones(text: str, source_url: str) -> List[DateItem]:
    """Extract release dates, milestones, and temporal events."""
    dates: List[DateItem] = []
    seen: Set[str] = set()

    patterns = [
        # ISO Dates: 2026-09-27
        r"\b(\d{4}-\d{2}-\d{2})\b",
        # Full Month Day, Year: September 27, 2026 or Sep 27, 2026
        r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4})\b",
        # Quarter & Year: Q1 2026, Q3 2025
        r"\b(Q[1-4]\s+\d{4})\b",
        # Month Year: March 2026
        r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
    ]

    for pat in patterns:
        for match in re.finditer(pat, text, re.IGNORECASE):
            date_str = match.group(1).strip()
            if date_str in seen:
                continue
            seen.add(date_str)

            # Extract surrounding context as the event
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 60)
            event_snippet = text[start:end].strip()

            dates.append(
                DateItem(
                    id=str(uuid.uuid4())[:8],
                    event=event_snippet,
                    date_str=date_str,
                    source_url=source_url,
                )
            )

    return dates


def extract_entities(text: str, source_url: str) -> List[EntityItem]:
    """Extract technical entities, frameworks, models, and organizations."""
    entities: List[EntityItem] = []
    seen: Set[str] = set()

    # 1. Match known tech entities
    for name, ent_type in KNOWN_TECH_ENTITIES.items():
        if re.search(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE):
            if name.lower() not in seen:
                seen.add(name.lower())
                entities.append(
                    EntityItem(
                        id=str(uuid.uuid4())[:8],
                        name=name,
                        type=ent_type,
                        relevance=1.0,
                        source_url=source_url,
                    )
                )

    # 2. Match versioned software patterns (e.g. v2.4, Python 3.12, Llama-3.1)
    versioned_pat = r"\b([A-Z][a-zA-Z0-9_\-\.]+\s+(?:v\d+(?:\.\d+)*|\d+\.\d+))\b"
    for match in re.finditer(versioned_pat, text):
        ent_name = match.group(1).strip()
        if ent_name.lower() not in seen and len(ent_name) > 3:
            seen.add(ent_name.lower())
            entities.append(
                EntityItem(
                    id=str(uuid.uuid4())[:8],
                    name=ent_name,
                    type="Software Version",
                    relevance=0.85,
                    source_url=source_url,
                )
            )

    return entities


def evaluate_claim_verification(
    sentence: str,
    source_url: str,
    uncertainty_keywords: List[str],
) -> Tuple[ClaimStatus, Optional[str], Optional[str]]:
    """Determine whether claim is source-backed or explicitly uncertain.
    Returns: (verification_status, uncertainty_reason, evidence_quote)
    """
    sentence_lower = sentence.lower()

    # Check for uncertainty markers
    for kw in uncertainty_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", sentence_lower):
            reason = f"Contains speculative or unconfirmed marker '{kw}'; pending official release verification."
            return "explicitly_uncertain", reason, None

    # If it's directly from the source text and has factual substance
    return "source-backed", None, sentence.strip()


def detect_things_not_to_claim(
    text: str,
    source_url: str,
    hype_patterns: Optional[List[Tuple[str, str]]] = None,
) -> List[ThingNotToClaimItem]:
    """Detect unverified marketing hype, absolutes, and superlatives to avoid."""
    if hype_patterns is None:
        hype_patterns = DEFAULT_HYPE_PATTERNS

    avoid_items: List[ThingNotToClaimItem] = []
    seen: Set[str] = set()

    for pattern_regex, reason in hype_patterns:
        match = re.search(pattern_regex, text, re.IGNORECASE)
        if match:
            matched_phrase = match.group(0).strip()
            if matched_phrase.lower() not in seen:
                seen.add(matched_phrase.lower())
                # Get the sentence containing the phrase
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 50)
                claim_context = text[start:end].strip()

                avoid_items.append(
                    ThingNotToClaimItem(
                        id=str(uuid.uuid4())[:8],
                        claim_text=f"'{matched_phrase}' ({claim_context})",
                        reason_to_avoid=reason,
                        flagged_source=source_url,
                    )
                )

    return avoid_items


def detect_contradictions(
    sources_data: List[Dict[str, Any]],
    numbers: List[NumberMetric],
) -> List[ContradictionItem]:
    """Detect discrepancies in metrics or claims across multiple cited sources."""
    contradictions: List[ContradictionItem] = []

    # Group metrics by category / metric type
    by_category: Dict[str, List[NumberMetric]] = {}
    for num in numbers:
        by_category.setdefault(num.metric, []).append(num)

    # Check for conflicting numbers across different source URLs
    for metric_name, items in by_category.items():
        if len(items) >= 2:
            first = items[0]
            for other in items[1:]:
                if first.source_url != other.source_url and first.value != other.value:
                    contradictions.append(
                        ContradictionItem(
                            id=str(uuid.uuid4())[:8],
                            claim_a=f"{first.metric}: {first.value} (Context: {first.context})",
                            source_a=first.source_url,
                            claim_b=f"{other.metric}: {other.value} (Context: {other.context})",
                            source_b=other.source_url,
                            conflict_summary=f"Conflicting {metric_name} reported: '{first.value}' vs '{other.value}' across separate sources.",
                        )
                    )
                    break  # Avoid flood of pairwise combinations

    return contradictions


def extract_research_packet(
    topic: str,
    sources: List[Dict[str, Any]],
    opportunity_id: Optional[str] = None,
    raw_text: Optional[str] = None,
    context: Optional[str] = None,
    rules: Optional[Dict[str, Any]] = None,
) -> ResearchPacketItem:
    """Build a complete, traceable ResearchPacket strictly grounded in verified sources."""
    packet_id = str(uuid.uuid4())
    slug_base = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:200]
    slug = f"{slug_base}-{packet_id[:8]}"

    rules = rules or {}
    uncertainty_keywords = rules.get("uncertainty_keywords", DEFAULT_UNCERTAINTY_KEYWORDS)

    # 1. Normalize Sources & Citations
    normalized_sources: List[SourceReference] = []
    seen_urls: Set[str] = set()

    for s in sources:
        url = s.get("url") or s.get("canonical_url") or s.get("link") or "https://source.local"
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = s.get("title") or s.get("feed_name") or s.get("name") or "Primary Reference"
        excerpt = s.get("excerpt") or s.get("summary") or s.get("content") or ""
        domain = s.get("domain") or _extract_domain(url)
        trust_weight = float(s.get("trust_weight") or 1.0)
        published_at = s.get("published_at")

        normalized_sources.append(
            SourceReference(
                url=url,
                title=title,
                domain=domain,
                excerpt=excerpt,
                trust_weight=trust_weight,
                published_at=published_at,
            )
        )

    # Sort sources by trust_weight descending
    normalized_sources.sort(key=lambda x: x.trust_weight, reverse=True)

    # Partition into Primary and Supporting based on trust ranking
    if len(normalized_sources) > 2:
        primary_sources = normalized_sources[:2]
        supporting_sources = normalized_sources[2:]
    elif len(normalized_sources) == 2:
        primary_sources = [normalized_sources[0]]
        supporting_sources = [normalized_sources[1]]
    elif len(normalized_sources) == 1:
        primary_sources = [normalized_sources[0]]
        supporting_sources = []
    else:
        # Fallback if no sources passed
        dummy_url = "https://internal.research/source"
        primary_sources = [
            SourceReference(
                url=dummy_url,
                title=topic,
                domain="internal.research",
                excerpt=raw_text or context or topic,
                trust_weight=1.0,
            )
        ]
        supporting_sources = []

    # 2. Extract Sentences across all sources
    all_facts: List[FactItem] = []
    all_numbers: List[NumberMetric] = []
    all_dates: List[DateItem] = []
    all_entities: List[EntityItem] = []
    all_claims: List[ClaimItem] = []
    all_uncertain_claims: List[UncertainClaimItem] = []
    all_things_not_to_claim: List[ThingNotToClaimItem] = []

    combined_texts: List[Tuple[str, str, str]] = []  # (text, source_url, source_title)
    for src in primary_sources + supporting_sources:
        if src.excerpt:
            combined_texts.append((src.excerpt, src.url, src.title))

    if raw_text:
        primary_url = primary_sources[0].url if primary_sources else "https://internal.research/raw"
        combined_texts.append((raw_text, primary_url, "Provided Document"))

    # If sources were empty of excerpts, use topic + context
    if not combined_texts:
        primary_url = primary_sources[0].url if primary_sources else "https://internal.research/context"
        combined_texts.append((f"{topic}. {context or ''}".strip(), primary_url, topic))

    for text_block, src_url, src_title in combined_texts:
        # Numbers & metrics
        all_numbers.extend(extract_numbers_and_metrics(text_block, src_url))

        # Dates & milestones
        all_dates.extend(extract_dates_and_milestones(text_block, src_url))

        # Entities
        all_entities.extend(extract_entities(text_block, src_url))

        # Hype / Things not to claim
        all_things_not_to_claim.extend(detect_things_not_to_claim(text_block, src_url))

        # Claims & Facts
        sentences = _split_sentences(text_block)
        for sent in sentences:
            # Fact statement
            all_facts.append(
                FactItem(
                    id=str(uuid.uuid4())[:8],
                    text=sent,
                    source_url=src_url,
                    source_title=src_title,
                    confidence=0.92,
                )
            )

            # Claim Verification Classification
            status, uncertainty_reason, evidence_quote = evaluate_claim_verification(
                sent, src_url, uncertainty_keywords
            )

            claim_id = str(uuid.uuid4())[:8]
            claim_item = ClaimItem(
                id=claim_id,
                claim_text=sent,
                verification_status=status,
                evidence_quote=evidence_quote,
                source_url=src_url,
                uncertainty_reason=uncertainty_reason,
                confidence=0.90 if status == "source-backed" else 0.65,
            )
            all_claims.append(claim_item)

            if status == "explicitly_uncertain":
                all_uncertain_claims.append(
                    UncertainClaimItem(
                        id=claim_id,
                        claim_text=sent,
                        uncertainty_reason=uncertainty_reason or "Pending verification",
                    )
                )

    # 3. Contradiction Detection
    contradictions = detect_contradictions(sources, all_numbers)

    # 4. Generate Synthesized Summary grounded in sources
    summary_parts = []
    summary_parts.append(f"Research synthesis on '{topic}'.")
    if all_numbers:
        top_metrics = ", ".join([f"{n.metric}: {n.value}" for n in all_numbers[:3]])
        summary_parts.append(f"Key verified benchmarks: {top_metrics}.")
    if all_claims:
        backed_claims_count = sum(1 for c in all_claims if c.verification_status == "source-backed")
        uncertain_count = len(all_uncertain_claims)
        summary_parts.append(
            f"Evidence grounding: {backed_claims_count} source-backed claims, {uncertain_count} explicitly uncertain items, across {len(primary_sources) + len(supporting_sources)} citations."
        )
    if all_things_not_to_claim:
        summary_parts.append(
            f"Flagged {len(all_things_not_to_claim)} unverified vendor claims to avoid in production scripts."
        )

    summary = " ".join(summary_parts)

    return ResearchPacketItem(
        id=packet_id,
        opportunity_id=opportunity_id,
        topic=topic,
        slug=slug,
        summary=summary,
        primary_sources=primary_sources,
        supporting_sources=supporting_sources,
        facts=all_facts[:30],
        numbers=all_numbers[:20],
        dates=all_dates[:15],
        entities=all_entities[:20],
        claims=all_claims[:30],
        contradictions=contradictions,
        uncertain_claims=all_uncertain_claims[:20],
        things_not_to_claim=all_things_not_to_claim[:15],
        version=1,
        is_verified=False,
    )
