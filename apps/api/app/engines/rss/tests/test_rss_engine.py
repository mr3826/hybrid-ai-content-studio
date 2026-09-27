import email.utils
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import pytest

from app.engines.core.base import EngineContext
from app.engines.rss.adapters import (
    calculate_fingerprint,
    calculate_title_similarity,
    canonicalize_url,
    normalize_title,
    parse_feed_xml,
)
from app.engines.rss.contracts import SourceFeedInput
from app.engines.rss.engine import RssEngine


def _generate_rss_xml(items: List[Dict[str, str]]) -> str:
    """Helper to generate standard RSS 2.0 XML string."""
    items_xml = ""
    for item in items:
        pub = item.get("pub_date", email.utils.format_datetime(datetime.now(timezone.utc)))
        items_xml += f"""
        <item>
            <title>{item.get('title', '')}</title>
            <link>{item.get('link', '')}</link>
            <description>{item.get('summary', '')}</description>
            <pubDate>{pub}</pubDate>
            <guid>{item.get('guid', item.get('link', ''))}</guid>
        </item>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test RSS Channel</title>
            <link>https://example.com/feed</link>
            <description>Test Description</description>
            {items_xml}
        </channel>
    </rss>"""


def _generate_atom_xml(entries: List[Dict[str, str]]) -> str:
    """Helper to generate standard Atom 1.0 XML string."""
    entries_xml = ""
    for entry in entries:
        pub = entry.get("pub_date", datetime.now(timezone.utc).isoformat())
        entries_xml += f"""
        <entry>
            <title>{entry.get('title', '')}</title>
            <link rel="alternate" href="{entry.get('link', '')}"/>
            <id>{entry.get('guid', entry.get('link', ''))}</id>
            <updated>{pub}</updated>
            <summary>{entry.get('summary', '')}</summary>
        </entry>"""
    return f"""<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <title>Test Atom Feed</title>
        <link href="https://example.com/atom"/>
        <updated>{datetime.now(timezone.utc).isoformat()}</updated>
        {entries_xml}
    </feed>"""


def test_url_canonicalization():
    raw_url = "https://example.com/posts/ai-agent-benchmark/?utm_source=twitter&utm_medium=social&fbclid=12345&v=1#heading-2"
    expected = "https://example.com/posts/ai-agent-benchmark?v=1"
    canon = canonicalize_url(raw_url)
    assert canon == expected
    assert "utm_source" not in canon
    assert "fbclid" not in canon
    assert "#heading-2" not in canon


def test_title_normalization_and_similarity():
    t1 = "  Show HN: An Open-Source Coding Agent with vLLM Support! &amp; Benchmarks  "
    norm = normalize_title(t1)
    assert norm == "show hn an open source coding agent with vllm support benchmarks"

    t2 = "Show HN: An Open-Source Coding Agent with vLLM Support & Benchmarks"
    sim = calculate_title_similarity(t1, t2)
    assert sim >= 0.85

    t3 = "Completely Unrelated Weather Report For Tomorrow"
    assert calculate_title_similarity(t1, t3) == 0.0


def test_rss_and_atom_xml_parsers():
    now = datetime.now(timezone.utc)
    rss_items = [
        {
            "title": "Local LLM Fine-Tuning Guide",
            "link": "https://tech.example.com/llm-guide?ref=feed",
            "summary": "<p>Comprehensive guide to fine-tuning Llama 3 on local RTX GPUs.</p>",
            "pub_date": email.utils.format_datetime(now),
        }
    ]
    parsed_rss = parse_feed_xml(
        _generate_rss_xml(rss_items), feed_source_name="TechDaily", default_trust=0.9
    )
    assert len(parsed_rss) == 1
    assert parsed_rss[0].title == "Local LLM Fine-Tuning Guide"
    assert "Comprehensive guide" in parsed_rss[0].summary
    assert parsed_rss[0].trust_weight == 0.9

    atom_items = [
        {
            "title": "Benchmarking Coding Agents in 2026",
            "link": "https://research.example.org/benchmarks/agents",
            "summary": "Comparing autonomous agents on real-world repositories.",
            "pub_date": now.isoformat(),
        }
    ]
    parsed_atom = parse_feed_xml(
        _generate_atom_xml(atom_items), feed_source_name="AI Research", default_trust=0.95
    )
    assert len(parsed_atom) == 1
    assert parsed_atom[0].title == "Benchmarking Coding Agents in 2026"
    assert parsed_atom[0].link == "https://research.example.org/benchmarks/agents"


