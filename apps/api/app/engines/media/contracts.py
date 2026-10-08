from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SceneMediaInput(BaseModel):
    id: str
    scene_order: int
    narration: str
    timing_estimate: float
    visual_type: str = "real_screen_recording"
    visual_source: Optional[str] = None
    on_screen_text: Optional[str] = None


class VoiceConfigRequest(BaseModel):
    voice_id: str = "en-US-Studio-Standard"
    speed: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float = Field(0.0, ge=-10.0, le=10.0)
    sample_rate: int = 44100
    mock_mode: Optional[bool] = None  # None = inherit settings.TTS_MOCK_MODE


class SubtitleConfigRequest(BaseModel):
    format: str = "srt"  # "srt" or "vtt"
    max_words_per_line: int = Field(4, ge=1, le=15)
    highlight_color: str = "#F59E0B"
    font_size: int = 42
    silence_gap_sec: float = Field(0.2, ge=0.0, le=2.0)


class MediaRenderConfigRequest(BaseModel):
    resolution: str = "1080x1920"
    fps: int = Field(30, ge=15, le=60)
    burn_subtitles: bool = False
    preset: str = "fast"

    def get_normalized_resolution(self) -> str:
        """Normalizes aspect ratio aliases to standard WxH strings."""
        res_str = self.resolution.strip().lower()
        if res_str in ("horizontal_16_9", "16:9", "1920x1080", "landscape"):
            return "1920x1080"
        return "1080x1920"


class VoiceTrackOutput(BaseModel):
    scene_id: str
    audio_path: str
    duration_sec: float
    word_count: int
    waveform_peaks: List[float] = Field(default_factory=list)


class VoiceSynthesisOutput(BaseModel):
    package_id: str
    script_id: str
    tracks: List[VoiceTrackOutput]
    master_audio_path: str
    total_duration_sec: float


class SubtitleCueOutput(BaseModel):
    index: int
    start_sec: float
    end_sec: float
    start_timestamp: str
    end_timestamp: str
    text: str
    scene_id: Optional[str] = None
    cps: float = 0.0
    wpm: float = 0.0


class SubtitleGenerationOutput(BaseModel):
    subtitle_path: str
    content_text: str
    cue_count: int
    format: str
    cues: List[SubtitleCueOutput]
    avg_cps: float = 0.0
    max_cps: float = 0.0
    pacing_status: str = "OPTIMAL"


class MediaRenderOutput(BaseModel):
    package_id: str
    script_id: str
    video_path: str
    duration_sec: float
    file_size_bytes: int
    resolution: str
    fps: int
    status: str
    quality_report: Dict[str, Any]
