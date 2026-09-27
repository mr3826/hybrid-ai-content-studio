from app.engines.core.base import EngineManifest
from app.engines.core.catalog_engine import CatalogEngine
from app.engines.core.registry import engine_registry
from app.engines.reference.engine import ReferenceEngine
from app.engines.niche_guard.engine import NicheGuardEngine
from app.engines.brand.engine import BrandEngine
from app.engines.rss.engine import RssEngine
from app.engines.trends.engine import TrendsEngine

CATALOG_DEFINITIONS = [

    {
        "id": "rss",
        "name": "RSS Discovery Engine",
        "version": "1.0.0",
        "description": "Discovers fresh niche candidates from configured RSS/Atom feeds with zero AI calls.",
        "inputs": ["SourceFeed"],
        "outputs": ["DiscoveryCandidate"],
        "dependencies": ["niche_guard"],
        "triggers": ["manual", "scheduled"],
    },
    {
        "id": "trends",
        "name": "Trends Engine",
        "version": "1.0.0",
        "description": "Detects velocity, mention frequency, and cross-source momentum inside the niche.",
        "inputs": ["DiscoveryCandidate"],
        "outputs": ["TopicTrend"],
        "dependencies": [],
        "triggers": ["manual", "scheduled"],
    },
    {
        "id": "niche_guard",
        "name": "Niche Guard Engine",
        "version": "1.0.0",
        "description": "Deterministic keyword, topic, and negative signal filtering against the single niche profile.",
        "inputs": ["DiscoveryCandidate", "ContentDraft"],
        "outputs": ["NicheGuardVerdict"],
        "dependencies": [],
        "triggers": ["manual"],
    },
    {
        "id": "opportunity",
        "name": "Opportunity Scoring Engine",
        "version": "1.0.0",
        "description": "Ranks candidates on business value, originality potential, trend strength, and evergreen value.",
        "inputs": ["DiscoveryCandidate", "TopicTrend", "NicheGuardVerdict"],
        "outputs": ["OpportunityScore"],
        "dependencies": ["niche_guard", "trends"],
        "triggers": ["manual"],
    },
    {
        "id": "brand",
        "name": "Brand Engine",
        "version": "1.0.0",
        "description": "Enforces voice, tone, banned clichés, claim rules, and visual identity consistency.",
        "inputs": ["ContentDraft", "ScriptDraft"],
        "outputs": ["BrandQAVerdict"],
        "dependencies": [],
        "triggers": ["manual"],
    },
    {
        "id": "research",
        "name": "Research Engine",
        "version": "1.0.0",
        "description": "Extracts verifiable facts, numbers, dates, and claims with primary source links.",
        "inputs": ["OpportunityScore", "SourceArticle"],
        "outputs": ["ResearchPacket"],
        "dependencies": [],
        "triggers": ["manual"],
    },
    {
        "id": "originality",
        "name": "Originality Engine",
        "version": "1.0.0",
        "description": "Enforces channel contribution (test, benchmark, tutorial, failure analysis) and blocks generic summaries.",
        "inputs": ["ResearchPacket"],
        "outputs": ["OriginalityPlan"],
        "dependencies": [],
        "triggers": ["manual"],
    },
    {
        "id": "ai",
        "name": "AI Provider Engine",
        "version": "1.0.0",
        "description": "Pluggable LLM provider adapters (Gemini, Qwen) with technical fallback and token cost logging.",
        "inputs": ["PromptRequest"],
        "outputs": ["ModelResponse"],
        "dependencies": [],
        "triggers": ["manual"],
    },
    {
        "id": "content",
        "name": "Content Engine",
        "version": "1.0.0",
        "description": "Generates structured shorts, long-form scripts, and platform companion posts.",
        "inputs": ["ResearchPacket", "OriginalityPlan", "BrandProfile"],
        "outputs": ["MasterContent"],
        "dependencies": ["brand", "ai"],
        "triggers": ["manual"],
    },
    {
        "id": "media",
        "name": "Media Engine",
        "version": "1.0.0",
        "description": "Manages TTS synthesis, subtitle alignment, licensed BGM, and FFmpeg video composition.",
        "inputs": ["MasterContent", "SceneStoryboard"],
        "outputs": ["RenderedMedia"],
        "dependencies": [],
        "triggers": ["manual", "queue"],
    },
    {
        "id": "export",
        "name": "Export Engine",
        "version": "1.0.0",
        "description": "Assembles final video, platform captions, hashtags, and manifest packages.",
        "inputs": ["MasterContent", "RenderedMedia"],
        "outputs": ["ExportPackage"],
        "dependencies": [],
        "triggers": ["manual"],
    },
    {
        "id": "analytics",
        "name": "Analytics Engine",
        "version": "1.0.0",
        "description": "Analyzes manual publication metrics, hook performance, and content ROI.",
        "inputs": ["PublicationRecord"],
        "outputs": ["PerformanceInsight"],
        "dependencies": [],
        "triggers": ["manual"],
    },
    {
        "id": "cleanup",
        "name": "Cleanup Engine",
        "version": "1.0.0",
        "description": "Executes reference-safe storage retention, cache pruning, and recoverable bytes calculation.",
        "inputs": ["StorageInspection"],
        "outputs": ["CleanupReport"],
        "dependencies": [],
        "triggers": ["manual", "scheduled"],
    },
]


def register_all_catalog_engines() -> None:
    """Register all 13 standard catalog engines and the reference engine."""
    # Register reference engine first
    ref_engine = ReferenceEngine()
    if not engine_registry.get(ref_engine.id):
        engine_registry.register(ref_engine)

    # Register concrete engines
    niche_guard_engine = NicheGuardEngine()
    engine_registry.register(niche_guard_engine, replace=True)

    brand_engine = BrandEngine()
    engine_registry.register(brand_engine, replace=True)

    rss_engine = RssEngine()
    engine_registry.register(rss_engine, replace=True)

    trends_engine = TrendsEngine()
    engine_registry.register(trends_engine, replace=True)

    # Register remaining catalog engines as placeholders if not already registered
    for d in CATALOG_DEFINITIONS:
        if d["id"] in ("niche_guard", "brand", "rss", "trends"):
            continue
        if not engine_registry.get(d["id"]):
            manifest = EngineManifest(**d)
            engine = CatalogEngine(manifest=manifest)
            engine_registry.register(engine)