@pytest.mark.asyncio
async def test_rss_engine_100_fixture_items_and_deduplication():
    """Verify ingestion of 100+ fixture items across multiple feeds,
    ensuring duplicate reruns create 0 new candidates (idempotency).
    """
    engine = RssEngine()
    engine.validate_config()
    now = datetime.now(timezone.utc)

    subjects_a = [
        "SWE-bench", "Cursor", "Windsurf", "Aider", "Cline", "OpenHands", "Devin", "Qwen-Coder",
        "DeepSeek-R1", "Ollama", "vLLM", "SGLang", "Llama-3", "Mistral-Large", "LangChain",
        "LlamaIndex", "DSPy", "CrewAI", "AutoGen", "Semantic-Kernel", "ChromaDB", "Qdrant",
        "Milvus", "LanceDB", "FastAPI", "Next.js", "Docker", "Kubernetes", "PostgreSQL",
        "SQLite", "Ray-Serve", "Triton-Inference", "TensorRT-LLM", "ExLlamaV2", "llama.cpp",
        "Tree-Sitter", "AST-Parsing", "Ripgrep", "Git-Automation", "Prompt-Caching",
        "Speculative-Decoding", "Structured-Outputs", "Function-Calling", "Evals-Harness",
        "Code-Review-Agent", "Refactoring-Agent", "Test-Generation-Agent", "Bug-Localization",
        "Repository-Indexing", "Context-Pruning", "Embedding-Quantization", "Model-Merging",
        "LoRA-Fine-Tuning", "Unsloth-Acceleration"
    ]
    subjects_b = [
        "Continuous-Integration", "Performance-Profiling", "Memory-Leak-Detector", "Thread-Pool",
        "Asynchronous-IO", "Zero-Copy-Serialization", "Protocol-Buffers", "gRPC-Services",
        "GraphQL-Endpoints", "WebSockets-Relay", "Distributed-Tracing", "Prometheus-Metrics",
        "Grafana-Dashboards", "Alertmanager-Rules", "Incident-Runbook", "Chaos-Experiment",
        "Deadlock-Detection", "Connection-Pooling", "Database-Migration", "Schema-Validation",
        "Security-Hardening", "Secret-Scanning", "Vulnerability-Audit", "Penetration-Testing",
        "Static-Type-Checker", "Bytecode-Optimization", "JIT-Compilation", "Native-Extensions",
        "C-FFI-Bindings", "Rust-Toolchain", "WebAssembly-Runtimes", "Linux-Namespaces",
        "Cgroups-V2", "Systemd-Services", "eBPF-Tracing", "Kernel-Bypass",
        "High-Throughput-Queues", "WAL-Journaling", "B-Tree-Indexes", "Bitmap-Scans",
        "Vector-Search-Algorithms", "HNSW-Graphs", "IVF-PQ-Compression", "Cosine-Similarity",
        "Semantic-Reranking", "Cross-Encoder-Models", "ColBERT-Late-Interaction", "BM25-Hybrid",
        "Reciprocal-Rank-Fusion", "Query-Rewriting", "Chunking-Strategies", "Document-Parsers",
        "Markdown-AST", "Metadata-Enrichment", "Knowledge-Graphs", "Entity-Extraction",
        "Relation-Extraction", "Ontology-Mapping", "Graph-Retrieval"
    ]

    feed1_items = [
        {
            "title": f"Exploring {subjects_a[i-1]} for Coding Agents #{i}",
            "link": f"https://agentnews.example.com/article-{subjects_a[i-1].lower()}",
            "summary": f"Deep dive into {subjects_a[i-1]} with reproducible benchmark and code repository.",
            "pub_date": email.utils.format_datetime(now - timedelta(hours=i % 24)),
        }
        for i in range(1, len(subjects_a) + 1)
    ]

    feed2_items = [
        {
            "title": f"Evaluating {subjects_b[j-1]} in Local LLM Workflows #{j}",
            "link": f"https://localai.example.org/tests/{subjects_b[j-1].lower()}",
            "summary": f"Benchmark measuring {subjects_b[j-1]} with code repository and reproducible benchmark.",
            "pub_date": (now - timedelta(hours=j % 30)).isoformat(),
        }
        for j in range(1, len(subjects_b) + 1)
    ]

    feed1_xml = _generate_rss_xml(feed1_items)
    feed2_xml = _generate_atom_xml(feed2_items)

    test_feeds = [
        SourceFeedInput(name="AgentNews", url="https://agentnews.example.com/rss", trust_weight=0.85),
        SourceFeedInput(name="LocalAI", url="https://localai.example.org/atom", trust_weight=0.90),
    ]

    xml_fixtures = {
        "https://agentnews.example.com/rss": feed1_xml,
        "https://localai.example.org/atom": feed2_xml,
    }

    ctx = EngineContext(
        run_id="test_run_100_items",
        parameters={"feeds": test_feeds, "xml_fixtures": xml_fixtures},
    )

    # First run
    res = await engine.run(ctx)
    assert res.success is True
    assert res.input_count == 113  # 54 + 59 = 113 items
    assert res.output_count == 113
    assert res.error_count == 0

    # RERUN with the EXACT SAME feed data to verify idempotency (0 new candidates created)
    ctx_rerun = EngineContext(
        run_id="test_run_rerun",
        parameters={"feeds": test_feeds, "xml_fixtures": xml_fixtures},
    )
    res_rerun = await engine.run(ctx_rerun)
    assert res_rerun.input_count == 113
    for cand in res_rerun.outputs:
        assert cand["source_count"] >= 1


