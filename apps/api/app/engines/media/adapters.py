from datetime import datetime, timezone
from array import array
import base64
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple
import wave
import xml.etree.ElementTree as ET

from app.core.config import settings
from app.engines.media.contracts import (
    MediaRenderConfigRequest,
    MediaRenderOutput,
    SceneMediaInput,
    SubtitleConfigRequest,
    SubtitleCueOutput,
    SubtitleGenerationOutput,
    VoiceConfigRequest,
    VoiceTrackOutput,
)

logger = logging.getLogger("studio.engines.media.adapters")


class MediaPipelineError(RuntimeError):
    """A production media step failed with a user-actionable diagnostic."""

    def __init__(self, message: str, stage: str):
        super().__init__(message)
        self.stage = stage


class TTSUnavailableError(MediaPipelineError):
    def __init__(self, message: str):
        super().__init__(message, stage="voice")


class UnsupportedVoiceError(MediaPipelineError):
    def __init__(self, message: str):
        super().__init__(message, stage="voice")


class AssetUnavailableError(MediaPipelineError):
    def __init__(self, message: str):
        super().__init__(message, stage="assets")


class MediaRenderError(MediaPipelineError):
    def __init__(self, message: str, stage: str = "render"):
        super().__init__(message, stage=stage)


class LocalAudioSynthesizer:
    """Local audio synthesizer producing valid 44.1kHz 16-bit PCM WAV tracks.
    Supports fast deterministic harmonic synthesis (mock mode) and offline system speech synthesis.
    Operates 100% offline with zero external paid API dependencies.
    """

    def __init__(self, output_dir: str = "data/assets/audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._voice_catalog: Optional[Dict[str, Any]] = None

    @staticmethod
    def _run_powershell(script: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
        """Run a fixed, base64-encoded PowerShell script without shell interpolation."""
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if not powershell:
            raise TTSUnavailableError("Windows PowerShell is unavailable; Windows SAPI5 narration cannot run.")
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            return subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TTSUnavailableError(f"Windows SAPI5 process failed: {exc}") from exc

    def get_voice_catalog(self) -> Dict[str, Any]:
        """Return the actual enabled voices installed in Windows SAPI5."""
        if self._voice_catalog is not None:
            return self._voice_catalog
        if sys.platform != "win32":
            self._voice_catalog = {
                "available": False,
                "default_voice_id": None,
                "voices": [],
                "supported_languages": [],
                "unavailable_languages": ["en-US", "bn-BD"],
                "message": "Windows SAPI5 is available only on Windows.",
            }
            return self._voice_catalog

        script = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $voices = @($s.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object {
    [pscustomobject]@{
      id = $_.VoiceInfo.Name
      name = $_.VoiceInfo.Name
      locale = $_.VoiceInfo.Culture.Name
      gender = $_.VoiceInfo.Gender.ToString()
      age = $_.VoiceInfo.Age.ToString()
    }
  })
  $result = [pscustomobject]@{ default_voice_id = $s.Voice.Name; voices = $voices }
  ConvertTo-Json -InputObject $result -Depth 5 -Compress
} finally { $s.Dispose() }
"""
        try:
            proc = self._run_powershell(script)
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout or "SAPI5 voice enumeration failed.").strip()[-500:]
                self._voice_catalog = {
                    "available": False,
                    "default_voice_id": None,
                    "voices": [],
                    "supported_languages": [],
                    "unavailable_languages": ["en-US", "bn-BD"],
                    "message": detail,
                }
                return self._voice_catalog
            parsed = json.loads(proc.stdout.strip() or "{}")
            voices = parsed.get("voices") or []
            if isinstance(voices, dict):
                voices = [voices]
            languages = sorted({str(voice.get("locale", "")) for voice in voices if voice.get("locale")})
            self._voice_catalog = {
                "available": bool(voices),
                "default_voice_id": parsed.get("default_voice_id"),
                "voices": voices,
                "supported_languages": languages,
                "unavailable_languages": [lang for lang in ("en-US", "bn-BD") if lang not in languages],
                "message": "" if voices else "Windows SAPI5 is installed but has no enabled voices.",
            }
            return self._voice_catalog
        except (TTSUnavailableError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self._voice_catalog = {
                "available": False,
                "default_voice_id": None,
                "voices": [],
                "supported_languages": [],
                "unavailable_languages": ["en-US", "bn-BD"],
                "message": str(exc),
            }
            return self._voice_catalog

    @staticmethod
    def _resample_mono_pcm(samples: array, source_rate: int, target_rate: int) -> array:
        """Convert mono signed 16-bit PCM to the requested rate using linear interpolation."""
        if source_rate == target_rate or not samples:
            return samples
        output_count = max(1, round(len(samples) * target_rate / source_rate))
        converted = array("h")
        max_index = len(samples) - 1
        for index in range(output_count):
            source_position = index * source_rate / target_rate
            left = min(int(source_position), max_index)
            right = min(left + 1, max_index)
            fraction = source_position - left
            value = round(samples[left] + (samples[right] - samples[left]) * fraction)
            converted.append(max(-32768, min(32767, value)))
        return converted

    @staticmethod
    def _generate_waveform_peaks(samples: List[int], count: int = 50) -> List[float]:
        """Extracts normalized peak points for audio waveform visualization."""
        if not samples:
            return [0.0] * count
        step = max(1, len(samples) // count)
        peaks = []
        for p_idx in range(count):
            chunk = samples[p_idx * step : (p_idx + 1) * step]
            peak = max([abs(s) for s in chunk], default=0) / 32768.0
            peaks.append(round(min(1.0, peak * 1.2), 3))
        return peaks

    def _synthesize_harmonic_pcm(
        self,
        scene_id: str,
        narration: str,
        target_duration_sec: float,
        config: VoiceConfigRequest,
    ) -> VoiceTrackOutput:
        """Deterministic 44.1kHz 16-bit PCM WAV synthesis with acoustic harmonic modulation."""
        sample_rate = config.sample_rate
        speed = max(0.5, min(2.0, config.speed))
        duration = max(1.0, round(target_duration_sec / speed, 2))

        num_samples = int(sample_rate * duration)
        words = narration.strip().split()
        word_count = len(words)

        # Profile-based fundamental pitch
        voice_id = config.voice_id.lower()
        if "authoritative" in voice_id:
            base_pitch = 110.0
        elif "casual" in voice_id:
            base_pitch = 175.0
        elif "bn-bd" in voice_id or "bangla" in voice_id:
            base_pitch = 135.0
        else:
            base_pitch = 145.0

        # Subtle seed variation per scene
        hash_val = int(hashlib.md5(scene_id.encode("utf-8")).hexdigest()[:6], 16)
        base_freq = base_pitch + (hash_val % 25) + (config.pitch * 4.0)

        samples: List[int] = []
        envelope_len = int(sample_rate * 0.05)  # 50ms fade
        cadence_freq = max(1.5, word_count / duration)

        for i in range(num_samples):
            t = i / sample_rate

            # Smooth fade in and fade out
            amp = 0.5
            if i < envelope_len:
                amp *= 0.5 * (1.0 - math.cos(math.pi * i / envelope_len))
            elif i > num_samples - envelope_len:
                amp *= 0.5 * (1.0 - math.cos(math.pi * (num_samples - i) / envelope_len))

            # Speech cadence modulation
            speech_mod = 0.4 + 0.6 * math.sin(2.0 * math.pi * cadence_freq * t) ** 2

            # Vocal harmonic timbre (Fundamental + 2nd, 3rd, 4th harmonics)
            val = (
                0.50 * math.sin(2.0 * math.pi * base_freq * t)
                + 0.30 * math.sin(2.0 * math.pi * base_freq * 2.0 * t)
                + 0.15 * math.sin(2.0 * math.pi * base_freq * 3.0 * t)
                + 0.05 * math.sin(2.0 * math.pi * base_freq * 4.0 * t)
            )

            sample_val = int(val * amp * speech_mod * 32767.0 * 0.75)
            sample_val = max(-32768, min(32767, sample_val))
            samples.append(sample_val)

        # Write WAV file
        clean_scene_id = re.sub(r"[^a-zA-Z0-9_-]", "_", scene_id)
        out_filename = f"voice_scene_{clean_scene_id}.wav"
        out_path = self.output_dir / out_filename
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            raw_bytes = struct.pack(f"<{len(samples)}h", *samples)
            wf.writeframes(raw_bytes)

        peaks = self._generate_waveform_peaks(samples, 50)

        return VoiceTrackOutput(
            scene_id=scene_id,
            audio_path=str(out_path).replace("\\", "/"),
            duration_sec=duration,
            word_count=word_count,
            waveform_peaks=peaks,
            synthesis_mode="mock_harmonic",
            is_mock=True,
        )

    def _synthesize_offline_system_tts(
        self,
        scene_id: str,
        narration: str,
        target_duration_sec: float,
        config: VoiceConfigRequest,
    ) -> Optional[VoiceTrackOutput]:
        """Synthesizes real speech using an installed Windows SAPI5 voice."""
        clean_scene_id = re.sub(r"[^a-zA-Z0-9_-]", "_", scene_id)
        out_filename = f"voice_scene_{clean_scene_id}.wav"
        out_path = (self.output_dir / out_filename).resolve()
        catalog = self.get_voice_catalog()
        voices = catalog["voices"]
        if not catalog["available"]:
            detail = catalog.get("message") or "No enabled Windows SAPI5 voices are installed."
            raise TTSUnavailableError(f"Real offline narration is unavailable: {detail}")

        requested_voice = config.voice_id.strip() or str(catalog.get("default_voice_id") or "")
        voice = next((entry for entry in voices if entry.get("id") == requested_voice), None)
        if voice is None:
            installed = ", ".join(f"{entry['name']} ({entry['locale']})" for entry in voices)
            requested_language_match = re.match(r"^[a-z]{2,3}-[A-Z]{2,4}", requested_voice)
            requested_language = requested_language_match.group(0) if requested_language_match else requested_voice
            raise UnsupportedVoiceError(
                f"Windows SAPI5 voice '{requested_voice}' is not installed. Available voices: {installed}. "
                f"Available languages: {', '.join(catalog['supported_languages']) or 'none'}; "
                f"{requested_language} is unsupported on this host."
            )

        payload = {
            "text": narration,
            "voice_name": voice["id"],
            "output_path": str(out_path),
            "rate": int(max(-10, min(10, round((config.speed - 1.0) * 10)))),
        }
        payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        script = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$payloadJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{payload_b64}'))
$payload = ConvertFrom-Json -InputObject $payloadJson
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{
  $s.SelectVoice([string]$payload.voice_name)
  $s.Rate = [int]$payload.rate
  $s.SetOutputToWaveFile([string]$payload.output_path)
  $s.Speak([string]$payload.text)
  $s.SetOutputToNull()
}} catch {{
  [Console]::Error.WriteLine($_.Exception.Message)
  exit 1
}} finally {{ $s.Dispose() }}
"""
        proc = self._run_powershell(script, timeout=60)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "SAPI5 did not produce narration.").strip()[-800:]
            raise TTSUnavailableError(f"Windows SAPI5 failed to synthesize narration: {detail}")
        if not out_path.exists() or out_path.stat().st_size <= 100:
            raise TTSUnavailableError("Windows SAPI5 returned without creating a valid WAV narration track.")

        try:
            with wave.open(str(out_path), "rb") as wf:
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                source_rate = wf.getframerate()
                raw_data = wf.readframes(wf.getnframes())
        except (wave.Error, OSError) as exc:
            raise TTSUnavailableError(f"Windows SAPI5 produced an invalid WAV file: {exc}") from exc
        if sampwidth != 2 or channels < 1 or source_rate <= 0:
            raise TTSUnavailableError(
                f"Windows SAPI5 produced unsupported PCM format: {channels} channels, {sampwidth * 8}-bit, {source_rate} Hz."
            )

        source_samples = array("h")
        source_samples.frombytes(raw_data[: len(raw_data) - (len(raw_data) % (2 * channels))])
        if sys.byteorder != "little":
            source_samples.byteswap()
        mono_samples = array("h")
        for frame_start in range(0, len(source_samples), channels):
            frame = source_samples[frame_start : frame_start + channels]
            mono_samples.append(round(sum(frame) / channels))
        normalized_samples = self._resample_mono_pcm(mono_samples, source_rate, config.sample_rate)
        if not normalized_samples:
            raise TTSUnavailableError("Windows SAPI5 produced an empty narration track.")
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(config.sample_rate)
            wf.writeframes(normalized_samples.tobytes())

        peaks = self._generate_waveform_peaks(list(normalized_samples), 50)
        actual_duration = len(normalized_samples) / config.sample_rate
        return VoiceTrackOutput(
            scene_id=scene_id,
            audio_path=str(out_path).replace("\\", "/"),
            duration_sec=round(actual_duration, 3),
            word_count=len(narration.strip().split()),
            waveform_peaks=peaks,
            synthesis_mode="windows_sapi5",
            is_mock=False,
        )

    def synthesize_scene_audio(
        self,
        scene_id: str,
        narration: str,
        target_duration_sec: float,
        config: VoiceConfigRequest,
    ) -> VoiceTrackOutput:
        """Synthesize real SAPI5 speech, or explicitly labeled test/mock audio."""
        is_mock = config.mock_mode if config.mock_mode is not None else settings.TTS_MOCK_MODE

        if is_mock:
            return self._synthesize_harmonic_pcm(
                scene_id=scene_id,
                narration=narration,
                target_duration_sec=target_duration_sec,
                config=config,
            )
        return self._synthesize_offline_system_tts(
            scene_id=scene_id,
            narration=narration,
            target_duration_sec=target_duration_sec,
            config=config,
        )

    def stitch_master_audio(
        self,
        script_id: str,
        tracks: List[VoiceTrackOutput],
        silence_gap_sec: float = 0.2,
        sample_rate: int = 44100,
    ) -> Tuple[str, float]:
        """Combines scene audio tracks into a master narration audio track."""
        gap_samples = int(sample_rate * silence_gap_sec)
        gap_bytes = struct.pack(f"<{gap_samples}h", *([0] * gap_samples))

        master_filename = f"master_{script_id[:8]}.wav"
        master_path = self.output_dir / master_filename

        total_frames = 0
        with wave.open(str(master_path), "wb") as out_wf:
            out_wf.setnchannels(1)
            out_wf.setsampwidth(2)
            out_wf.setframerate(sample_rate)

            for idx, track in enumerate(tracks):
                track_file = Path(track.audio_path)
                if track_file.exists():
                    try:
                        with wave.open(str(track_file), "rb") as in_wf:
                            in_rate = in_wf.getframerate()
                            data = in_wf.readframes(in_wf.getnframes())
                            channels = in_wf.getnchannels()
                            sample_width = in_wf.getsampwidth()
                            if sample_width != 2 or channels < 1 or in_rate <= 0:
                                raise TTSUnavailableError(f"Unsupported PCM format in {track_file}.")
                            samples = array("h")
                            samples.frombytes(data[: len(data) - (len(data) % (2 * channels))])
                            if sys.byteorder != "little":
                                samples.byteswap()
                            mono = array("h")
                            for frame_start in range(0, len(samples), channels):
                                mono.append(round(sum(samples[frame_start : frame_start + channels]) / channels))
                            normalized = self._resample_mono_pcm(mono, in_rate, sample_rate)
                            out_wf.writeframes(normalized.tobytes())
                            total_frames += len(normalized)
                    except Exception as e:
                        raise TTSUnavailableError(f"Could not read scene narration {track.audio_path}: {e}") from e
                else:
                    raise TTSUnavailableError(f"Scene narration WAV is missing: {track.audio_path}")

                # Add silence gap between scenes (except after last scene)
                if idx < len(tracks) - 1 and silence_gap_sec > 0:
                    out_wf.writeframes(gap_bytes)
                    total_frames += gap_samples

        total_duration = round(total_frames / sample_rate, 2)
        return str(master_path).replace("\\", "/"), total_duration

    @staticmethod
    def get_audio_peak_db(audio_path: str) -> float:
        """Measures peak audio level in decibels relative to full scale (dBFS)."""
        p = Path(audio_path)
        if not p.exists():
            return -1.0
        try:
            with wave.open(str(p), "rb") as wf:
                nframes = wf.getnframes()
                sampwidth = wf.getsampwidth()
                if sampwidth != 2 or nframes == 0:
                    return -1.0
                raw = wf.readframes(min(nframes, 44100 * 5))  # Sample first 5 seconds
                samples = struct.unpack(f"<{len(raw)//2}h", raw)
                peak = max([abs(s) for s in samples], default=0)
                if peak <= 0:
                    return -60.0
                db = 20.0 * math.log10(peak / 32768.0)
                return round(max(-60.0, min(0.0, db)), 1)
        except Exception:
            return -1.2


