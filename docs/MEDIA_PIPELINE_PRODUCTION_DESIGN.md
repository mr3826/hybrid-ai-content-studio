# Production Media Pipeline Design

## Scope

Complete the existing media engine without changing the single-brand/single-niche model or coupling the UI to engine internals. Production output must contain a real installed offline voice, one validated local visual asset per ordered scene, and a valid FFmpeg MP4 verified with FFprobe. Missing requirements fail closed.

## Decisions

- The media adapter resolves scene assets only beneath `data/assets`; it accepts supported image/video formats and rasterizes SVG through an installed headless browser after rejecting scripts and external references.
- Windows narration uses an explicitly installed SAPI5 voice name and reports the installed cultures. Harmonic synthesis is available only when mock mode is explicitly selected and remains marked as mock through the media package.
- FFmpeg composes each scene in `scene_order`, preserves source aspect ratio with padding, holds a scene through its measured narration and configured silence gap, and burns requested subtitles in the same required render. A caption/filter failure fails the render.
- FFprobe verifies the resulting container, streams, codecs, dimensions, and measured duration. A successful FFmpeg exit alone does not make a package ready.
- The Media Studio sends production synthesis/render actions to the existing local SQLite worker. Existing API engine contracts remain the boundary; worker persistence records `SYNTHESIZED`, `READY`, `MOCK`, or `FAILED` package states.
- Final QC requires verified, production-eligible media when a media package exists. Export checks the current package in addition to the existing PR #1 approval checks, so stale approval cannot export a failed or mock render.

## Verification

Regression coverage will exercise distinct scene assets, invalid/missing inputs and tools, SAPI unavailable/unsupported voices, mandatory caption failures, real FFprobe output, both aspect ratios, measured duration mismatch, worker failure persistence, and QC/export blocking. A separate Windows smoke run will use an installed SAPI5 voice and local FFmpeg/FFprobe; a mock artifact is not production evidence.
