"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  FileText,
  Film,
  FolderArchive,
  Headphones,
  Layers,
  Mic,
  Monitor,
  Music,
  Play,
  RefreshCw,
  Sliders,
  Smartphone,
  Sparkles,
  Subtitles,
  Volume2,
} from "lucide-react";
import {
  MediaPackage,
  PublishableItemSummary,
  SceneVoiceTrack,
  ScriptDraft,
  SubtitleCue,
  SubtitleGenerationOutput,
  VoiceProfile,
  VoiceCatalog,
  generateScriptSubtitles,
  enqueueMediaJob,
  getMediaPackageByScript,
  getScriptByItem,
  getVoiceProfiles,
  listPublishableItems,
  waitForStudioJob,
} from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

export default function MediaStudioPage() {
  const { t } = useLanguage();

  // State: Script / Publishable Items
  const [items, setItems] = useState<PublishableItemSummary[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<string>("");
  const [activeScript, setActiveScript] = useState<ScriptDraft | null>(null);
  const [loadingScript, setLoadingScript] = useState(false);

  // State: Voice Profiles & Synthesis
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [voiceCatalog, setVoiceCatalog] = useState<VoiceCatalog | null>(null);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>("");
  const [speechSpeed, setSpeechSpeed] = useState<number>(1.0);
  const [synthesizing, setSynthesizing] = useState(false);

  // State: Subtitles
  const [subtitleFormat, setSubtitleFormat] = useState<"srt" | "vtt">("srt");
  const [maxWordsPerCue, setMaxWordsPerCue] = useState<number>(4);
  const [generatingSubtitles, setGeneratingSubtitles] = useState(false);
  const [subtitlesOutput, setSubtitlesOutput] = useState<SubtitleGenerationOutput | null>(null);
  const [copiedSubtitle, setCopiedSubtitle] = useState(false);

  // State: Rendering
  const [renderResolution, setRenderResolution] = useState<"vertical_9_16" | "horizontal_16_9">("vertical_9_16");
  const [burnSubtitles, setBurnSubtitles] = useState<boolean>(true);
  const [rendering, setRendering] = useState(false);
  const [renderedVideoPath, setRenderedVideoPath] = useState<string | null>(null);
  const [qualityReport, setQualityReport] = useState<Record<string, any> | null>(null);

  // State: Active Media Package
  const [mediaPackage, setMediaPackage] = useState<MediaPackage | null>(null);
  const [activeAudioPlaying, setActiveAudioPlaying] = useState<string | null>(null);

  // Load items and voice profiles on mount
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [itemList, voiceCatalogResult] = await Promise.all([
        listPublishableItems(),
        getVoiceProfiles(),
      ]);
      setItems(itemList);
      setVoiceCatalog(voiceCatalogResult);
      setVoices(voiceCatalogResult.voices);
      if (itemList.length > 0 && !selectedItemId) {
        setSelectedItemId(itemList[0].id);
      }
      setSelectedVoiceId(
        voiceCatalogResult.default_voice_id || voiceCatalogResult.voices[0]?.id || ""
      );
    } catch (e) {
      console.error("Failed to load initial media studio data:", e);
    }
  };

  // When item selected, load its script and media package
  useEffect(() => {
    if (selectedItemId) {
      loadScriptAndMediaPackage(selectedItemId);
    }
  }, [selectedItemId]);

  const loadScriptAndMediaPackage = async (itemId: string) => {
    try {
      setLoadingScript(true);
      const script = await getScriptByItem(itemId);
      setActiveScript(script);

      if (script) {
        const pkg = await getMediaPackageByScript(script.id);
        setMediaPackage(pkg);
        setRenderedVideoPath(pkg?.video_path || null);
        setQualityReport(pkg?.quality_checks || null);
        setSubtitlesOutput(null);
        if (pkg?.resolution) {
          setRenderResolution(pkg.resolution as any);
        }
      } else {
        setMediaPackage(null);
        setRenderedVideoPath(null);
        setQualityReport(null);
        setSubtitlesOutput(null);
      }
    } catch (e) {
      console.error("Failed to load script or media package:", e);
      setMediaPackage(null);
      setRenderedVideoPath(null);
      setQualityReport(null);
    } finally {
      setLoadingScript(false);
    }
  };

  // Synthesize voice tracks
  const handleSynthesizeVoice = async () => {
    if (!activeScript) return;
    try {
      setSynthesizing(true);
      setMediaPackage((current) => current ? { ...current, status: "SYNTHESIZING" } : current);
      const job = await enqueueMediaJob(activeScript.id, {
        action: "synthesize",
        voice_config: {
          voice_id: selectedVoiceId,
          speed: speechSpeed,
          mock_mode: false,
        },
      });
      const completedJob = await waitForStudioJob(job.id);
      const updated = await getMediaPackageByScript(activeScript.id);
      setMediaPackage(updated);
      if (completedJob.status !== "completed") {
        throw new Error(completedJob.error || "Local media worker failed to synthesize narration.");
      }
    } catch (e: any) {
      alert("Voice synthesis failed: " + (e.message || e));
    } finally {
      setSynthesizing(false);
    }
  };

  // Generate synchronized subtitles
  const handleGenerateSubtitles = async () => {
    if (!activeScript) return;
    try {
      setGeneratingSubtitles(true);
      const res = await generateScriptSubtitles(activeScript.id, {
        format: subtitleFormat,
        max_words_per_line: maxWordsPerCue,
      });
      setSubtitlesOutput(res);
      // Refresh package
      const updated = await getMediaPackageByScript(activeScript.id);
      setMediaPackage(updated);
    } catch (e: any) {
      alert("Subtitle generation failed: " + (e.message || e));
    } finally {
      setGeneratingSubtitles(false);
    }
  };

  // Copy subtitle text
  const handleCopySubtitles = () => {
    if (!subtitlesOutput?.content_text) return;
    navigator.clipboard.writeText(subtitlesOutput.content_text);
    setCopiedSubtitle(true);
    setTimeout(() => setCopiedSubtitle(false), 2000);
  };

  // Render video composition
  const handleRenderMedia = async () => {
    if (!activeScript) return;
    try {
      setRendering(true);
      setMediaPackage((current) => current ? { ...current, status: "RENDERING" } : current);
      const job = await enqueueMediaJob(activeScript.id, {
        action: "render",
        voice_config: {
          voice_id: selectedVoiceId,
          speed: speechSpeed,
          mock_mode: false,
        },
        subtitle_config: {
          format: subtitleFormat,
          max_words_per_line: maxWordsPerCue,
        },
        render_config: {
          resolution: renderResolution,
          fps: 30,
          burn_subtitles: burnSubtitles,
        },
      });
      const completedJob = await waitForStudioJob(job.id);
      const updated = await getMediaPackageByScript(activeScript.id);
      setMediaPackage(updated);
      setRenderedVideoPath(updated?.video_path || null);
      setQualityReport(updated?.quality_checks || null);
      if (completedJob.status !== "completed" || updated?.status !== "READY") {
        const issues = updated?.quality_checks?.issues?.join("; ");
        throw new Error(completedJob.error || issues || "Media output did not pass production verification.");
      }
      setRenderedVideoPath(updated.video_path || null);
      setQualityReport(updated.quality_checks || null);
    } catch (e: any) {
      alert("Media render failed: " + (e.message || e));
    } finally {
      setRendering(false);
    }
  };

  // Status Badge Helper
  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case "ready":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {t("mediaStudioPage.statusReady", "Ready")}
          </span>
        );
      case "synthesized":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-300 border border-sky-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Narration ready
          </span>
        );
      case "mock":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-orange-500/10 text-orange-300 border border-orange-500/20">
            <AlertCircle className="w-3.5 h-3.5" />
            Mock output · not production-ready
          </span>
        );
      case "synthesizing":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            {t("mediaStudioPage.statusSynthesizing", "Synthesizing...")}
          </span>
        );
      case "rendering":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            {t("mediaStudioPage.statusRendering", "Rendering...")}
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3.5 h-3.5" />
            {t("mediaStudioPage.statusFailed", "Failed")}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {t("mediaStudioPage.statusDraft", "Draft")}
          </span>
        );
    }
  };

  const isMockOutput = mediaPackage?.status === "MOCK";
  const videoAspectClass = renderResolution === "vertical_9_16"
    ? "max-w-[280px] aspect-[9/16]"
    : "max-w-[560px] aspect-video";

  return (
    <div className="space-y-8 pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <Headphones className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                {t("mediaStudioPage.title", "Voice, Subtitle & Media Studio")}
                <span className="text-xs font-medium px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Phase 16
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                {t("mediaStudioPage.subtitle", "Installed offline system voices, measured scene timing, and local FFmpeg composition")}
              </p>
            </div>
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-3">
          {mediaPackage && getStatusBadge(mediaPackage.status)}
          <button
            onClick={() => selectedItemId && loadScriptAndMediaPackage(selectedItemId)}
            className="p-2 text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition-colors"
            title={t("common.refresh", "Refresh")}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Script Selector Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm backdrop-blur-sm">
        <div className="flex-1 max-w-xl">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            {t("mediaStudioPage.scriptSelector", "Select Script")}
          </label>
          <select
            value={selectedItemId}
            onChange={(e) => setSelectedItemId(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
          >
            <option value="" disabled>
              {t("mediaStudioPage.selectScriptPlaceholder", "-- Choose a script for media production --")}
            </option>
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.working_title || item.family_title || "Untitled"} ({item.platform_target || item.format || "Script"})
              </option>
            ))}
          </select>
        </div>

        {activeScript && (
          <div className="flex items-center gap-6 text-sm text-slate-400 bg-slate-950/60 px-4 py-3 rounded-lg border border-slate-800/80">
            <div>
              <span className="text-xs text-slate-500 block">Version</span>
              <span className="font-semibold text-slate-200">v{activeScript.version}</span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-xs text-slate-500 block">Approval Gate</span>
              <span className={`font-semibold ${activeScript.is_approved ? "text-emerald-400" : "text-amber-400"}`}>
                {activeScript.is_approved ? "Approved" : "Draft"}
              </span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-xs text-slate-500 block">Estimated Duration</span>
              <span className="font-semibold text-slate-200">
                {activeScript.target_duration_sec ? `${activeScript.target_duration_sec}s` : "30s"}
              </span>
            </div>
          </div>
        )}
      </div>

      {!activeScript && !loadingScript && (
        <div className="p-12 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30">
          <FolderArchive className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">
            {t("mediaStudioPage.noScriptSelected", "No script selected.")}
          </h3>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            Please choose an approved script from the dropdown above to synthesize voice tracks, build sub-second captions, and assemble videos.
          </p>
        </div>
      )}

      {activeScript && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* ========================================================================= */}
          {/* MODULE A: VOICE SYNTHESIZER */}
          {/* ========================================================================= */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm p-6 flex flex-col justify-between shadow-sm">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    <Mic className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">
                      {t("mediaStudioPage.voiceSection.title", "Voice Synthesis")}
                    </h2>
                    <p className="text-xs text-slate-400">
                      {t("mediaStudioPage.voiceSection.desc", "Actual Windows SAPI5 voices installed on this computer")}
                    </p>
                  </div>
                </div>
              </div>

              {/* Voice profile picker */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">
                  {t("mediaStudioPage.voiceSection.selectVoice", "Voice Profile")}
                </label>
                {!voiceCatalog?.available && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                    {voiceCatalog?.message || "No supported offline system voices are available on this computer."}
                    {voiceCatalog?.unavailable_languages?.length ? (
                      <div className="mt-1 text-amber-300/80">
                        Unavailable languages: {voiceCatalog.unavailable_languages.join(", ")}
                      </div>
                    ) : null}
                  </div>
                )}
                <div className="grid grid-cols-1 gap-2">
                  {voices.map((v) => (
                    <button
                      key={v.id}
                      onClick={() => setSelectedVoiceId(v.id)}
                      className={`flex items-center justify-between p-3 rounded-lg border text-left text-xs transition-all ${
                        selectedVoiceId === v.id
                          ? "border-indigo-500 bg-indigo-600/10 text-white font-medium"
                          : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <div>
                        <div className="font-semibold text-slate-200">{v.name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {v.gender} • {v.locale}
                        </div>
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        Installed
                      </span>
                    </button>
                  ))}
                </div>
                {!!voiceCatalog?.available && !!voiceCatalog.unavailable_languages.length && (
                  <p className="text-[11px] text-amber-300/80">
                    Unavailable languages: {voiceCatalog.unavailable_languages.join(", ")}
                  </p>
                )}
              </div>

              {/* Speech speed slider */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">
                    {t("mediaStudioPage.voiceSection.speed", "Speech Speed")}
                  </span>
                  <span className="font-mono text-indigo-400 font-semibold">{speechSpeed.toFixed(2)}x</span>
                </div>
                <input
                  type="range"
                  min="0.80"
                  max="1.30"
                  step="0.05"
                  value={speechSpeed}
                  onChange={(e) => setSpeechSpeed(parseFloat(e.target.value))}
                  className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>0.80x (Calm)</span>
                  <span>1.0x (Natural)</span>
                  <span>1.30x (Dynamic)</span>
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={handleSynthesizeVoice}
                disabled={synthesizing || !voiceCatalog?.available || !selectedVoiceId}
                className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-50 transition-all"
              >
                {synthesizing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    {t("mediaStudioPage.voiceSection.synthesizing", "Synthesizing Voice...")}
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    {t("mediaStudioPage.voiceSection.synthesizeBtn", "Synthesize Voice Tracks")}
                  </>
                )}
              </button>

              {/* Waveform & Tracks List */}
              {mediaPackage && mediaPackage.voice_tracks && mediaPackage.voice_tracks.length > 0 && (
                <div className="space-y-3 pt-3 border-t border-slate-800/80">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300">
                      {t("mediaStudioPage.voiceSection.sceneTracks", "Scene Voice Tracks")} ({mediaPackage.voice_tracks.length})
                    </span>
                    <span className="font-mono text-slate-400">
                      {mediaPackage.total_duration_sec.toFixed(1)}s total
                    </span>
                  </div>

                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {mediaPackage.voice_tracks.map((track, idx) => (
                      <div
                        key={track.id || idx}
                        className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex flex-col gap-2"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-indigo-300">
                            Scene {idx + 1}
                          </span>
                          <span className="text-[11px] font-mono text-slate-400">
                            {track.duration_sec.toFixed(1)}s • {track.word_count} {t("mediaStudioPage.voiceSection.words", "words")}
                          </span>
                        </div>

                        {/* Interactive Waveform Visualizer */}
                        <div className="h-8 flex items-end gap-[2px] bg-slate-900/80 p-1 rounded border border-slate-800/50">
                          {(track.waveform_peaks || []).slice(0, 32).map((peak, pidx) => {
                            const barHeight = Math.max(12, Math.round(peak * 100));
                            return (
                              <div
                                key={pidx}
                                style={{ height: `${barHeight}%` }}
                                className="flex-1 bg-gradient-to-t from-indigo-600 to-indigo-400 rounded-t-sm opacity-80 hover:opacity-100 transition-opacity"
                                title={`Peak ${pidx + 1}: ${peak.toFixed(2)}`}
                              />
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* MODULE B: SUBTITLE & CAPTION SYNCHRONIZER */}
          {/* ========================================================================= */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm p-6 flex flex-col justify-between shadow-sm">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <Subtitles className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">
                      {t("mediaStudioPage.subtitleSection.title", "Subtitle Synchronization")}
                    </h2>
                    <p className="text-xs text-slate-400">
                      {t("mediaStudioPage.subtitleSection.desc", "Word-cadence timing calculations and sub-second cues")}
                    </p>
                  </div>
                </div>
              </div>

              {/* Subtitle Format Selector */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">
                  {t("mediaStudioPage.subtitleSection.format", "Caption Format")}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setSubtitleFormat("srt")}
                    className={`py-2 px-3 rounded-lg border text-xs font-medium transition-all ${
                      subtitleFormat === "srt"
                        ? "border-amber-500 bg-amber-500/10 text-amber-300"
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    SubRip (.SRT)
                  </button>
                  <button
                    onClick={() => setSubtitleFormat("vtt")}
                    className={`py-2 px-3 rounded-lg border text-xs font-medium transition-all ${
                      subtitleFormat === "vtt"
                        ? "border-amber-500 bg-amber-500/10 text-amber-300"
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    WebVTT (.VTT)
                  </button>
                </div>
              </div>

              {/* Word Chunks Density */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Words Per Cue</span>
                  <span className="font-mono text-amber-400 font-semibold">{maxWordsPerCue} words</span>
                </div>
                <input
                  type="range"
                  min="2"
                  max="8"
                  step="1"
                  value={maxWordsPerCue}
                  onChange={(e) => setMaxWordsPerCue(parseInt(e.target.value))}
                  className="w-full accent-amber-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>2 (High Pacing)</span>
                  <span>4 (Shorts / Reels)</span>
                  <span>8 (Desktop)</span>
                </div>
              </div>

              {/* Generate Subtitles Button */}
              <button
                onClick={handleGenerateSubtitles}
                disabled={generatingSubtitles}
                className="w-full py-2.5 px-4 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-md shadow-amber-600/20 disabled:opacity-50 transition-all"
              >
                {generatingSubtitles ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    {t("mediaStudioPage.subtitleSection.generating", "Generating Subtitles...")}
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4" />
                    {t("mediaStudioPage.subtitleSection.generateBtn", "Generate Subtitles")}
                  </>
                )}
              </button>

              {/* Cues List & Actions */}
              {subtitlesOutput && subtitlesOutput.cues && (
                <div className="space-y-3 pt-3 border-t border-slate-800/80">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300">
                      {t("mediaStudioPage.subtitleSection.cueCount", "Total Cues")}: {subtitlesOutput.cue_count}
                    </span>
                    <button
                      onClick={handleCopySubtitles}
                      className="inline-flex items-center gap-1 text-[11px] text-amber-400 hover:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 px-2 py-1 rounded transition-colors"
                    >
                      {copiedSubtitle ? <CheckCircle2 className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                      {copiedSubtitle ? t("common.copied", "Copied!") : t("mediaStudioPage.subtitleSection.copySrt", "Copy")}
                    </button>
                  </div>

                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {subtitlesOutput.cues.map((cue, cidx) => (
                      <div
                        key={cidx}
                        className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-[11px] font-mono text-amber-400/90">
                          <span>#{cue.index}</span>
                          <span>
                            {cue.start_timestamp.slice(0, 8)} ➔ {cue.end_timestamp.slice(0, 8)}
                          </span>
                        </div>
                        <p className="text-slate-200 font-medium leading-relaxed">
                          &ldquo;{cue.text}&rdquo;
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ========================================================================= */}
          {/* MODULE C: VIDEO ASSEMBLY & FFmpeg RENDER */}
          {/* ========================================================================= */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm p-6 flex flex-col justify-between shadow-sm">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <Film className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">
                      {t("mediaStudioPage.renderSection.title", "Video Assembly & Render")}
                    </h2>
                    <p className="text-xs text-slate-400">
                      {t("mediaStudioPage.renderSection.desc", "Local FFmpeg 9:16 Shorts or 16:9 Landscape Composition")}
                    </p>
                  </div>
                </div>
              </div>

              {/* Resolution preset */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">
                  {t("mediaStudioPage.renderSection.preset", "Video Aspect Ratio")}
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setRenderResolution("vertical_9_16")}
                    className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs font-medium transition-all ${
                      renderResolution === "vertical_9_16"
                        ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <Smartphone className="w-4 h-4 shrink-0 text-emerald-400" />
                    <div className="text-left">
                      <div className="font-semibold text-white">9:16 Shorts</div>
                      <div className="text-[10px] text-slate-500">1080x1920</div>
                    </div>
                  </button>

                  <button
                    onClick={() => setRenderResolution("horizontal_16_9")}
                    className={`flex items-center gap-2 p-2.5 rounded-lg border text-xs font-medium transition-all ${
                      renderResolution === "horizontal_16_9"
                        ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <Monitor className="w-4 h-4 shrink-0 text-emerald-400" />
                    <div className="text-left">
                      <div className="font-semibold text-white">16:9 Desktop</div>
                      <div className="text-[10px] text-slate-500">1920x1080</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Subtitle burn-in checkbox */}
              <label className="flex items-center gap-3 p-3 rounded-lg bg-slate-950/40 border border-slate-800 text-xs text-slate-300 cursor-pointer hover:border-slate-700 transition-colors">
                <input
                  type="checkbox"
                  checked={burnSubtitles}
                  onChange={(e) => setBurnSubtitles(e.target.checked)}
                  className="rounded border-slate-700 text-emerald-600 focus:ring-emerald-500 w-4 h-4 bg-slate-900"
                />
                <div className="flex-1">
                  <div className="font-medium text-white">
                    {t("mediaStudioPage.renderSection.burnSubtitles", "Burn Subtitles into Video")}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Embeds synchronized caption cues directly onto the render frames.
                  </div>
                </div>
              </label>

              {/* Render Button */}
              <button
                onClick={handleRenderMedia}
                disabled={rendering || (!mediaPackage?.audio_path && (!voiceCatalog?.available || !selectedVoiceId))}
                className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-md shadow-emerald-600/20 disabled:opacity-50 transition-all"
              >
                {rendering ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    {t("mediaStudioPage.renderSection.rendering", "Rendering with FFmpeg...")}
                  </>
                ) : (
                  <>
                    <Film className="w-4 h-4" />
                    {t("mediaStudioPage.renderSection.renderBtn", "Render Video Composition")}
                  </>
                )}
              </button>

              {/* Rendered Video Card & Quality Report */}
              {renderedVideoPath && (
                <div className="space-y-4 pt-4 border-t border-slate-800/80">
                  <div className={`p-4 rounded-xl text-xs space-y-4 ${isMockOutput ? "bg-orange-950/20 border border-orange-500/30" : "bg-emerald-950/20 border border-emerald-500/30"}`}>
                    <div className="flex items-center justify-between">
                      <span className={`font-semibold flex items-center gap-1.5 text-sm ${isMockOutput ? "text-orange-300" : "text-emerald-400"}`}>
                        {isMockOutput ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                        {isMockOutput ? "Mock preview · not production-ready" : "Verified production video"}
                      </span>
                      <span className={`text-[10px] uppercase font-mono px-2.5 py-1 rounded-full font-bold ${isMockOutput ? "bg-orange-500/20 text-orange-300 border border-orange-500/30" : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"}`}>
                        {mediaPackage?.resolution || (renderResolution === "vertical_9_16" ? "1080x1920" : "1920x1080")}
                      </span>
                    </div>

                    {/* Inline Video Player */}
                    <div className={`relative mx-auto ${videoAspectClass} rounded-2xl overflow-hidden border-2 ${isMockOutput ? "border-orange-500/40" : "border-emerald-500/40"} shadow-2xl bg-black`}>
                      <video
                        src={`http://localhost:8400/assets/video/${renderedVideoPath.split(/[/\\]/).pop()}`}
                        controls
                        playsInline
                        className="w-full h-full object-contain"
                      />
                    </div>

                    <div className="flex items-center justify-between gap-2 pt-2">
                      <div className="font-mono text-[11px] text-slate-400 truncate bg-slate-950/80 p-2 rounded-lg border border-slate-800/80 flex-1">
                        {renderedVideoPath}
                      </div>
                      <a
                        href={`http://localhost:8400/assets/video/${renderedVideoPath.split(/[/\\]/).pop()}`}
                        download
                        className="py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center gap-1.5 transition-colors shrink-0"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Download MP4
                      </a>
                    </div>

                    {qualityReport && (
                      <div className="space-y-1 pt-1 text-[11px] text-slate-300 border-t border-slate-700">
                        <div className="font-semibold text-slate-200">
                          {t("mediaStudioPage.renderSection.qualityReport", "Quality & Compliance Report")}:
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Video / audio codec:</span>
                          <span className="font-mono text-slate-300">
                            {qualityReport.video_codec || "—"} / {qualityReport.audio_codec || "—"}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Measured video / audio:</span>
                          <span className="font-mono text-slate-300">
                            {qualityReport.video_duration_sec ?? "—"}s / {qualityReport.audio_duration_sec ?? "—"}s
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>FFprobe verified:</span>
                          <span className="font-mono text-slate-300">
                            {qualityReport.ffprobe_verified ? "Yes" : "No"} · sync delta {qualityReport.duration_sync_delta ?? "—"}s
                          </span>
                        </div>
                        {qualityReport.timing_limitation && (
                          <p className="pt-1 text-slate-400">{qualityReport.timing_limitation}</p>
                        )}
                        {qualityReport.issues?.length > 0 && (
                          <p className="pt-1 text-orange-200">{qualityReport.issues.join("; ")}</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
