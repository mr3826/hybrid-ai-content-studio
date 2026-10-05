from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional
import uuid


class GeneratedMediaAdapter(ABC):
    """Abstract contract for pluggable generated media adapters."""

    @abstractmethod
    def generate_visual(
        self,
        prompt: str,
        visual_type: str,
        title: str,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generates a visual asset from prompt/context without external vendor lock-in."""
        pass


class LocalDeterministicVisualAdapter(GeneratedMediaAdapter):
    """Local, offline visual generator that creates deterministic visual SVG cards.

    Ensures the studio is 100% operational with zero paid image/video API dependencies.
    """

    def generate_visual(
        self,
        prompt: str,
        visual_type: str,
        title: str,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        target_dir = output_dir or Path("data/assets/generated")
        target_dir.mkdir(parents=True, exist_ok=True)

        asset_id = f"gen-{uuid.uuid4().hex[:8]}"
        file_name = f"{asset_id}.svg"
        file_path = target_dir / file_name

        # Clean display texts
        safe_title = title.replace("<", "&lt;").replace(">", "&gt;")[:40]
        safe_type = visual_type.replace("_", " ").upper()
        safe_prompt = prompt.replace("<", "&lt;").replace(">", "&gt;")[:60]

        # Generate a high-contrast dark-mode SVG card suitable for video overlay / testing
        svg_content = f"""<svg width="1080" height="1920" viewBox="0 0 1080 1920" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#020617" />
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#6366f1" />
      <stop offset="100%" stop-color="#a855f7" />
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="1080" height="1920" fill="url(#bg)" />

  <!-- Grid Pattern -->
  <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
    <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#1e293b" stroke-width="1" opacity="0.6"/>
  </pattern>
  <rect width="1080" height="1920" fill="url(#grid)" />

  <!-- Badge Container -->
  <rect x="140" y="500" width="800" height="920" rx="32" fill="#1e293b" fill-opacity="0.7" stroke="#334155" stroke-width="3" />

  <!-- Header Accent Line -->
  <rect x="140" y="500" width="800" height="12" rx="6" fill="url(#accent)" />

  <!-- Type Badge -->
  <rect x="200" y="560" width="280" height="54" rx="27" fill="#6366f1" fill-opacity="0.2" stroke="#6366f1" stroke-width="2" />
  <text x="340" y="596" font-family="system-ui, sans-serif" font-size="22" font-weight="bold" fill="#818cf8" text-anchor="middle">
    {safe_type}
  </text>

  <!-- Title -->
  <text x="200" y="680" font-family="system-ui, sans-serif" font-size="44" font-weight="800" fill="#ffffff">
    {safe_title}
  </text>

  <!-- Prompt / Spec Preview -->
  <text x="200" y="740" font-family="system-ui, sans-serif" font-size="24" fill="#94a3b8">
    Evidence Cue: {safe_prompt}
  </text>

  <!-- Center Graphic Icon Representation -->
  <circle cx="540" cy="980" r="160" fill="#0f172a" stroke="#6366f1" stroke-width="4" stroke-dasharray="12 12" />
  <text x="540" y="995" font-family="system-ui, monospace" font-size="40" font-weight="bold" fill="#38bdf8" text-anchor="middle">
    EVIDENCE 1st
  </text>

  <!-- Footer Watermark -->
  <text x="540" y="1340" font-family="system-ui, sans-serif" font-size="20" fill="#64748b" text-anchor="middle">
    Fresh Local AI Content Studio • Local Offline Asset
  </text>
</svg>"""

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        return {
            "asset_id": asset_id,
            "file_name": file_name,
            "file_path": str(file_path).replace("\\", "/"),
            "mime_type": "image/svg+xml",
            "visual_type": visual_type,
            "is_local_mock": True,
            "width": 1080,
            "height": 1920,
        }
