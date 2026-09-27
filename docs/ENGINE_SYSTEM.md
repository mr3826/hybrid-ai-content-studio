# Engine System — Architecture & Catalog

## 1. Engine Structure Standard
Every engine is located under `apps/api/app/engines/<engine_name>/` and implements:
- `manifest.yaml`: Engine ID, version, dependencies, capabilities (dry run, explain, health check).
- `README.md`: Design purpose, input/output schemas, and usage examples.
- `engine.py`: Core logic inheriting from `BaseEngine`.
- `contracts.py`: Typed Pydantic input and output schemas.
- `rules.yaml`: Versioned configuration parameters.
- `tests/`: Isolated unit tests ensuring regression safety.

## 2. Base Engine Interface
```python
class BaseEngine(ABC):
    id: str
    version: str

    @abstractmethod
    def validate_config(self) -> None: ...

    @abstractmethod
    def health(self) -> EngineHealth: ...

    @abstractmethod
    async def run(self, context: EngineContext) -> EngineResult: ...

    @abstractmethod
    async def dry_run(self, context: EngineContext) -> EngineResult: ...

    @abstractmethod
    def explain(self, result_id: str) -> EngineExplanation: ...
```

## 3. Engine Catalog

| Engine ID | Name | Inputs | Outputs | Dependencies |
|---|---|---|---|---|
| `rss` | RSS Discovery Engine | SourceFeed list | DiscoveryCandidate list | `niche_guard` |
| `trends` | Trends Engine | DiscoveryCandidate list | TopicTrend list | None |
| `niche_guard` | Niche Guard Engine | Candidate/Content text | GuardVerdict | None |
| `opportunity` | Opportunity Scoring Engine | Candidate + Trend + Guard | OpportunityScore list | `niche_guard`, `trends` |
| `brand` | Brand Engine | ContentDraft | BrandVerdict | None |
| `research` | Research Engine | ApprovedCandidate | ResearchPacket | None |
| `originality` | Originality Engine | ResearchPacket | OriginalityPlan | None |
| `ai` | AI Provider Engine | PromptRequest | ProviderResponse | None |
| `content_family` | Content Family Engine | Research + Originality + Evidence + Brand | ContentFamilyPlan | `research`, `evidence`, `originality`, `brand` |
| `content` | Content Engine | Research + Originality + Brand | MasterContent | `brand`, `ai` |
| `media` | Media Engine | SceneStoryboard | RenderedMedia | None |
| `export` | Export Engine | MasterContent + RenderedMedia | ExportPackage | None |
| `analytics` | Analytics Engine | PublicationRecord + Metrics | AnalyticsReport | None |
| `cleanup` | Cleanup Engine | StorageState | CleanupResult | None |
