import pytest
from app.engines.research.contracts import ResearchEngineInput
from app.engines.research.engine import ResearchEngine
from app.engines.research.extractor import (
    detect_contradictions,
    detect_things_not_to_claim,
    evaluate_claim_verification,
    extract_dates_and_milestones,
    extract_entities,
    extract_numbers_and_metrics,
    extract_research_packet,
)


def test_research_engine_manifest_and_health():
    engine = ResearchEngine()
    assert engine.id == "research"
    assert engine.name == "Research Engine"
    health = engine.health()
    assert health.status == "healthy"
    assert health.details["uncertainty_keywords_count"] > 0


def test_extractor_numbers_and_metrics():
    sample_text = (
        "In our benchmarks, Ollama achieved 142 tokens/s generation speed with 12ms first-token latency, "
        "representing a +180% improvement over the baseline. The machine used 32GB unified RAM on an M4 Max "
        "and reduced memory footprint by 3x, costing only $0.002 per 1k tokens."
    )
    metrics = extract_numbers_and_metrics(sample_text, "https://benchmark.local/run1")
    assert len(metrics) >= 4

    metrics_values = [m.value for m in metrics]
    assert any("tokens/s" in v or "142" in v for v in metrics_values)
    assert any("12ms" in v or "12" in v for v in metrics_values)
    assert any("+180%" in v for v in metrics_values)
    assert any("32GB" in v or "32" in v for v in metrics_values)
    assert any("3x" in v for v in metrics_values)
    assert any("$0.002" in v for v in metrics_values)


def test_extractor_dates_and_milestones():
    sample_text = (
        "The model was initially released on 2026-02-15. The official v2.0 benchmark report followed "
        "on March 12, 2026, with widespread deployment planned for Q3 2026."
    )
    dates = extract_dates_and_milestones(sample_text, "https://release.local/v2")
    assert len(dates) >= 2
    dates_found = [d.date_str for d in dates]
    assert any("2026-02-15" in d for d in dates_found)
    assert any("March 12, 2026" in d or "Q3 2026" in d for d in dates_found)


def test_extractor_entities():
    sample_text = (
        "We tested DeepSeek and Claude 3.5 Sonnet on Mac M4 Max using vLLM and FastAPI with PostgreSQL."
    )
    entities = extract_entities(sample_text, "https://tech.local/test")
    names = [e.name for e in entities]
    assert "DeepSeek" in names
    assert "M4 Max" in names or "Mac M4" in names
    assert "FastAPI" in names
    assert "PostgreSQL" in names


def test_claim_verification_classification():
    keywords = ["might", "rumored", "allegedly", "unconfirmed"]

    # 1. Direct factual statement from trusted source
    fact_sent = "The unified memory architecture allows zero-copy CPU and GPU memory access."
    status, reason, quote = evaluate_claim_verification(fact_sent, "https://apple.com/silicon", keywords)
    assert status == "source-backed"
    assert quote == fact_sent
    assert reason is None

    # 2. Speculative or hedged statement
    spec_sent = "A smaller 7B distilled version is rumored to launch next month."
    status, reason, quote = evaluate_claim_verification(spec_sent, "https://leak.local/post", keywords)
    assert status == "explicitly_uncertain"
    assert "rumored" in reason
    assert quote is None


def test_things_not_to_claim_detection():
    hype_text = (
        "This tool is 100% bug-free and completely replaces all engineers, "
        "offering zero latency and infinitely scalable throughput."
    )
    avoid_items = detect_things_not_to_claim(hype_text, "https://vendor.local/marketing")
    assert len(avoid_items) >= 3
    texts = " ".join([i.claim_text for i in avoid_items])
    assert "100% bug-free" in texts or "zero bugs" in texts
    assert "replaces" in texts
    assert "infinitely scalable" in texts or "zero latency" in texts


def test_contradiction_detection():
    from app.engines.research.contracts import NumberMetric

    num_a = NumberMetric(
        id="1",
        metric="Latency/Throughput",
        value="14ms",
        context="Source A reports 14ms latency",
        source_url="https://source-a.com",
    )
    num_b = NumberMetric(
        id="2",
        metric="Latency/Throughput",
        value="65ms",
        context="Source B reports 65ms latency under stress",
        source_url="https://source-b.com",
    )

    contradictions = detect_contradictions([], [num_a, num_b])
    assert len(contradictions) == 1
    assert contradictions[0].source_a == "https://source-a.com"
    assert contradictions[0].source_b == "https://source-b.com"
    assert "14ms" in contradictions[0].conflict_summary
    assert "65ms" in contradictions[0].conflict_summary


def test_extract_research_packet_acceptance():
    sources = [
        {
            "url": "https://source-primary.com/benchmarks",
            "title": "Local LLM Benchmarks 2026",
            "excerpt": (
                "DeepSeek on Mac M4 Max achieved 150 tokens/s with 14ms latency on 2026-03-01. "
                "This engine is infinitely scalable according to company claims. "
                "A quantized version might be released later."
            ),
            "trust_weight": 1.4,
        },
        {
            "url": "https://source-supporting.com/tests",
            "title": "Community Reproduction Tests",
            "excerpt": (
                "Community testers measured 45ms latency under sustained thermal load. "
                "Memory consumption peaked at 24GB VRAM."
            ),
            "trust_weight": 1.0,
        },
    ]

    packet = extract_research_packet(
        topic="DeepSeek Mac M4 Max Benchmark Analysis",
        sources=sources,
    )

    # Acceptance criteria checks:
    # 1. Sources separation
    assert len(packet.primary_sources) >= 1
    assert len(packet.supporting_sources) >= 1
    assert packet.primary_sources[0].url == "https://source-primary.com/benchmarks"

    # 2. Grounded metrics & facts
    assert len(packet.numbers) >= 2
    assert len(packet.dates) >= 1
    assert len(packet.entities) >= 1

    # 3. Every claim MUST be source-backed, explicitly_uncertain, or manually_entered
    assert len(packet.claims) > 0
    valid_statuses = {"source-backed", "explicitly_uncertain", "manually_entered"}
    for claim in packet.claims:
        assert claim.verification_status in valid_statuses
        if claim.verification_status == "source-backed":
            assert claim.source_url is not None
            assert claim.evidence_quote is not None
        elif claim.verification_status == "explicitly_uncertain":
            assert claim.uncertainty_reason is not None

    # 4. Things not to claim
    assert len(packet.things_not_to_claim) >= 1
    assert any("infinitely scalable" in item.claim_text for item in packet.things_not_to_claim)

    # 5. Contradictions detected (14ms vs 45ms)
    assert len(packet.contradictions) >= 1
