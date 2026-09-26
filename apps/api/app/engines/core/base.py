from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, ConfigDict, Field


class EngineManifest(BaseModel):
    id: str = Field(..., description="Unique engine identifier e.g. rss, trends")
    name: str = Field(..., description="Human-readable engine title")
    version: str = Field(default="1.0.0", description="Semantic version string")
    description: str = Field(default="", description="Detailed summary of engine function")
    enabled: bool = Field(default=True, description="Whether the engine is active in the studio")
    inputs: List[str] = Field(default_factory=list, description="List of accepted input data contracts")
    outputs: List[str] = Field(default_factory=list, description="List of produced output data contracts")
    dependencies: List[str] = Field(default_factory=list, description="Other engine IDs required to run")
    triggers: List[str] = Field(default_factory=lambda: ["manual"], description="Supported triggers")
    supports: Dict[str, bool] = Field(
        default_factory=lambda: {
            "dry_run": True,
            "explain": True,
            "health_check": True,
            "configure": True,
        }
    )

    model_config = ConfigDict(extra="ignore")


class EngineHealth(BaseModel):
    status: str = Field(description="healthy, degraded, failing")
    message: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)


class EngineContext(BaseModel):
    run_id: str
    dry_run: bool = False
    trigger: str = "manual"
    parameters: Dict[str, Any] = Field(default_factory=dict)


class EngineResult(BaseModel):
    engine_id: str
    engine_version: str
    run_id: str
    success: bool
    started_at: datetime
    ended_at: datetime
    duration_ms: int = 0
    input_count: int = 0
    output_count: int = 0
    rejected_count: int = 0
    error_count: int = 0
    cost: float = 0.0
    summary: str = ""
    outputs: List[Any] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    explanations: List[Dict[str, Any]] = Field(default_factory=list)


class EngineExplanation(BaseModel):
    result_id: str
    summary: str
    factors: List[Dict[str, Any]] = Field(default_factory=list)


class BaseEngine(ABC):
    """Abstract Base Class for all 13 Studio Engines."""

    def __init__(self, engine_dir: Optional[Path] = None):
        self.engine_dir = engine_dir
        self.manifest = self._load_manifest()
        self.rules = self._load_rules()

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    def _load_manifest(self) -> EngineManifest:
        if self.engine_dir:
            manifest_file = self.engine_dir / "manifest.yaml"
            if manifest_file.exists():
                with open(manifest_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    return EngineManifest(**data)
        return EngineManifest(
            id="base",
            name="Base Engine",
            version="1.0.0",
            description="Abstract base engine",
        )

    def _load_rules(self) -> Dict[str, Any]:
        if self.engine_dir:
            rules_file = self.engine_dir / "rules.yaml"
            if rules_file.exists():
                with open(rules_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        return {}

    def get_rules(self) -> Dict[str, Any]:
        return self.rules

    def update_rules(self, new_rules: Dict[str, Any]) -> None:
        self.rules = new_rules
        if self.engine_dir:
            rules_file = self.engine_dir / "rules.yaml"
            with open(rules_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(new_rules, f, sort_keys=False)
        self.validate_config()

    @abstractmethod
    def validate_config(self) -> None:
        """Validate engine configuration or rules."""
        pass

    @abstractmethod
    def health(self) -> EngineHealth:
        """Perform active health check."""
        pass

    @abstractmethod
    async def run(self, context: EngineContext) -> EngineResult:
        """Execute the engine logic with side effects."""
        pass

    @abstractmethod
    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Execute without persisting side effects."""
        pass

    @abstractmethod
    def explain(self, result_id: str) -> EngineExplanation:
        """Provide detailed human-readable breakdown of an output decision."""
        pass