@pytest.mark.asyncio
async def test_failing_feed_isolation():
    """Verify that a failing/malformed feed does NOT break successful feeds in the batch."""
    engine = RssEngine()
    now = datetime.now(timezone.utc)

    good_items = [
        {
            "title": "Production Automation Recipe with Local Models",
            "link": "https://goodfeed.example.com/recipe-1",
            "summary": "Deploying reproducible evals and workflow automation.",
            "pub_date": email.utils.format_datetime(now),
        }
    ]
    good_xml = _generate_rss_xml(good_items)
    bad_xml = "<invalid_xml><broken></unclosed>"

    test_feeds = [
        SourceFeedInput(name="GoodFeed", url="https://good.example.com/feed", trust_weight=0.8),
        SourceFeedInput(name="BrokenFeed", url="https://broken.example.com/feed", trust_weight=0.7),
        SourceFeedInput(name="TimeoutFeed", url="https://timeout.example.com/feed", trust_weight=0.6),
    ]

    xml_fixtures = {
        "https://good.example.com/feed": good_xml,
        "https://broken.example.com/feed": bad_xml,
    }

    ctx = EngineContext(
        run_id="test_isolation",
        parameters={"feeds": test_feeds, "xml_fixtures": xml_fixtures},
    )

    res = await engine.run(ctx)
    assert res.success is False  # some feeds failed
    assert res.error_count == 2  # BrokenFeed and TimeoutFeed
    assert res.output_count == 1
    assert res.outputs[0]["title"] == "Production Automation Recipe with Local Models"
    assert len(res.errors) >= 1


@pytest.mark.asyncio
async def test_freshness_filter_rejects_old_content():
    """Verify items older than max_item_age_hours (72h) are rejected."""
    engine = RssEngine()
    now = datetime.now(timezone.utc)

    items = [
        {
            "title": "Fresh AI Engineering Article",
            "link": "https://example.com/fresh-ai",
            "summary": "Coding agents evals and benchmarks update with reproducible benchmark and code repository.",
            "pub_date": email.utils.format_datetime(now - timedelta(hours=5)),
        },
        {
            "title": "Ancient 10-Day-Old Article on Developer Tools",
            "link": "https://example.com/ancient-article",
            "summary": "Old news from 10 days ago.",
            "pub_date": email.utils.format_datetime(now - timedelta(days=10)),
        },
    ]

    feed_xml = _generate_rss_xml(items)
    feeds = [SourceFeedInput(name="TechNews", url="https://freshness.example.com/feed", trust_weight=0.8)]
    ctx = EngineContext(
        run_id="test_freshness",
        parameters={"feeds": feeds, "xml_fixtures": {"https://freshness.example.com/feed": feed_xml}},
    )

    res = await engine.run(ctx)
    assert res.rejected_count == 1
    assert res.output_count == 1
    assert res.outputs[0]["title"] == "Fresh AI Engineering Article"
    assert res.outputs[0]["is_in_niche"] is True