class SubtitleAdapter:
    """Synchronized SubRip (.srt) and WebVTT (.vtt) caption generator with pacing metrics."""

    def __init__(self, output_dir: str = "data/assets/subtitles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _format_timestamp(seconds: float, vtt: bool = False) -> str:
        """Converts float seconds to 00:00:00,000 (SRT) or 00:00:00.000 (VTT)."""
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis >= 1000:
            seconds += 1.0
            millis = 0
        total_sec = int(seconds)
        s = total_sec % 60
        m = (total_sec // 60) % 60
        h = total_sec // 3600
        sep = "." if vtt else ","
        return f"{h:02d}:{m:02d}:{s:02d}{sep}{millis:03d}"

    def generate_subtitles(
        self,
        script_id: str,
        scenes: List[SceneMediaInput],
        track_durations: Optional[Dict[str, float]] = None,
        config: Optional[SubtitleConfigRequest] = None,
        silence_gap_sec: float = 0.2,
    ) -> SubtitleGenerationOutput:
        """Generates synchronized subtitle cues matching scene audio durations and silence gaps."""
        cfg = config or SubtitleConfigRequest()
        max_words = cfg.max_words_per_line
        gap = cfg.silence_gap_sec
        ordered_scenes = sorted(scenes, key=lambda scene: scene.scene_order)
        has_all_measured_durations = bool(track_durations) and all(
            scene.id in track_durations and track_durations[scene.id] > 0 for scene in ordered_scenes
        )
        has_some_measured_durations = bool(track_durations) and any(
            scene.id in track_durations and track_durations[scene.id] > 0 for scene in ordered_scenes
        )
        if has_all_measured_durations:
            timing_method = "proportional_to_measured_scene_audio"
            timing_limitation = (
                "Scene boundaries use measured narration durations and configured silence gaps. "
                "Word-level cue times are proportional estimates; forced alignment is not available."
            )
        elif has_some_measured_durations:
            timing_method = "mixed_measured_and_storyboard_estimates"
            timing_limitation = (
                "Some scene boundaries use measured narration durations; missing tracks use storyboard estimates. "
                "Word-level cue times are proportional estimates; forced alignment is not available."
            )
        else:
            timing_method = "proportional_to_storyboard_estimates"
            timing_limitation = (
                "Scene and word-level cue times use proportional storyboard estimates; "
                "forced alignment is not available."
            )

        cues: List[SubtitleCueOutput] = []
        current_time = 0.0
        cue_idx = 1

        for s_idx, scene in enumerate(ordered_scenes):
            # Account for silence gap before scene if not first scene
            if s_idx > 0 and gap > 0:
                current_time += gap

            scene_duration = (
                track_durations.get(scene.id, scene.timing_estimate)
                if track_durations
                else scene.timing_estimate
            )
            if scene_duration <= 0:
                raise MediaPipelineError(f"Scene {scene.id} has no usable narration duration.", stage="subtitles")
            words = scene.narration.strip().split()
            if not words:
                current_time += scene_duration
                continue

            # Split into word chunks
            chunks = []
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i : i + max_words]))

            # Proportional duration allocation per chunk
            total_words = len(words)
            for chunk in chunks:
                chunk_words = len(chunk.split())
                chunk_chars = len(chunk)
                chunk_duration = scene_duration * (chunk_words / max(1, total_words))

                start_sec = current_time
                end_sec = start_sec + chunk_duration

                cps = round(chunk_chars / max(0.1, chunk_duration), 1)
                wpm = round((chunk_words / max(0.1, chunk_duration)) * 60, 1)

                cue = SubtitleCueOutput(
                    index=cue_idx,
                    start_sec=round(start_sec, 3),
                    end_sec=round(end_sec, 3),
                    start_timestamp=self._format_timestamp(start_sec, vtt=(cfg.format == "vtt")),
                    end_timestamp=self._format_timestamp(end_sec, vtt=(cfg.format == "vtt")),
                    text=chunk,
                    scene_id=scene.id,
                    cps=cps,
                    wpm=wpm,
                )
                cues.append(cue)
                cue_idx += 1
                current_time = end_sec

        # Pacing calculations
        avg_cps = round(sum(c.cps for c in cues) / max(1, len(cues)), 1) if cues else 0.0
        max_cps = max([c.cps for c in cues], default=0.0)
        pacing_status = "FAST" if avg_cps > 22.0 else ("SLOW" if avg_cps < 8.0 else "OPTIMAL")

        # Format subtitle string
        if cfg.format == "vtt":
            lines = ["WEBVTT\n"]
            for cue in cues:
                lines.append(f"{cue.index}\n{cue.start_timestamp} --> {cue.end_timestamp}\n{cue.text}\n")
            content_text = "\n".join(lines)
            ext = ".vtt"
        else:
            lines = []
            for cue in cues:
                lines.append(f"{cue.index}\n{cue.start_timestamp} --> {cue.end_timestamp}\n{cue.text}\n")
            content_text = "\n".join(lines)
            ext = ".srt"

        safe_script_id = re.sub(r"[^a-zA-Z0-9_-]", "_", script_id[:40])
        out_path = self.output_dir / f"subtitles_{safe_script_id[:8]}{ext}"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content_text)

        return SubtitleGenerationOutput(
            script_id=script_id,
            subtitle_path=str(out_path).replace("\\", "/"),
            content_text=content_text,
            cue_count=len(cues),
            format=cfg.format,
            cues=cues,
            avg_cps=avg_cps,
            max_cps=max_cps,
            pacing_status=pacing_status,
            timing_method=timing_method,
            timing_limitation=timing_limitation,
        )


