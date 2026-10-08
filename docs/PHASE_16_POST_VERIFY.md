# Phase 16 Verification Audit — Voice, Subtitle & Media Engine

## 1. Executive Summary
Phase 16 implements the **Voice, Subtitle & Media Engine** (`media`), transforming validated storyboard scenes and scripts into master narration audio, timed captions, and a verified MP4. Production narration uses installed Windows SAPI5 voices with no paid audio/video API dependency. Harmonic synthesis is explicitly labeled mock output for isolated tests only.

All studio invariants were strictly preserved:
- **Single Niche & Single Brand:** Operates within the active niche and brand profile context.
- **Engine Independence:** Decoupled contracts (`contracts.py`), rulebook (`rules.yaml`), manifest (`manifest.yaml`), deterministic offline adapters (`adapters.py`), and test harness.
- **Offline Speech:** Uses real installed SAPI5 voices and reports actual voice names and language cultures. Missing or unsupported voices fail without a synthetic-speech fallback.
- **Topic-Specific Visuals:** Requires one validated local image, video, or SVG asset per scene, preserves scene order, and keeps source aspect ratios with padding. SVG is rasterized through installed Edge or Chrome after active and external content checks.
- **Verified Composition:** FFmpeg renders the requested aspect ratio; FFprobe verifies the MP4 container, H.264/AAC streams, dimensions, frame rate, and measured stream durations. Missing FFmpeg/FFprobe or any required caption failure stops the render.
- **Bilingual Interface:** Fully localized in both English and Bangla.
- **Zero CI/CD & Zero n8n:** Pure local-first architecture with SQLite WAL mode.

---

## 2. Core Components & Capabilities

### A. Offline System Speech
- Windows SAPI5 voice enumeration returns the real installed voice names, genders, and cultures.
- Synthesis selects the requested installed voice, normalizes its WAV output to mono 44.1kHz PCM, and records measured per-scene durations.
- Missing voices and unsupported languages are reported directly. Production rendering never substitutes harmonic tones for speech.
- Harmonic output remains available only when mock mode is explicitly selected and is labeled `MOCK` in the media package.

### B. Timed Captions & Subtitles
- Generates valid `.srt` (SubRip) and `.vtt` (WebVTT) files.
- Automatically splits scene narrations into readable word chunks based on the visual layout preset (4 words per chunk for 9:16 vertical shorts, 8 words per chunk for 16:9 landscape).
- Uses measured scene narration durations and silence gaps for scene boundaries. Word-level cue timing is proportional, not forced-aligned, and this limitation is returned with each subtitle package.

### C. Local FFmpeg Media Adapter
- Resolves each scene's own asset beneath `data/assets`; there is no unrelated demo-image or blank-canvas fallback.
- Accepts supported raster images and local video assets. SVG assets are validated and rasterized with installed Edge or Chrome.
- Preserves scene order, uses measured narration timing, and applies scale/padding to avoid distorting visuals.
- Requires system FFmpeg and FFprobe. Requested subtitle burn-in is mandatory; a filter failure is reported without a caption-free retry.
- Failed and invalid output files are removed and cannot become `READY`.
- Resolution presets:
  - Vertical 9:16: 1080x1920 (Shorts, Reels, TikTok)
  - Horizontal 16:9: 1920x1080 (YouTube, Desktop)
- Subtitle burn-in support (`burn_subtitles`).

---

## 3. Database Schema & Migration
- **Alembic Revision:** `4d5e6f7a8b9c` (`create_media_packages_tables`)
- **Tables Created:**
  - `media_packages`: Encapsulates master audio, subtitle path, video path, timeline, resolution preset, status (`draft`, `synthesizing`, `synthesized`, `rendering`, `ready`, `mock`, `failed`), voice provenance, and quality report.
  - `scene_voice_tracks`: Tracks individual scene audio WAV files, voice profile, duration, word count, and normalized waveform peaks.
- **Foreign Keys & Indices:**
  - Foreign key to `scripts(id)` with cascade deletion.
  - Foreign key to `scenes(id)` on set null.
  - Indexed on `script_id`, `scene_id`, `status`.

---

## 4. API Endpoints
All endpoints are registered under `/api/v1/media`:

- `GET /api/v1/media/voices`: Actual installed SAPI5 voices and supported/unavailable language cultures.
- `GET /api/v1/media/script/{script_id}`: Active media package and all associated scene voice tracks.
- `POST /api/v1/media/voice/{script_id}`: Synthesize voice tracks for all scenes in a script.
- `POST /api/v1/media/subtitles/{script_id}`: Generate synchronized SRT and VTT subtitle files.
- `GET /api/v1/media/subtitles/{script_id}/file`: Raw caption download stream (`.srt` / `.vtt`).
- `POST /api/v1/media/render/{script_id}`: Render final video composition via FFmpeg.
- `POST /api/v1/media/jobs/{script_id}`: Queue local synthesis/render work for the Python worker.

---

## 5. Frontend & UI Verification
- **Route:** `/media-studio`
- **Navigation:** Integrated in studio sidebar with `Headphones` icon.
- **Bilingual Support:** Complete Bangla (`bn`) and English (`en`) dictionary keys under `mediaStudioPage`.
- **Three-Module Studio Layout:**
  - **Module A (Voice Synthesizer):** Voice profile selection, speech speed slider (0.8x - 1.3x), track cards with interactive 32-bar SVG waveform visualizer, and total duration monitor.
  - **Module B (Subtitle Studio):** Format selector (SRT/VTT), words-per-cue density slider, one-click clipboard copy with feedback, and live timecode cue inspection cards.
  - **Module C (Video Assembly & Render):** 9:16 vs 16:9 aspect ratio toggle, subtitle burn-in toggle, FFmpeg composition trigger, video path inspector, and quality report summary.

---

## 6. Verification Test Results
- **Engine Unit Tests:** `apps/api/tests/test_media_engine.py` (5/5 passed)
- **API Integration Tests:** `apps/api/tests/test_media_api.py` (1/1 passed)
- **Full Backend Suite:** 80/80 passed (`.\.venv\Scripts\pytest`)
- **Frontend Production Build:** `apps/web` compiled with 0 TypeScript errors (`npm run build`).