@pytest.mark.asyncio
async def test_niche_guard_filters_off_niche_and_blocked_topics():
    """Verify Niche Guard integration rejects blocked topics and off-niche content."""
    engine = RssEngine()
    now = datetime.now(timezone.utc)

    items = [
        {
            "title": "Coding Agent Evaluation with Local LLMs",
            "link": "https://niche-filter-test.example.com/in-niche-agent",
            "summary": "Evaluating coding agents on local models and developer tools with code repository and reproducible benchmark.",
            "pub_date": email.utils.format_datetime(now),
        },
        {
            "title": "New Crypto Web3 Token presale hits $100M",
            "link": "https://niche-filter-test.example.com/crypto-coin",
            "summary": "Get rich quick with this crypto/web3 trading presale token.",
            "pub_date": email.utils.format_datetime(now),
        },
        {
            "title": "Best Dog Food Recipes For Golden Retrievers",
            "link": "https://niche-filter-test.example.com/dog-food",
            "summary": "Healthy organic food for dogs.",
            "pub_date": email.utils.format_datetime(now),
        },
    ]

    feed_xml = _generate_rss_xml(items)
    feeds = [SourceFeedInput(name="MixedFeed", url="https://mixed.example.com/feed", trust_weight=0.8)]
    ctx = EngineContext(
        run_id="test_niche_filter",
        parameters={"feeds": feeds, "xml_fixtures": {"https://mixed.example.com/feed": feed_xml}},
    )

    res = await engine.run(ctx)
    assert res.rejected_count == 2

    # Check candidates status
    candidates_by_title = {c["title"]: c for c in res.outputs}
    assert candidates_by_title["Coding Agent Evaluation with Local LLMs"]["status"] == "candidate"
    assert candidates_by_title["Coding Agent Evaluation with Local LLMs"]["is_in_niche"] is True
    assert candidates_by_title["Coding Agent Evaluation with Local LLMs"]["pillar"] is not None

    assert candidates_by_title["New Crypto Web3 Token presale hits $100M"]["status"] == "rejected"
    assert candidates_by_title["New Crypto Web3 Token presale hits $100M"]["is_in_niche"] is False

    assert candidates_by_title["Best Dog Food Recipes For Golden Retrievers"]["status"] == "rejected"


@pytest.mark.asyncio
async def test_cross_source_grouping():
    """Verify that multiple feeds reporting the same story are grouped into a single candidate
    with source_count, source list, and updated authority mix.
    """
    engine = RssEngine()
    now = datetime.now(timezone.utc)

    # 3 feeds report on the exact same story with slight title variations
    feed_a_items = [
        {
            "title": "Anthropic Announces Claude 3.7 Sonnet with Hybrid Reasoning",
            "link": "https://arstechnica.com/ai/2026/02/claude-3-7-sonnet-hybrid-reasoning?utm_source=rss",
            "summary": "Anthropic has released Claude 3.7 Sonnet with hybrid reasoning capabilities for coding agents.",
            "pub_date": email.utils.format_datetime(now),
        }
    ]

    feed_b_items = [
        {
            "title": "Claude 3.7 Sonnet Released by Anthropic: Hybrid Reasoning for Coding",
            "link": "https://techcrunch.com/2026/02/claude-3-7-sonnet-hybrid-reasoning/?ref=feed",
            "summary": "New frontier model Claude 3.7 Sonnet introduces hybrid reasoning for coding agents and developer tools.",
            "pub_date": email.utils.format_datetime(now - timedelta(minutes=15)),
        }
    ]

    feed_c_items = [
        {
            "title": "Anthropic Announces Claude 3.7 Sonnet with Hybrid Reasoning Models",
            "link": "https://news.ycombinator.com/item?id=999888",
            "summary": "Discussion of Claude 3.7 Sonnet hybrid reasoning benchmark results.",
            "pub_date": email.utils.format_datetime(now - timedelta(minutes=30)),
        }
    ]

    feeds = [
        SourceFeedInput(name="Ars Technica", url="https://arstechnica.com/feed", trust_weight=0.90),
        SourceFeedInput(name="TechCrunch", url="https://techcrunch.com/feed", trust_weight=0.80),
        SourceFeedInput(name="Hacker News", url="https://news.ycombinator.com/feed", trust_weight=0.70),
    ]

    xml_fixtures = {
        "https://arstechnica.com/feed": _generate_rss_xml(feed_a_items),
        "https://techcrunch.com/feed": _generate_rss_xml(feed_b_items),
        "https://news.ycombinator.com/feed": _generate_rss_xml(feed_c_items),
    }

    ctx = EngineContext(
        run_id="test_cross_source",
        parameters={"feeds": feeds, "xml_fixtures": xml_fixtures},
    )

    res = await engine.run(ctx)

    # Should group into 1 candidate
    assert res.output_count == 1
    candidate = res.outputs[0]
    assert candidate["source_count"] == 3
    assert len(candidate["sources"]) == 3
    source_names = {s["feed_name"] for s in candidate["sources"]}
    assert source_names == {"Ars Technica", "TechCrunch", "Hacker News"}

    # Authority score should be average: (0.90 + 0.80 + 0.70) / 3 = 0.80
    assert candidate["authority_score"] == 0.8

    # Verify explainability
    explanation = engine.explain(ctx.run_id)
    assert explanation.result_id == ctx.run_id
    assert "cross-source grouped" in explanation.summary
