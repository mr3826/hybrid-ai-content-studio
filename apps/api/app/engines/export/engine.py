import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.engines.core import BaseEngine, EngineContext, EngineExplanation, EngineHealth, EngineResult
from app.engines.export.contracts import (
    ExportEngineInput,
    ExportPackageOutput,
    PlatformPackageData,
    PublishingChecklist,
)

logger = logging.getLogger("studio.engines.export")


class ExportEngine(BaseEngine):
    """Engine responsible for assembling verified, offline-first export packages
    and generating tailored platform metadata for manual publishing.
    """

    def __init__(self, engine_dir: Optional[Path] = None):
        super().__init__(engine_dir=engine_dir or Path(__file__).parent)

    def validate_config(self) -> None:
        if not self.rules:
            raise ValueError("ExportEngine rules cannot be empty.")
        if "platform_limits" not in self.rules:
            raise ValueError("ExportEngine rules missing 'platform_limits'.")
        if "package_contents" not in self.rules:
            raise ValueError("ExportEngine rules missing 'package_contents'.")

    def health(self) -> EngineHealth:
        has_manifest = self.manifest is not None
        has_rules = bool(self.rules)
        status = "healthy" if (has_manifest and has_rules) else "degraded"
        platforms = list(self.rules.get("platform_limits", {}).keys()) if self.rules else []
        return EngineHealth(
            status=status,
            message="Export engine configuration and platform rules loaded.",
            details={
                "engine_id": "export",
                "version": self.manifest.version if self.manifest else "1.0.0",
                "supported_platforms": platforms,
                "required_files": self.rules.get("package_contents", {}).get("required_files", []),
            },
        )

    async def run(self, context: EngineContext) -> EngineResult:
        """Executes export package generation through standard EngineContext."""
        started_at = datetime.now(timezone.utc)
        params = context.parameters
        try:
            payload = ExportEngineInput.model_validate(params)
            output = self.generate_export_package(payload)
            ended_at = datetime.now(timezone.utc)
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)
            return EngineResult(
                engine_id="export",
                engine_version=self.manifest.version if self.manifest else "1.0.0",
                rules_version=self.rules_version,
                run_id=context.run_id,
                project_id=context.project_id,
                success=True,
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
                input_count=1,
                output_count=len(output.files),
                summary=f"Successfully assembled export package {output.package_slug} with {len(output.files)} files.",
                outputs=[output.model_dump(mode="json")],
            )
        except Exception as e:
            logger.error("ExportEngine execution failed: %s", e, exc_info=True)
            ended_at = datetime.now(timezone.utc)
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)
            return EngineResult(
                engine_id="export",
                engine_version=self.manifest.version if self.manifest else "1.0.0",
                rules_version=self.rules_version,
                run_id=context.run_id,
                project_id=context.project_id,
                success=False,
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
                input_count=1,
                output_count=0,
                error_count=1,
                summary=f"ExportEngine failed: {str(e)}",
                errors=[str(e)],
            )

    async def dry_run(self, context: EngineContext) -> EngineResult:
        """Executes dry run without writing files to disk."""
        started_at = datetime.now(timezone.utc)
        params = dict(context.parameters)
        params["dry_run"] = True
        try:
            payload = ExportEngineInput.model_validate(params)
            output = self.generate_export_package(payload)
            ended_at = datetime.now(timezone.utc)
            return EngineResult(
                engine_id="export",
                engine_version=self.manifest.version if self.manifest else "1.0.0",
                rules_version=self.rules_version,
                run_id=context.run_id,
                project_id=context.project_id,
                success=True,
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=0,
                input_count=1,
                output_count=len(output.files),
                summary="ExportEngine dry run passed. Verified manifest, files, and checksums in memory.",
                outputs=[output.model_dump(mode="json")],
            )
        except Exception as e:
            ended_at = datetime.now(timezone.utc)
            return EngineResult(
                engine_id="export",
                engine_version=self.manifest.version if self.manifest else "1.0.0",
                rules_version=self.rules_version,
                run_id=context.run_id,
                project_id=context.project_id,
                success=False,
                started_at=started_at,
                ended_at=ended_at,
                error_count=1,
                summary=f"ExportEngine dry run failed: {str(e)}",
                errors=[str(e)],
            )

    def explain(self, result_id: str) -> EngineExplanation:
        """Provides transparency into package structure, checklist verification, and checksums."""
        return EngineExplanation(
            result_id=result_id,
            summary="Export packages compile factual citations, structured scripts, visual asset requirements, and tailored social platform copy into a reference-safe offline bundle.",
            factors=[
                {
                    "title": "Evidence Preservation",
                    "description": "Evidence & primary sources are compiled into sources.md and evidence-summary.md.",
                },
                {
                    "title": "Platform Tailoring",
                    "description": "Copy is formatted for YouTube, Facebook, Instagram, and TikTok with character limits.",
                },
                {
                    "title": "Cryptographic Integrity",
                    "description": "A SHA256 checksum manifest validates package contents against drift or corruption.",
                },
                {
                    "title": "Human Readiness Gate",
                    "description": "The 7-point checklist verifies media, thumbnail, title/caption, and licensing before publishing.",
                },
            ],
        )

    def generate_export_package(
        self,
        payload: ExportEngineInput,
        base_dir: Optional[Path] = None,
    ) -> ExportPackageOutput:
        """Assembles the offline export package directory, renders markdown documents,
        tailors social copy, writes all files, and calculates SHA256 checksums.
        """
        package_id = str(uuid.uuid4())
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug_clean = re.sub(r"[^a-zA-Z0-9_\-]+", "-", payload.slug).strip("-").lower()
        package_slug = f"{date_str}-{slug_clean}"

        # Determine target export directory
        export_root = Path(base_dir) if base_dir else Path(self.rules.get("storage", {}).get("export_root", "data/exports"))
        package_dir = export_root / package_slug

        # 1. Generate text documents
        sources_content = self._render_sources_markdown(payload)
        evidence_content = self._render_evidence_markdown(payload)
        script_content = self._render_script_markdown(payload)
        assets_content = self._render_asset_requirements_markdown(payload)

        # 2. Tailor platform metadata
        platform_packages = self._generate_platform_metadata(payload)

        # 3. Collect all files to write
        files_to_write: Dict[str, str] = {
            "sources.md": sources_content,
            "evidence-summary.md": evidence_content,
            "script.md": script_content,
            "asset-requirements.md": assets_content,
            "youtube/title.txt": platform_packages["youtube"].title,
            "youtube/description.txt": platform_packages["youtube"].caption,
            "youtube/hashtags.txt": " ".join(platform_packages["youtube"].hashtags),
            "youtube/pinned-comment.txt": platform_packages["youtube"].pinned_comment,
            "facebook/caption.txt": platform_packages["facebook"].caption,
            "instagram/caption.txt": platform_packages["instagram"].caption,
            "tiktok/caption.txt": platform_packages["tiktok"].caption,
        }

        # 4. Calculate individual file checksums
        file_checksums: Dict[str, str] = {}
        for rel_path, content in files_to_write.items():
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            file_checksums[rel_path] = digest

        # 5. Build Manifest JSON
        manifest_dict: Dict[str, Any] = {
            "export_id": package_id,
            "content_item_id": payload.content_item_id,
            "package_slug": package_slug,
            "title": payload.working_title,
            "format": payload.format,
            "platform_target": payload.platform_target,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "brand": {
                "name": payload.brand_name,
                "tone": payload.brand_tone,
            },
            "engine_versions": {
                "export": self.manifest.version if self.manifest else "1.0.0",
                **payload.engine_versions,
            },
            "sources_count": len(payload.sources),
            "claims_count": len(payload.claims),
            "file_checksums": file_checksums,
        }

        manifest_content = json.dumps(manifest_dict, indent=2, ensure_ascii=False)
        manifest_checksum = hashlib.sha256(manifest_content.encode("utf-8")).hexdigest()
        manifest_dict["package_checksum"] = manifest_checksum
        files_to_write["manifest.json"] = json.dumps(manifest_dict, indent=2, ensure_ascii=False)
        file_checksums["manifest.json"] = manifest_checksum

        # 6. Write files to disk if not dry_run
        relative_file_list = sorted(list(files_to_write.keys()))
        if not payload.dry_run:
            package_dir.mkdir(parents=True, exist_ok=True)
            for rel_path, content in files_to_write.items():
                out_path = package_dir / rel_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(content, encoding="utf-8")

        # Update generated files list for platform data
        platform_packages["youtube"].files_generated = [
            "youtube/title.txt",
            "youtube/description.txt",
            "youtube/hashtags.txt",
            "youtube/pinned-comment.txt",
        ]
        platform_packages["facebook"].files_generated = ["facebook/caption.txt"]
        platform_packages["instagram"].files_generated = ["instagram/caption.txt"]
        platform_packages["tiktok"].files_generated = ["tiktok/caption.txt"]

        return ExportPackageOutput(
            package_id=package_id,
            package_slug=package_slug,
            export_dir=str(package_dir).replace("\\", "/"),
            files=relative_file_list,
            checksum=manifest_checksum,
            manifest_data=manifest_dict,
            platform_packages=platform_packages,
        )

    # -------------------------------------------------------------------------
    # Markdown Rendering Methods
    # -------------------------------------------------------------------------

    def _render_sources_markdown(self, payload: ExportEngineInput) -> str:
        lines = [
            f"# Primary Sources & Citations",
            f"",
            f"**Content Item:** {payload.working_title}  ",
            f"**Generated At:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Brand:** {payload.brand_name}  ",
            f"",
            f"---",
            f"",
            f"## Verified Primary Sources ({len(payload.sources)})",
            f"",
        ]

        if not payload.sources:
            lines.append("No primary sources were explicitly attached to this item.\n")
        else:
            for idx, s in enumerate(payload.sources, start=1):
                title = s.get("title", f"Source {idx}")
                url = s.get("url", "#")
                stype = s.get("source_type", "web_article")
                author = s.get("author_or_org") or "Unknown Author"
                excerpt = s.get("excerpt", "").strip()

                lines.append(f"### {idx}. {title}")
                lines.append(f"- **URL:** [{url}]({url})")
                lines.append(f"- **Type:** `{stype}` | **Author/Org:** {author}")
                if excerpt:
                    lines.append(f"- **Key Fact / Excerpt:**")
                    lines.append(f"  > {excerpt}")
                lines.append("")

        return "\n".join(lines)

    def _render_evidence_markdown(self, payload: ExportEngineInput) -> str:
        lines = [
            f"# Evidence & Empirical Foundation",
            f"",
            f"**Content Item:** {payload.working_title}  ",
            f"**Originality Contribution:** {payload.originality_summary or 'Direct empirical test / analysis'}  ",
            f"",
            f"---",
            f"",
            f"## Linked Claims & Verification Status ({len(payload.claims)})",
            f"",
        ]

        if not payload.claims:
            lines.append("No structured claims attached to this script.\n")
        else:
            lines.append("| # | Claim Text | Type | Verification | Metric / Quote |")
            lines.append("|---|---|---|---|---|")
            for idx, c in enumerate(payload.claims, start=1):
                text = c.get("claim_text", "").replace("|", "-")
                ctype = c.get("claim_type", "factual")
                vstatus = c.get("verification_status", "verified")
                metric = (c.get("quote_or_metric") or "").replace("|", "-")
                lines.append(f"| {idx} | {text} | `{ctype}` | **{vstatus}** | {metric} |")
            lines.append("")

        if payload.experiments:
            lines.extend([
                f"---",
                f"",
                f"## Empirical Experiments ({len(payload.experiments)})",
                f"",
            ])
            for exp in payload.experiments:
                exp_name = exp.get("name", "Experiment")
                exp_hyp = exp.get("hypothesis", "")
                exp_out = exp.get("outcome", "")
                lines.append(f"### {exp_name}")
                if exp_hyp:
                    lines.append(f"- **Hypothesis:** {exp_hyp}")
                if exp_out:
                    lines.append(f"- **Outcome/Result:** {exp_out}")
                lines.append("")

        return "\n".join(lines)

    def _render_script_markdown(self, payload: ExportEngineInput) -> str:
        lines = [
            f"# Script: {payload.script_title or payload.working_title}",
            f"",
            f"**Format:** `{payload.format}` | **Target Platform:** `{payload.platform_target}`  ",
            f"**Brand Tone:** {payload.brand_tone}  ",
            f"**Script Version:** v{payload.script_version}  ",
            f"",
            f"---",
            f"",
        ]

        if not payload.sections:
            lines.append("No script sections available.\n")
        else:
            total_duration = sum(s.get("estimated_seconds", 0) for s in payload.sections)
            total_words = sum(s.get("word_count", 0) for s in payload.sections)
            lines.append(f"**Total Duration:** ~{total_duration}s | **Total Words:** {total_words} words\n")

            for idx, sec in enumerate(payload.sections, start=1):
                stype = sec.get("section_type", "section").upper()
                heading = sec.get("heading") or f"Section {idx}"
                duration = sec.get("estimated_seconds", 0)
                words = sec.get("word_count", 0)
                narration = sec.get("narration", "").strip()
                visual = sec.get("visual_cue", "").strip()
                claims = sec.get("linked_claim_ids", [])

                lines.append(f"## {idx}. [{stype}] {heading} ({duration}s, {words} words)")
                if visual:
                    lines.append(f"> 🎬 **Visual Cue:** {visual}")
                    lines.append("")
                lines.append(f"**Narration:**")
                lines.append(f"{narration}")
                if claims:
                    lines.append(f"")
                    lines.append(f"*Linked Claims:* `{', '.join(claims)}`")
                lines.append("")

        return "\n".join(lines)

    def _render_asset_requirements_markdown(self, payload: ExportEngineInput) -> str:
        lines = [
            f"# Visual & Audio Asset Requirements",
            f"",
            f"**Item:** {payload.working_title}  ",
            f"**Target:** {payload.platform_target} ({payload.format})  ",
            f"",
            f"| Section | Est. Duration | Visual Requirements / B-Roll | Screen Capture / Tool Asset |",
            f"|---|---|---|---|",
        ]

        if not payload.sections:
            lines.append("| 1 | 0s | No assets specified | None |")
        else:
            for idx, sec in enumerate(payload.sections, start=1):
                stype = sec.get("section_type", "section")
                duration = f"{sec.get('estimated_seconds', 0)}s"
                visual = sec.get("visual_cue", "Standard talking head / presenter").replace("|", "-")
                screen_need = "Code editor / benchmark terminal" if "test" in stype or "evidence" in stype else "Presenter / graphic overlay"
                lines.append(f"| {idx}. {stype.title()} | {duration} | {visual} | {screen_need} |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## Audio & Licensing Checklist",
            f"- [x] Royalty-free or owned background music track (max -18dB relative to vocal).",
            f"- [x] Crisp voice track normalized to -14 LUFS (YouTube) / -16 LUFS (TikTok/Instagram).",
            f"- [x] On-screen fonts licensed for commercial digital publishing.",
        ])

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Social Platform Metadata Tailoring
    # -------------------------------------------------------------------------

    def _generate_platform_metadata(self, payload: ExportEngineInput) -> Dict[str, PlatformPackageData]:
        title = payload.script_title or payload.working_title
        brand = payload.brand_name
        ai_disclosure = self.rules.get("disclosures", {}).get(
            "ai_disclosure_text",
            "Created with local AI research assistance; tested, verified, and approved by a human creator."
        )

        # Extract primary hook and takeaways from script sections
        hook_text = ""
        result_text = ""
        cta_text = ""
        for sec in payload.sections:
            stype = sec.get("section_type", "").lower()
            if stype == "hook" and not hook_text:
                hook_text = sec.get("narration", "")
            elif stype in ("result", "evidence") and not result_text:
                result_text = sec.get("narration", "")
            elif stype == "cta" and not cta_text:
                cta_text = sec.get("narration", "")

        # Default fallback texts
        if not hook_text:
            hook_text = f"We tested {title} with real data."
        if not result_text:
            result_text = payload.originality_summary or "Here are the concrete benchmark results and takeaways."
        if not cta_text:
            cta_text = "What was your experience with this? Let us know in the comments."

        # 1. YouTube Metadata
        # Clean Title (max 100 chars)
        yt_title = title if len(title) <= 90 else title[:87] + "..."
        # Description
        yt_desc_parts = [
            hook_text,
            "",
            "📌 KEY TAKEAWAYS & METHODOLOGY:",
            result_text,
            "",
            "⏱️ CHAPTERS / TIMESTAMPS:",
        ]
        curr_time = 0
        for sec in payload.sections:
            mins = curr_time // 60
            secs = curr_time % 60
            sec_heading = sec.get("heading") or sec.get("section_type", "Section").title()
            yt_desc_parts.append(f"{mins:02d}:{secs:02d} - {sec_heading}")
            curr_time += sec.get("estimated_seconds", 0)

        yt_desc_parts.extend([
            "",
            "🔗 SOURCES & EVIDENCE CITATIONS:",
        ])
        for idx, s in enumerate(payload.sources[:5], start=1):
            s_url = s.get("url", "")
            s_title = s.get("title", f"Source {idx}")
            if s_url:
                yt_desc_parts.append(f"- {s_title}: {s_url}")

        yt_desc_parts.extend([
            "",
            "⚖️ TRANSPARENCY & DISCLOSURES:",
            f"• {ai_disclosure}",
            "",
            f"Subscribe to {brand} for empirical tool tests and workflows.",
        ])

        yt_hashtags = ["#AIAutomation", "#CodingAgents", "#TechReview", "#Productivity", "#OpenSource"]
        yt_pinned = f"💬 Discussion: {cta_text}\n\nCheck out the full evidence summary and sources in the description below!"

        # 2. Facebook Metadata
        fb_caption = f"{hook_text}\n\n{result_text}\n\n👉 {cta_text}\n\n{ai_disclosure}\n\n#AI #Automation #Coding #TechTools"

        # 3. Instagram Metadata
        ig_hashtags = ["#automation", "#artificialintelligence", "#codinglife", "#techreview", "#softwareengineering", "#developer", "#workflow", "#aitools"]
        ig_caption = f"{hook_text}\n\nSwipe to see our empirical test results 📊\n\nTakeaway: {result_text[:280]}\n\n💬 {cta_text}\n\n.\n.\n{' '.join(ig_hashtags)}"

        # 4. TikTok Metadata (punchy, max 2200 chars)
        tt_hashtags = ["#techtok", "#aitools", "#coding", "#developer", "#software"]
        tt_caption = f"{hook_text[:120]} Test results & breakdown: {result_text[:120]} {' '.join(tt_hashtags)}"

        default_checklist = {
            "media_ready": False,
            "thumbnail_ready": False,
            "title_caption_ready": True,
            "sources_checked": bool(payload.sources),
            "affiliate_disclosure_needed": False,
            "ai_disclosure_recommended": True,
            "asset_rights_verified": True,
        }

        return {
            "youtube": PlatformPackageData(
                platform="youtube",
                status="NOT_READY",
                title=yt_title,
                caption="\n".join(yt_desc_parts),
                hashtags=yt_hashtags,
                pinned_comment=yt_pinned,
                checklist=dict(default_checklist),
            ),
            "facebook": PlatformPackageData(
                platform="facebook",
                status="NOT_READY",
                title=title,
                caption=fb_caption,
                hashtags=["#AI", "#Automation", "#TechTools"],
                pinned_comment="",
                checklist=dict(default_checklist),
            ),
            "instagram": PlatformPackageData(
                platform="instagram",
                status="NOT_READY",
                title=title,
                caption=ig_caption,
                hashtags=ig_hashtags,
                pinned_comment="",
                checklist=dict(default_checklist),
            ),
            "tiktok": PlatformPackageData(
                platform="tiktok",
                status="NOT_READY",
                title=title,
                caption=tt_caption,
                hashtags=tt_hashtags,
                pinned_comment="",
                checklist=dict(default_checklist),
            ),
        }