class FFmpegMediaAdapter:
    """Compose verified scene assets and narration into a real MP4 using local tools."""

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".gif"}
    SVG_MAX_BYTES = 10 * 1024 * 1024
    MAX_PROBE_DIAGNOSTIC_CHARS = 1000

    def __init__(
        self,
        output_dir: str = "data/assets/video",
        asset_root: str = "data/assets",
        svg_renderer_path: Optional[str] = None,
    ):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.asset_root = Path(asset_root).resolve()
        configured_ffmpeg = str(getattr(settings, "FFMPEG_BINARY", "ffmpeg"))
        self.ffmpeg_path = shutil.which(configured_ffmpeg) or shutil.which("ffmpeg")
        self.ffprobe_path = self._find_ffprobe()
        self.svg_renderer_path = svg_renderer_path or self._find_svg_renderer()
        self._ffmpeg_version: Optional[str] = None
        self._ffprobe_version: Optional[str] = None

    def _find_ffprobe(self) -> Optional[str]:
        ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
        if self.ffmpeg_path:
            adjacent = Path(self.ffmpeg_path).with_name(ffprobe_name)
            if adjacent.is_file():
                return str(adjacent)
        return shutil.which(ffprobe_name) or shutil.which("ffprobe")

    @staticmethod
    def _find_svg_renderer() -> Optional[str]:
        for name in ("msedge.exe", "msedge", "chrome.exe", "chrome", "chromium.exe", "chromium"):
            found = shutil.which(name)
            if found:
                return found
        if os.name == "nt":
            for env_name, suffix in (
                ("ProgramFiles(x86)", "Microsoft/Edge/Application/msedge.exe"),
                ("ProgramFiles", "Microsoft/Edge/Application/msedge.exe"),
                ("ProgramFiles", "Google/Chrome/Application/chrome.exe"),
            ):
                base = os.environ.get(env_name)
                if base:
                    candidate = Path(base) / suffix
                    if candidate.is_file():
                        return str(candidate)
        return None

    def has_ffmpeg(self) -> bool:
        return bool(self.ffmpeg_path)

    def has_ffprobe(self) -> bool:
        return bool(self.ffprobe_path)

    def get_ffmpeg_version(self) -> str:
        if not self.has_ffmpeg():
            return "Unavailable"
        if self._ffmpeg_version:
            return self._ffmpeg_version
        try:
            res = subprocess.run([self.ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5, check=False)
            self._ffmpeg_version = res.stdout.splitlines()[0].strip() if res.stdout else "Available"
        except (OSError, subprocess.TimeoutExpired):
            self._ffmpeg_version = "Available"
        return self._ffmpeg_version

    def get_ffprobe_version(self) -> str:
        if not self.has_ffprobe():
            return "Unavailable"
        if self._ffprobe_version:
            return self._ffprobe_version
        try:
            res = subprocess.run([self.ffprobe_path, "-version"], capture_output=True, text=True, timeout=5, check=False)
            self._ffprobe_version = res.stdout.splitlines()[0].strip() if res.stdout else "Available"
        except (OSError, subprocess.TimeoutExpired):
            self._ffprobe_version = "Available"
        return self._ffprobe_version

    def _resolve_asset(self, raw_path: Optional[str], label: str) -> Path:
        if not raw_path or not raw_path.strip():
            raise AssetUnavailableError(f"{label} is missing; attach a local asset before rendering.")
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = candidate if candidate.exists() else self.asset_root / candidate
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise AssetUnavailableError(f"{label} was not found: {raw_path}") from exc
        try:
            resolved.relative_to(self.asset_root)
        except ValueError as exc:
            raise AssetUnavailableError(f"{label} must be inside the local asset directory: {self.asset_root}") from exc
        if not resolved.is_file():
            raise AssetUnavailableError(f"{label} is not a file: {raw_path}")
        return resolved

    def _probe_file(self, path: Path, label: str) -> Dict[str, Any]:
        if not self.has_ffprobe():
            raise MediaRenderError("FFprobe is not installed or available on PATH; output cannot be verified.", stage="verification")
        try:
            proc = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v", "error",
                    "-show_entries", "format=format_name,duration:stream=codec_type,codec_name,width,height,duration,avg_frame_rate,sample_rate,channels",
                    "-of", "json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MediaRenderError(f"FFprobe could not inspect {label}: {exc}", stage="verification") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "no diagnostic returned").strip()[-self.MAX_PROBE_DIAGNOSTIC_CHARS :]
            raise MediaRenderError(f"FFprobe rejected {label}: {detail}", stage="verification")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise MediaRenderError(f"FFprobe returned invalid metadata for {label}.", stage="verification") from exc

    @staticmethod
    def _stream_duration(stream: Dict[str, Any], format_data: Dict[str, Any]) -> float:
        raw_duration = stream.get("duration") or format_data.get("duration")
        try:
            duration = float(raw_duration)
        except (TypeError, ValueError):
            return 0.0
        return duration if math.isfinite(duration) and duration > 0 else 0.0

    @staticmethod
    def _parse_frame_rate(raw_value: Any) -> Optional[float]:
        if not isinstance(raw_value, str) or "/" not in raw_value:
            return None
        numerator, denominator = raw_value.split("/", 1)
        try:
            divisor = float(denominator)
            return float(numerator) / divisor if divisor else None
        except ValueError:
            return None

    def _validate_svg(self, path: Path) -> None:
        if path.stat().st_size > self.SVG_MAX_BYTES:
            raise AssetUnavailableError(f"SVG asset exceeds the {self.SVG_MAX_BYTES // (1024 * 1024)} MiB size limit: {path.name}")
        content = path.read_bytes()
        lowered = content.lower()
        if b"<!doctype" in lowered or b"<!entity" in lowered:
            raise AssetUnavailableError(f"SVG asset contains a forbidden document type or entity declaration: {path.name}")
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise AssetUnavailableError(f"SVG asset is malformed: {path.name}: {exc}") from exc
        if root.tag.split("}")[-1].lower() != "svg":
            raise AssetUnavailableError(f"Asset is not an SVG document: {path.name}")

        url_pattern = re.compile(r"url\(\s*['\"]?([^)'\"]+)", re.IGNORECASE)
        for element in root.iter():
            tag_name = element.tag.split("}")[-1].lower()
            if tag_name in {"script", "foreignobject", "iframe", "object", "embed"}:
                raise AssetUnavailableError(f"SVG asset contains disallowed active content ({tag_name}): {path.name}")
            values = list(element.attrib.values())
            if element.text:
                values.append(element.text)
            for attr_name, attr_value in element.attrib.items():
                local_attr = attr_name.split("}")[-1].lower()
                if local_attr.startswith("on"):
                    raise AssetUnavailableError(f"SVG asset contains an event handler: {path.name}")
                if local_attr in {"href", "src"} and attr_value:
                    value = attr_value.strip().lower()
                    if value.startswith("#"):
                        continue
                    if value.startswith("data:image/") and ";base64," in value:
                        continue
                    raise AssetUnavailableError(f"SVG external resource references are not allowed: {path.name}")
            for value in values:
                if "@import" in value.lower():
                    raise AssetUnavailableError(f"SVG external style imports are not allowed: {path.name}")
                for match in url_pattern.finditer(value):
                    reference = match.group(1).strip().lower()
                    if not reference.startswith("#") and not (
                        reference.startswith("data:image/") and ";base64," in reference
                    ):
                        raise AssetUnavailableError(f"SVG external resource references are not allowed: {path.name}")

    def _rasterize_svg(self, path: Path, temp_dir: Path, scene_id: str) -> Path:
        self._validate_svg(path)
        if not self.svg_renderer_path:
            raise MediaRenderError(
                "An installed headless Edge/Chrome browser is required to rasterize SVG scene assets.",
                stage="svg_rasterization",
            )
        clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", scene_id)[:48]
        png_path = temp_dir / f"scene_{clean_id}.png"
        profile_dir = temp_dir / f"browser_profile_{clean_id}"
        command = [
            self.svg_renderer_path,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            f"--user-data-dir={profile_dir}",
            "--window-size=1080,1920",
            "--force-device-scale-factor=1",
            f"--screenshot={png_path}",
            path.as_uri(),
        ]
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MediaRenderError(f"SVG rasterization failed for {path.name}: {exc}", stage="svg_rasterization") from exc
        # Edge/Chrome may hand off to its browser process and exit before the screenshot is written.
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if png_path.is_file() and png_path.stat().st_size >= 100:
                break
            time.sleep(0.1)
        if proc.returncode != 0 or not png_path.is_file() or png_path.stat().st_size < 100:
            detail = (proc.stderr or proc.stdout or f"browser did not create a PNG frame (exit code {proc.returncode})").strip()[-500:]
            raise MediaRenderError(f"SVG rasterization failed for {path.name}: {detail}", stage="svg_rasterization")
        if png_path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise MediaRenderError(f"SVG rasterization returned an invalid PNG for {path.name}.", stage="svg_rasterization")
        time.sleep(1.5)
        return png_path

    @staticmethod
    def _escape_path_for_ffmpeg(path: Path) -> str:
        """Escape a resolved local path for the FFmpeg subtitles filter."""
        escaped = str(path.resolve()).replace("\\", "/")
        return escaped.replace(":", r"\:").replace("'", r"\'")

    @staticmethod
    def _ass_timestamp(value: str) -> str:
        """Convert an SRT/VTT timestamp to ASS centisecond precision."""
        normalized = value.strip().replace(",", ".")
        parts = normalized.split(":")
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_part = parts[2]
        elif len(parts) == 2:
            hours = 0
            minutes = int(parts[0])
            seconds_part = parts[1]
        else:
            raise ValueError(f"Invalid subtitle timestamp: {value}")
        seconds_text, _, fraction = seconds_part.partition(".")
        seconds = int(seconds_text)
        centiseconds = int(round(float(f"0.{fraction or '0'}") * 100))
        total_centiseconds = ((hours * 60 + minutes) * 60 + seconds) * 100 + centiseconds
        hours, remainder = divmod(total_centiseconds, 360000)
        minutes, remainder = divmod(remainder, 6000)
        seconds, centiseconds = divmod(remainder, 100)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    @classmethod
    def _write_ass_subtitles(cls, source: Path, destination: Path, width: int, height: int) -> None:
        """Create resolution-aware ASS captions so SRT defaults cannot scale text over scenes."""
        try:
            content = source.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise MediaRenderError(f"Required subtitle file could not be read: {exc}", stage="subtitles") from exc

        timing_pattern = re.compile(
            r"^\s*(?P<start>(?:\d+:)?\d{1,2}:\d{2}[,.]\d{1,3})\s+-->\s+"
            r"(?P<end>(?:\d+:)?\d{1,2}:\d{2}[,.]\d{1,3})(?:\s+.*)?$"
        )
        cues = []
        for block in re.split(r"\r?\n\s*\r?\n", content.strip()):
            lines = block.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            timing_index = next((i for i, line in enumerate(lines) if timing_pattern.match(line)), None)
            if timing_index is None:
                continue
            timing_match = timing_pattern.match(lines[timing_index])
            if timing_match:
                cues.append((timing_match.group("start"), timing_match.group("end"), "\n".join(lines[timing_index + 1 :])))
        matches = cues
        if not matches:
            raise MediaRenderError("Required subtitle file contains no valid timed captions.", stage="subtitles")

        font_size = 42 if height >= width else 34
        vertical_margin = 120 if height >= width else 60
        ass_lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "ScaledBorderAndShadow: yes",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,3,1,0,2,60,60,{vertical_margin},1",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
        for start_value, end_value, body in matches:
            text = body.strip()
            text = re.sub(r"\n{2,}", "\n", text)
            if not text:
                continue
            # Prevent caption content from injecting ASS override commands.
            text = text.replace("\\", "＼").replace("{", "｛").replace("}", "｝").replace("\n", r"\N")
            try:
                start = cls._ass_timestamp(start_value)
                end = cls._ass_timestamp(end_value)
            except ValueError as exc:
                raise MediaRenderError(str(exc), stage="subtitles") from exc
            ass_lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

        if len(ass_lines) == 10:
            raise MediaRenderError("Required subtitle file contains no usable caption text.", stage="subtitles")
        destination.write_text("\n".join(ass_lines) + "\n", encoding="utf-8")

    def _validate_visual_asset(self, path: Path, label: str) -> None:
        """Probe each source before a looped FFmpeg input can hang on malformed media."""
        try:
            metadata = self._probe_file(path, label)
        except MediaPipelineError as exc:
            raise AssetUnavailableError(f"{label} is corrupt or not decodable: {exc}") from exc
        stream = next(
            (entry for entry in (metadata.get("streams") or []) if entry.get("codec_type") == "video"),
            None,
        )
        if not stream or int(stream.get("width") or 0) <= 0 or int(stream.get("height") or 0) <= 0:
            raise AssetUnavailableError(f"{label} has no decodable visual stream.")

    def _resolve_scene_sources(self, scenes: List[SceneMediaInput], temp_dir: Path) -> List[Tuple[SceneMediaInput, Path, str]]:
        resolved: List[Tuple[SceneMediaInput, Path, str]] = []
        for scene in sorted(scenes, key=lambda item: item.scene_order):
            source = self._resolve_asset(scene.visual_source, f"Visual asset for scene {scene.scene_order} ({scene.id})")
            extension = source.suffix.lower()
            if extension == ".svg":
                source = self._rasterize_svg(source, temp_dir, scene.id)
                self._validate_visual_asset(source, f"Rasterized visual asset for scene {scene.scene_order} ({scene.id})")
                resolved.append((scene, source, "image"))
            elif extension in self.IMAGE_EXTENSIONS:
                self._validate_visual_asset(source, f"Visual asset for scene {scene.scene_order} ({scene.id})")
                resolved.append((scene, source, "image"))
            elif extension in self.VIDEO_EXTENSIONS:
                self._validate_visual_asset(source, f"Visual asset for scene {scene.scene_order} ({scene.id})")
                resolved.append((scene, source, "video"))
            else:
                supported = ", ".join(sorted(self.IMAGE_EXTENSIONS | self.VIDEO_EXTENSIONS | {".svg"}))
                raise AssetUnavailableError(f"Unsupported scene asset format '{extension}' for {scene.id}. Supported: {supported}.")
        return resolved

    def _scene_durations(
        self,
        scenes: List[SceneMediaInput],
        audio_duration_sec: float,
        silence_gap_sec: float,
    ) -> Tuple[List[Tuple[SceneMediaInput, float]], str, float]:
        ordered = sorted(scenes, key=lambda item: item.scene_order)
        if not ordered:
            raise AssetUnavailableError("At least one scene with a local visual asset is required.")
        if any(scene.timing_estimate <= 0 for scene in ordered):
            raise MediaRenderError("Every scene must have a positive timing estimate.", stage="timeline")

        gaps_duration = silence_gap_sec * max(0, len(ordered) - 1)
        available_scene_duration = audio_duration_sec - gaps_duration
        if available_scene_duration <= 0:
            raise MediaRenderError("Narration is shorter than the configured scene silence gaps.", stage="timeline")

        measured = [scene.actual_audio_duration_sec for scene in ordered]
        missing_count = sum(1 for value in measured if value is None)
        if missing_count == 0:
            scene_durations = [float(value) for value in measured if value is not None]
            method = "measured_per_scene_audio"
        else:
            known_total = sum(float(value) for value in measured if value is not None)
            missing_time = available_scene_duration - known_total
            if missing_time <= 0:
                raise MediaRenderError("Measured scene narration durations exceed the master audio duration.", stage="timeline")
            missing_weights = sum(
                scene.timing_estimate for scene, value in zip(ordered, measured) if value is None
            )
            scene_durations = []
            for scene, value in zip(ordered, measured):
                if value is not None:
                    scene_durations.append(float(value))
                else:
                    scene_durations.append(missing_time * scene.timing_estimate / missing_weights)
            method = "mixed_measured_and_storyboard_estimates" if known_total else "proportional_to_storyboard_estimates"

        timeline_scene_duration = sum(scene_durations) + gaps_duration
        delta = abs(timeline_scene_duration - audio_duration_sec)
        if delta > 0.15:
            raise MediaRenderError(
                f"Per-scene narration durations plus silence gaps differ from the measured master audio by {delta:.3f}s.",
                stage="timeline",
            )
        return list(zip(ordered, scene_durations)), method, delta

    def _verify_output(
        self,
        output_path: Path,
        width: int,
        height: int,
        fps: int,
        audio_duration_sec: float,
    ) -> Dict[str, Any]:
        metadata = self._probe_file(output_path, "rendered MP4")
        format_data = metadata.get("format") or {}
        format_names = str(format_data.get("format_name", "")).lower().split(",")
        streams = metadata.get("streams") or []
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        if not any("mp4" in name or "mov" in name for name in format_names):
            raise MediaRenderError(f"FFprobe did not identify a valid MP4 container: {format_names}.", stage="verification")
        if not video_stream or not audio_stream:
            raise MediaRenderError("Rendered MP4 is missing its required video or audio stream.", stage="verification")
        if video_stream.get("codec_name") != "h264" or audio_stream.get("codec_name") != "aac":
            raise MediaRenderError(
                f"Rendered codecs are {video_stream.get('codec_name')}/{audio_stream.get('codec_name')}; expected h264/aac.",
                stage="verification",
            )
        actual_width = int(video_stream.get("width") or 0)
        actual_height = int(video_stream.get("height") or 0)
        if (actual_width, actual_height) != (width, height):
            raise MediaRenderError(
                f"Rendered dimensions are {actual_width}x{actual_height}; expected {width}x{height}.",
                stage="verification",
            )
        video_duration = self._stream_duration(video_stream, format_data)
        audio_duration = self._stream_duration(audio_stream, format_data)
        if video_duration <= 0 or audio_duration <= 0:
            raise MediaRenderError("FFprobe reported a zero or missing audio/video duration.", stage="verification")
        duration_delta = abs(video_duration - audio_duration)
        if duration_delta > 0.25 or abs(audio_duration - audio_duration_sec) > 0.25:
            raise MediaRenderError(
                f"Rendered stream duration mismatch: video={video_duration:.3f}s, audio={audio_duration:.3f}s, "
                f"master_audio={audio_duration_sec:.3f}s (delta={duration_delta:.3f}s).",
                stage="verification",
            )
        actual_fps = self._parse_frame_rate(video_stream.get("avg_frame_rate"))
        if actual_fps is not None and abs(actual_fps - fps) > 0.1:
            raise MediaRenderError(f"Rendered frame rate is {actual_fps:.3f}; expected {fps}.", stage="verification")
        return {
            "video_codec": video_stream["codec_name"],
            "audio_codec": audio_stream["codec_name"],
            "width": actual_width,
            "height": actual_height,
            "fps": round(actual_fps or float(fps), 3),
            "video_duration_sec": round(video_duration, 3),
            "audio_duration_sec": round(audio_duration, 3),
            "duration_sync_delta": round(duration_delta, 3),
            "container_format": format_data.get("format_name"),
        }

    def assemble_media(
        self,
        script_id: str,
        package_id: str,
        scenes: List[SceneMediaInput],
        master_audio_path: str,
        total_duration_sec: float,
        config: MediaRenderConfigRequest,
        subtitle_path: Optional[str] = None,
        audio_is_mock: bool = False,
        subtitle_timing_method: Optional[str] = None,
        silence_gap_sec: float = 0.2,
    ) -> MediaRenderOutput:
        """Compose scene assets in order and fail closed unless FFprobe validates the MP4."""
        if not self.has_ffmpeg():
            raise MediaRenderError("FFmpeg is not installed or available on PATH; video rendering cannot run.")
        if not self.has_ffprobe():
            raise MediaRenderError("FFprobe is not installed or available on PATH; production output cannot be verified.", stage="verification")
        if not scenes:
            raise AssetUnavailableError("No storyboard scenes were supplied for rendering.")
        try:
            norm_res = config.get_normalized_resolution()
        except ValueError as exc:
            raise MediaRenderError(str(exc), stage="configuration") from exc
        width, height = (1080, 1920) if norm_res == "1080x1920" else (1920, 1080)

        audio_asset = self._resolve_asset(master_audio_path, "Master narration audio")
        audio_metadata = self._probe_file(audio_asset, "master narration audio")
        audio_stream = next(
            (stream for stream in (audio_metadata.get("streams") or []) if stream.get("codec_type") == "audio"),
            None,
        )
        if not audio_stream:
            raise MediaRenderError("Master narration file has no decodable audio stream.", stage="voice")
        audio_duration_sec = self._stream_duration(audio_stream, audio_metadata.get("format") or {})
        if audio_duration_sec <= 0:
            raise MediaRenderError("Master narration audio has no measurable duration.", stage="voice")

        subtitle_asset: Optional[Path] = None
        if config.burn_subtitles:
            subtitle_asset = self._resolve_asset(subtitle_path, "Required subtitle file")
            if subtitle_asset.suffix.lower() not in {".srt", ".vtt"}:
                raise MediaRenderError("Burn-in captions must be an SRT or VTT file.", stage="subtitles")
            if subtitle_asset.stat().st_size == 0:
                raise MediaRenderError("Required subtitle file is empty.", stage="subtitles")

        safe_script_id = re.sub(r"[^a-zA-Z0-9_-]", "_", script_id)[:40] or "script"
        safe_package_id = re.sub(r"[^a-zA-Z0-9_-]", "_", package_id)[:40] or "package"
        out_path = self.output_dir / f"video_{safe_script_id[:8]}_{safe_package_id[:8]}.mp4"
        timeline_path = self.output_dir / f"timeline_{safe_package_id[:8]}.json"
        timeline_path.parent.mkdir(parents=True, exist_ok=True)
        # A failed retry must not leave an older video looking current.
        out_path.unlink(missing_ok=True)
        timeline_path.unlink(missing_ok=True)

        ordered_scenes = sorted(scenes, key=lambda scene: scene.scene_order)
        timeline_seconds, timing_method, scene_timing_delta = self._scene_durations(
            ordered_scenes,
            audio_duration_sec,
            silence_gap_sec,
        )
        audio_peak = LocalAudioSynthesizer.get_audio_peak_db(str(audio_asset))
        if audio_peak <= -55.0:
            raise MediaRenderError(f"Master narration is silent or too quiet (peak {audio_peak:.1f} dBFS).", stage="voice")

        subtitles_burned = False
        mock_visuals = any(scene.visual_is_mock for scene in ordered_scenes)
        with tempfile.TemporaryDirectory(prefix="studio-render-", dir=str(self.output_dir)) as temp_name:
            temp_dir = Path(temp_name)
            scene_sources = self._resolve_scene_sources(ordered_scenes, temp_dir)
            if config.burn_subtitles and subtitle_asset is None:
                raise MediaRenderError("Captions are required for this render but no valid subtitle file was supplied.", stage="subtitles")
            staged_subtitle: Optional[Path] = None
            if subtitle_asset:
                if config.burn_subtitles:
                    staged_subtitle = temp_dir / "captions.ass"
                    self._write_ass_subtitles(subtitle_asset, staged_subtitle, width, height)
                else:
                    staged_subtitle = temp_dir / f"captions{subtitle_asset.suffix.lower()}"
                    shutil.copyfile(subtitle_asset, staged_subtitle)

            filter_parts: List[str] = []
            video_labels: List[str] = []
            command: List[str] = [self.ffmpeg_path, "-hide_banner", "-loglevel", "error", "-y"]
            segment_durations: List[float] = []
            for index, (scene, source, source_type) in enumerate(scene_sources):
                duration = timeline_seconds[index][1]
                segment_duration = duration + (silence_gap_sec if index < len(scene_sources) - 1 else 0.0)
                segment_durations.append(segment_duration)
                if source_type == "image":
                    command.extend(["-loop", "1", "-framerate", str(config.fps), "-t", f"{segment_duration:.6f}", "-i", str(source)])
                else:
                    command.extend(["-stream_loop", "-1", "-i", str(source)])
                label = f"scene{index}"
                video_labels.append(f"[{label}]")
                filter_parts.append(
                    f"[{index}:v:0]trim=duration={segment_duration:.6f},setpts=PTS-STARTPTS,"
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={config.fps},format=yuv420p[{label}]"
                )

            audio_input_index = len(scene_sources)
            command.extend(["-i", str(audio_asset)])
            filter_parts.append("".join(video_labels) + f"concat=n={len(video_labels)}:v=1:a=0[vconcat]")
            video_map = "[vconcat]"
            if config.burn_subtitles and staged_subtitle:
                escaped_subtitle = self._escape_path_for_ffmpeg(staged_subtitle)
                filter_parts.append(f"[vconcat]subtitles=filename='{escaped_subtitle}'[vout]")
                video_map = "[vout]"
                subtitles_burned = True

            command.extend([
                "-filter_complex", ";".join(filter_parts),
                "-map", video_map,
                "-map", f"{audio_input_index}:a:0",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(config.fps),
                "-preset", config.preset,
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-t", f"{audio_duration_sec:.6f}",
                "-movflags", "+faststart",
                str(out_path),
            ])
            try:
                proc = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                out_path.unlink(missing_ok=True)
                stage = "subtitles" if config.burn_subtitles else "render"
                raise MediaRenderError(f"FFmpeg render process failed: {exc}", stage=stage) from exc
            if proc.returncode != 0:
                out_path.unlink(missing_ok=True)
                detail = (proc.stderr or proc.stdout or "FFmpeg returned a non-zero exit code.").strip()[-self.MAX_PROBE_DIAGNOSTIC_CHARS :]
                if config.burn_subtitles:
                    raise MediaRenderError(
                        f"FFmpeg could not render the required burned captions; no caption-free retry was made. {detail}",
                        stage="subtitles",
                    )
                raise MediaRenderError(f"FFmpeg video composition failed: {detail}", stage="render")

            if not out_path.is_file() or out_path.stat().st_size < 1024:
                out_path.unlink(missing_ok=True)
                raise MediaRenderError("FFmpeg did not produce a complete MP4 file.", stage="render")
            try:
                verified = self._verify_output(out_path, width, height, config.fps, audio_duration_sec)
            except MediaPipelineError:
                out_path.unlink(missing_ok=True)
                raise

            timeline = {
                "script_id": script_id,
                "package_id": package_id,
                "resolution": f"{width}x{height}",
                "fps": config.fps,
                "measured_audio_duration_sec": audio_duration_sec,
                "reported_duration_estimate_sec": total_duration_sec,
                "burn_subtitles": config.burn_subtitles,
                "subtitle_path": str(subtitle_asset) if subtitle_asset else None,
                "subtitle_timing_method": subtitle_timing_method or "not_applicable",
                "scenes": [
                    {
                        "scene_id": scene.id,
                        "scene_order": scene.scene_order,
                        "visual_type": scene.visual_type,
                        "visual_source": scene.visual_source,
                        "actual_audio_duration_sec": scene.actual_audio_duration_sec,
                        "timing_estimate": scene.timing_estimate,
                        "render_duration_sec": round(segment_durations[index], 3),
                        "visual_is_mock": scene.visual_is_mock,
                    }
                    for index, (scene, _, _) in enumerate(scene_sources)
                ],
            }
            try:
                with timeline_path.open("w", encoding="utf-8") as timeline_file:
                    json.dump(timeline, timeline_file, indent=2)
            except OSError as exc:
                out_path.unlink(missing_ok=True)
                timeline_path.unlink(missing_ok=True)
                raise MediaRenderError(f"Could not persist the verified render timeline: {exc}", stage="timeline") from exc

        issues: List[str] = []
        if audio_is_mock:
            issues.append("Mock harmonic audio was used; this output is not production narration.")
        if mock_visuals:
            issues.append("One or more scene assets are labeled mock; this output is not production-eligible.")
        if config.burn_subtitles and not subtitles_burned:
            issues.append("Required captions were not burned into the video.")
        timing_limitation = (
            "Scene durations use measured narration tracks; word-level caption timings remain proportional estimates."
            if timing_method == "measured_per_scene_audio"
            else "Some scene durations use proportional storyboard estimates because measured narration timing was unavailable."
        )
        production_eligible = not issues and subtitles_burned == config.burn_subtitles
        quality_report: Dict[str, Any] = {
            "ffmpeg_available": self.has_ffmpeg(),
            "ffmpeg_version": self.get_ffmpeg_version(),
            "ffprobe_available": self.has_ffprobe(),
            "ffprobe_version": self.get_ffprobe_version(),
            "ffprobe_verified": True,
            "video_codec": verified["video_codec"],
            "audio_codec": verified["audio_codec"],
            "width": verified["width"],
            "height": verified["height"],
            "resolution": f"{verified['width']}x{verified['height']}",
            "fps": verified["fps"],
            "video_duration_sec": verified["video_duration_sec"],
            "audio_duration_sec": verified["audio_duration_sec"],
            "measured_master_audio_duration_sec": round(audio_duration_sec, 3),
            "reported_duration_estimate_sec": total_duration_sec,
            "duration_sync_delta": verified["duration_sync_delta"],
            "scene_timing_method": timing_method,
            "scene_timing_delta": round(scene_timing_delta, 3),
            "subtitle_timing_method": subtitle_timing_method or "not_applicable",
            "timing_limitation": timing_limitation,
            "audio_peak_db": audio_peak,
            "has_audio": True,
            "has_video": True,
            "subtitles_requested": config.burn_subtitles,
            "subtitles_burned": subtitles_burned,
            "subtitle_path": str(subtitle_asset) if subtitles_burned and subtitle_asset else None,
            "mock_audio": audio_is_mock,
            "mock_visual_assets": mock_visuals,
            "production_eligible": production_eligible,
            "preset": config.preset,
            "passed": production_eligible and verified["duration_sync_delta"] <= 0.25,
            "issues": issues,
        }

        return MediaRenderOutput(
            package_id=package_id,
            script_id=script_id,
            video_path=str(out_path).replace("\\", "/"),
            duration_sec=verified["video_duration_sec"],
            file_size_bytes=out_path.stat().st_size,
            resolution=f"{width}x{height}",
            fps=config.fps,
            status="READY" if quality_report["passed"] else "MOCK",
            quality_report=quality_report,
            timeline_path=str(timeline_path).replace("\\", "/"),
        )
