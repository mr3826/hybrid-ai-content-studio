"use client";

import { useEffect, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Boxes,
  CheckCircle2,
  Clock,
  ExternalLink,
  Eye,
  FileCheck,
  FolderArchive,
  Image as ImageIcon,
  Layers,
  LayoutGrid,
  List,
  MoreVertical,
  Plus,
  RefreshCw,
  Search,
  Share2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Tag,
  Trash2,
  Upload,
  Video,
  Wand2,
} from "lucide-react";
import {
  MediaAsset,
  PublishableItemSummary,
  Scene,
  ScriptDraft,
  StoryboardValidationResult,
  createScene,
  decomposeScript,
  deleteScene,
  generateScenePlaceholder,
  getScriptByItem,
  listMediaAssets,
  listPublishableItems,
  listScriptScenes,
  registerMediaAsset,
  reorderScenes,
  updateScene,
  validateStoryboard,
} from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

const VISUAL_PRIORITY_META: Record<
  string,
  { rank: number; labelEn: string; labelBn: string; color: string; bg: string; border: string }
> = {
  real_screen_recording: {
    rank: 1,
    labelEn: "Rank 1: Real Screen Recording",
    labelBn: "র‌্যাংক ১: স্ক্রিন রেকর্ডিং",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
  },
  benchmark_chart: {
    rank: 2,
    labelEn: "Rank 2: Benchmark Chart",
    labelBn: "র‌্যাংক ২: বেঞ্চমার্ক চার্ট",
    color: "text-cyan-400",
    bg: "bg-cyan-500/10",
    border: "border-cyan-500/30",
  },
  code_terminal: {
    rank: 3,
    labelEn: "Rank 3: Code / Terminal",
    labelBn: "র‌্যাংক ৩: কোড ও টার্মিনাল",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
  },
  workflow_diagram: {
    rank: 4,
    labelEn: "Rank 4: Workflow Diagram",
    labelBn: "র‌্যাংক ৪: আর্কিটেকচার ডায়াগ্রাম",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    border: "border-indigo-500/30",
  },
  product_screenshot: {
    rank: 5,
    labelEn: "Rank 5: Product Screenshot",
    labelBn: "র‌্যাংক ৫: স্ক্রিনশট",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "border-purple-500/30",
  },
  original_motion_graphic: {
    rank: 6,
    labelEn: "Rank 6: Motion Graphic",
    labelBn: "র‌্যাংক ৬: মোশন গ্রাফিক",
    color: "text-pink-400",
    bg: "bg-pink-500/10",
    border: "border-pink-500/30",
  },
  generated_visual: {
    rank: 7,
    labelEn: "Rank 7: Generated Fallback",
    labelBn: "র‌্যাংক ৭: জেনারেটেড ফলব্যাক",
    color: "text-slate-400",
    bg: "bg-slate-500/10",
    border: "border-slate-500/30",
  },
};

export default function SceneStudioPage() {
  const { t, isBangla } = useLanguage();

  // State: publishable scripts
  const [items, setItems] = useState<PublishableItemSummary[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<string>("");
  const [activeScript, setActiveScript] = useState<ScriptDraft | null>(null);

  // State: scenes
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loadingScenes, setLoadingScenes] = useState(false);
  const [decomposing, setDecomposing] = useState(false);

  // State: validation
  const [validation, setValidation] = useState<StoryboardValidationResult | null>(null);
  const [validating, setValidating] = useState(false);

  // State: view mode
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");

  // State: media assets
  const [mediaAssets, setMediaAssets] = useState<MediaAsset[]>([]);
  const [showAssetModal, setShowAssetModal] = useState(false);
  const [selectedSceneForAsset, setSelectedSceneForAsset] = useState<string | null>(null);
  const [uploadingAsset, setUploadingAsset] = useState(false);
  const [newAssetName, setNewAssetName] = useState("");
  const [newAssetType, setNewAssetType] = useState("chart");
  const [newAssetLicense, setNewAssetLicense] = useState("Self-Created");
  const [newAssetFilePath, setNewAssetFilePath] = useState("");

  // State: manual scene modal
  const [showSceneModal, setShowSceneModal] = useState(false);
  const [editingScene, setEditingScene] = useState<Scene | null>(null);
  const [manualNarration, setManualNarration] = useState("");
  const [manualTiming, setManualTiming] = useState(3.0);
  const [manualVisualType, setManualVisualType] = useState("real_screen_recording");
  const [manualOnScreenText, setManualOnScreenText] = useState("");

  // Load publishable items
  const loadPublishableItems = async () => {
    try {
      const data = await listPublishableItems();
      setItems(data);
      if (data.length > 0 && !selectedItemId) {
        setSelectedItemId(data[0].id);
      }
    } catch (e) {
      console.error("Failed to load publishable items:", e);
    }
  };

  // Load script & scenes when item selected
  useEffect(() => {
    loadPublishableItems();
    loadMediaCatalog();
  }, []);

  const loadMediaCatalog = async () => {
    try {
      const assets = await listMediaAssets();
      setMediaAssets(assets);
    } catch (e) {
      console.error("Failed to load media assets:", e);
    }
  };

  const loadScriptAndScenes = async (itemId: string) => {
    if (!itemId) return;
    try {
      setLoadingScenes(true);
      const script = await getScriptByItem(itemId);
      setActiveScript(script);

      if (script) {
        const sceneList = await listScriptScenes(script.id);
        setScenes(sceneList);

        if (sceneList.length > 0) {
          runValidation(script.id);
        } else {
          setValidation(null);
        }
      } else {
        setScenes([]);
        setValidation(null);
      }
    } catch (e) {
      console.error("Failed to load script or scenes:", e);
      setActiveScript(null);
      setScenes([]);
      setValidation(null);
    } finally {
      setLoadingScenes(false);
    }
  };

  useEffect(() => {
    if (selectedItemId) {
      loadScriptAndScenes(selectedItemId);
    }
  }, [selectedItemId]);

  const handleDecompose = async () => {
    if (!activeScript) return;
    try {
      setDecomposing(true);
      const decomposed = await decomposeScript(activeScript.id, true);
      setScenes(decomposed);
      await runValidation(activeScript.id);
    } catch (e) {
      console.error("Decomposition failed:", e);
    } finally {
      setDecomposing(false);
    }
  };

  const runValidation = async (scriptId: string) => {
    try {
      setValidating(true);
      const res = await validateStoryboard(scriptId);
      setValidation(res);
    } catch (e) {
      console.error("Validation failed:", e);
    } finally {
      setValidating(false);
    }
  };

  const handleGeneratePlaceholder = async (sceneId: string) => {
    try {
      const updated = await generateScenePlaceholder(sceneId);
      setScenes((prev) => prev.map((s) => (s.id === sceneId ? updated : s)));
      if (activeScript) {
        runValidation(activeScript.id);
      }
    } catch (e) {
      console.error("Placeholder generation failed:", e);
    }
  };

  const handleReorder = async (direction: "up" | "down", index: number) => {
    if (!activeScript) return;
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= scenes.length) return;

    const newScenes = [...scenes];
    const temp = newScenes[index];
    newScenes[index] = newScenes[targetIndex];
    newScenes[targetIndex] = temp;

    setScenes(newScenes);
    try {
      const sceneIds = newScenes.map((s) => s.id);
      await reorderScenes(activeScript.id, sceneIds);
      runValidation(activeScript.id);
    } catch (e) {
      console.error("Reorder failed:", e);
    }
  };

  const handleDeleteScene = async (sceneId: string) => {
    if (!confirm(isBangla ? "আপনি কি নিশ্চিতভাবে এই সিনটি মুছে ফেলতে চান?" : "Are you sure you want to delete this scene?")) return;
    try {
      await deleteScene(sceneId);
      setScenes((prev) => prev.filter((s) => s.id !== sceneId));
      if (activeScript) {
        runValidation(activeScript.id);
      }
    } catch (e) {
      console.error("Delete scene failed:", e);
    }
  };

  const handleSaveScene = async () => {
    if (!activeScript || !manualNarration.trim()) return;
    try {
      if (editingScene) {
        const updated = await updateScene(editingScene.id, {
          narration: manualNarration,
          timing_estimate: manualTiming,
          visual_type: manualVisualType,
          on_screen_text: manualOnScreenText || undefined,
        });
        setScenes((prev) => prev.map((s) => (s.id === editingScene.id ? updated : s)));
      } else {
        const created = await createScene({
          script_id: activeScript.id,
          scene_order: scenes.length + 1,
          narration: manualNarration,
          timing_estimate: manualTiming,
          visual_type: manualVisualType,
          on_screen_text: manualOnScreenText || undefined,
        });
        setScenes((prev) => [...prev, created]);
      }
      setShowSceneModal(false);
      setEditingScene(null);
      setManualNarration("");
      setManualOnScreenText("");
      runValidation(activeScript.id);
    } catch (e) {
      console.error("Save scene failed:", e);
    }
  };

  const handleRegisterAsset = async () => {
    if (!newAssetName.trim()) return;
    try {
      setUploadingAsset(true);
      const created = await registerMediaAsset({
        name: newAssetName,
        asset_type: newAssetType,
        license_type: newAssetLicense,
        file_path: newAssetFilePath || undefined,
        tags: [newAssetType, "scene-studio"],
      });
      setMediaAssets((prev) => [created, ...prev]);

      if (selectedSceneForAsset) {
        await updateScene(selectedSceneForAsset, {
          visual_source: created.file_path,
          asset_rights_record_id: created.asset_rights_record_id || undefined,
          status: "READY",
        });
        if (activeScript) {
          loadScriptAndScenes(selectedItemId);
        }
      }

      setShowAssetModal(false);
      setSelectedSceneForAsset(null);
      setNewAssetName("");
      setNewAssetFilePath("");
    } catch (e) {
      console.error("Register asset failed:", e);
    } finally {
      setUploadingAsset(false);
    }
  };

  const handleAssignExistingAsset = async (asset: MediaAsset) => {
    if (!selectedSceneForAsset) return;
    try {
      await updateScene(selectedSceneForAsset, {
        visual_source: asset.file_path,
        asset_rights_record_id: asset.asset_rights_record_id || undefined,
        status: "READY",
      });
      if (activeScript) {
        loadScriptAndScenes(selectedItemId);
      }
      setShowAssetModal(false);
      setSelectedSceneForAsset(null);
    } catch (e) {
      console.error("Assign asset failed:", e);
    }
  };

  const totalDuration = scenes.reduce((acc, s) => acc + (s.timing_estimate || 0), 0);
  const empiricalCount = scenes.filter((s) =>
    ["real_screen_recording", "benchmark_chart", "code_terminal"].includes(s.visual_type)
  ).length;
  const empiricalRatio = scenes.length > 0 ? Math.round((empiricalCount / scenes.length) * 100) : 0;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-20">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center gap-1 font-mono">
              <Video className="w-3.5 h-3.5" />
              Phase 15: Scene + Asset Studio
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {t("sceneStudioPage.title", "Scene & Asset Studio")}
          </h1>
          <p className="text-sm text-slate-400 max-w-2xl mt-1">
            {t(
              "sceneStudioPage.subtitle",
              "Deconstruct scripts into visual storyboard scenes, enforce evidence visual hierarchy & link verified media assets."
            )}
          </p>
        </div>

        {/* Script Selection Dropdown & Controls */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex flex-col">
            <label className="text-[11px] font-semibold text-slate-400 mb-1">
              {t("sceneStudioPage.scriptSelector", "Select Approved Script")}
            </label>
            <select
              value={selectedItemId}
              onChange={(e) => setSelectedItemId(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none min-w-[240px]"
            >
              {items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.working_title} ({item.format} • {item.status})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleDecompose}
            disabled={!activeScript || decomposing}
            className="self-end px-3.5 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Wand2 className={`w-3.5 h-3.5 ${decomposing ? "animate-spin" : ""}`} />
            <span>
              {decomposing
                ? t("sceneStudioPage.decomposing", "Decomposing...")
                : t("sceneStudioPage.decomposeBtn", "Auto-Decompose")}
            </span>
          </button>

          <button
            onClick={() => {
              setEditingScene(null);
              setManualNarration("");
              setManualOnScreenText("");
              setManualTiming(3.0);
              setShowSceneModal(true);
            }}
            disabled={!activeScript}
            className="self-end px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 disabled:opacity-50 text-slate-200 flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{t("sceneStudioPage.addScene", "Add Scene")}</span>
          </button>
        </div>
      </div>

      {/* Storyboard Telemetry & Quality Verification Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total Scenes */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">{t("sceneStudioPage.stats.totalScenes", "Total Scenes")}</p>
            <p className="text-xl font-bold text-white mt-0.5">{scenes.length}</p>
          </div>
        </div>

        {/* Total Duration */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">
              {t("sceneStudioPage.stats.totalDuration", "Total Duration")}
            </p>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-xl font-bold text-white">{totalDuration.toFixed(1)}s</span>
              {activeScript?.target_duration_sec && (
                <span className="text-xs text-slate-400 font-mono">
                  / {activeScript.target_duration_sec}s target
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Empirical Visual Ratio */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">
              {t("sceneStudioPage.stats.empiricalRatio", "Empirical Ratio")}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xl font-bold text-emerald-400">{empiricalRatio}%</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                {empiricalCount}/{scenes.length}
              </span>
            </div>
          </div>
        </div>

        {/* Storyboard Gate Status */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
              validation?.passed
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-amber-500/10 text-amber-400"
            }`}
          >
            {validation?.passed ? <CheckCircle2 className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">
              {t("sceneStudioPage.stats.status", "Storyboard Status")}
            </p>
            <p className="text-sm font-semibold text-white mt-0.5">
              {validation?.passed ? (isBangla ? "গেটে উত্তীর্ণ" : "QC Verified") : (isBangla ? "রিভিউ প্রয়োজন" : "Needs Review")}
            </p>
          </div>
        </div>
      </div>

      {/* Visual Priority Hierarchy Strip */}
      <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            7-Level Visual Priority Hierarchy (Evidence First)
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setViewMode("list")}
              className={`p-1.5 rounded text-xs ${
                viewMode === "list" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <List className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded text-xs ${
                viewMode === "grid" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {Object.entries(VISUAL_PRIORITY_META).map(([key, meta]) => (
            <div
              key={key}
              className={`px-2 py-1 rounded text-[11px] font-mono border flex items-center gap-1.5 ${meta.bg} ${meta.color} ${meta.border}`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current" />
              <span>{isBangla ? meta.labelBn : meta.labelEn}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Storyboard Scene Editor Grid / List */}
      {scenes.length === 0 ? (
        <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800/80 space-y-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 mx-auto flex items-center justify-center">
            <Video className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">
              {t("sceneStudioPage.emptyStoryboard", "No storyboard scenes generated yet.")}
            </h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
              Select an approved script draft from the dropdown and click &quot;Auto-Decompose&quot; to transform script
              sections into paced visual scenes.
            </p>
          </div>
          <button
            onClick={handleDecompose}
            disabled={!activeScript || decomposing}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white inline-flex items-center gap-1.5"
          >
            <Wand2 className="w-4 h-4" />
            <span>{t("sceneStudioPage.decomposeBtn", "Auto-Decompose Script")}</span>
          </button>
        </div>
      ) : viewMode === "list" ? (
        /* Sequence List View */
        <div className="space-y-3">
          {scenes.map((scene, idx) => {
            const meta = VISUAL_PRIORITY_META[scene.visual_type] || VISUAL_PRIORITY_META.generated_visual;
            return (
              <div
                key={scene.id}
                className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all flex flex-col md:flex-row gap-4 items-start justify-between"
              >
                {/* Left: Reorder & Number */}
                <div className="flex items-center gap-2 shrink-0">
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => handleReorder("up", idx)}
                      disabled={idx === 0}
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-30 text-slate-300"
                    >
                      <ArrowUp className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleReorder("down", idx)}
                      disabled={idx === scenes.length - 1}
                      className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-30 text-slate-300"
                    >
                      <ArrowDown className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center font-mono font-bold text-xs text-white">
                    #{scene.scene_order}
                  </div>
                </div>

                {/* Center: Narration, Visual Details, & On-screen text */}
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Visual Type Pill */}
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-mono border font-medium ${meta.bg} ${meta.color} ${meta.border}`}
                    >
                      {isBangla ? meta.labelBn : meta.labelEn}
                    </span>

                    {/* Duration */}
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-amber-400" />
                      {scene.timing_estimate}s
                    </span>

                    {/* Transition */}
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800/80 text-slate-400">
                      {scene.transition}
                    </span>

                    {/* Evidence Ref if any */}
                    {scene.evidence_reference && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800 flex items-center gap-1">
                        <FileCheck className="w-3 h-3" />
                        {scene.evidence_reference}
                      </span>
                    )}

                    {/* Asset Rights Badge */}
                    {scene.asset_rights ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3" />
                        {scene.asset_rights.license_type} (Verified)
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400">
                        Local Asset
                      </span>
                    )}
                  </div>

                  {/* Narration */}
                  <p className="text-sm text-slate-200 leading-relaxed font-sans">{scene.narration}</p>

                  {/* On-screen Text */}
                  {scene.on_screen_text && (
                    <div className="flex items-center gap-1.5 text-xs text-amber-300/90 font-mono bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20 w-fit">
                      <Tag className="w-3 h-3 text-amber-400" />
                      <span>ON-SCREEN: &quot;{scene.on_screen_text}&quot;</span>
                    </div>
                  )}

                  {/* Visual Source path if generated */}
                  {scene.visual_source && (
                    <div className="text-[11px] font-mono text-slate-400 truncate max-w-xl">
                      Source: {scene.visual_source}
                    </div>
                  )}
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleGeneratePlaceholder(scene.id)}
                    title={isBangla ? "অফলাইন প্রিভিউ তৈরি করুন" : "Generate local SVG card"}
                    className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors flex items-center gap-1 text-xs"
                  >
                    <Wand2 className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="hidden sm:inline">Preview</span>
                  </button>

                  <button
                    onClick={() => {
                      setSelectedSceneForAsset(scene.id);
                      setShowAssetModal(true);
                    }}
                    title={isBangla ? "মিডিয়া লাইব্রেরি থেকে যুক্ত করুন" : "Assign from Media Catalog"}
                    className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors flex items-center gap-1 text-xs"
                  >
                    <ImageIcon className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="hidden sm:inline">Asset</span>
                  </button>

                  <button
                    onClick={() => {
                      setEditingScene(scene);
                      setManualNarration(scene.narration);
                      setManualTiming(scene.timing_estimate);
                      setManualVisualType(scene.visual_type);
                      setManualOnScreenText(scene.on_screen_text || "");
                      setShowSceneModal(true);
                    }}
                    className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors"
                  >
                    <MoreVertical className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => handleDeleteScene(scene.id)}
                    className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-400 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Grid Cards View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenes.map((scene) => {
            const meta = VISUAL_PRIORITY_META[scene.visual_type] || VISUAL_PRIORITY_META.generated_visual;
            return (
              <div
                key={scene.id}
                className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-bold text-white bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                      #{scene.scene_order}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono border font-medium ${meta.bg} ${meta.color} ${meta.border}`}
                    >
                      {isBangla ? meta.labelBn : meta.labelEn}
                    </span>
                    <span className="text-xs font-mono text-amber-400">{scene.timing_estimate}s</span>
                  </div>

                  <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed">{scene.narration}</p>

                  {scene.on_screen_text && (
                    <div className="text-[11px] font-mono text-amber-300 bg-amber-500/10 px-2 py-1 rounded border border-amber-500/20">
                      ON-SCREEN: {scene.on_screen_text}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                  <span className="text-[10px] font-mono text-slate-400">{scene.transition}</span>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleGeneratePlaceholder(scene.id)}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-400 text-[11px] font-medium"
                    >
                      Preview
                    </button>
                    <button
                      onClick={() => {
                        setSelectedSceneForAsset(scene.id);
                        setShowAssetModal(true);
                      }}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-400 text-[11px] font-medium"
                    >
                      Asset
                    </button>
                    <button
                      onClick={() => handleDeleteScene(scene.id)}
                      className="p-1 rounded text-rose-400 hover:bg-rose-500/20"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Media Catalog Drawer / Selector Modal */}
      {showAssetModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <ImageIcon className="w-4 h-4 text-emerald-400" />
                  {t("sceneStudioPage.mediaLibrary", "Local Media Asset Catalog")}
                </h3>
                <p className="text-xs text-slate-400">
                  Select a local asset or register new media with rights provenance.
                </p>
              </div>
              <button
                onClick={() => {
                  setShowAssetModal(false);
                  setSelectedSceneForAsset(null);
                }}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-4 flex-1">
              {/* Register New Asset Inline Form */}
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                  <Upload className="w-3.5 h-3.5 text-indigo-400" />
                  {t("sceneStudioPage.uploadAsset", "Register Local Media Asset")}
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <input
                    type="text"
                    placeholder="Asset Title (e.g. Local Terminal Demo GIF)"
                    value={newAssetName}
                    onChange={(e) => setNewAssetName(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                  />
                  <select
                    value={newAssetType}
                    onChange={(e) => setNewAssetType(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                  >
                    <option value="screen_recording">Screen Recording (Rank 1)</option>
                    <option value="chart">Benchmark Chart (Rank 2)</option>
                    <option value="terminal">Code Terminal (Rank 3)</option>
                    <option value="diagram">Workflow Diagram (Rank 4)</option>
                    <option value="screenshot">Screenshot (Rank 5)</option>
                    <option value="motion_graphic">Motion Graphic (Rank 6)</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Local File Path (e.g. data/assets/demo.mp4)"
                    value={newAssetFilePath}
                    onChange={(e) => setNewAssetFilePath(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                  />
                  <select
                    value={newAssetLicense}
                    onChange={(e) => setNewAssetLicense(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200"
                  >
                    <option value="Self-Created">Self-Created (Safe)</option>
                    <option value="CC0">CC0 (Public Domain)</option>
                    <option value="MIT">MIT License</option>
                    <option value="CC-BY-4.0">CC-BY-4.0 (Attribution Required)</option>
                  </select>
                </div>
                <button
                  onClick={handleRegisterAsset}
                  disabled={uploadingAsset || !newAssetName.trim()}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>
                    {uploadingAsset ? t("sceneStudioPage.uploading", "Registering...") : "Save & Attach Asset"}
                  </span>
                </button>
              </div>

              {/* Existing Assets List */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400">Available Catalog Assets</span>
                {mediaAssets.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No media assets found in catalog.</p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {mediaAssets.map((asset) => (
                      <div
                        key={asset.id}
                        className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between gap-2"
                      >
                        <div className="overflow-hidden">
                          <p className="text-xs font-medium text-white truncate">{asset.name}</p>
                          <p className="text-[10px] font-mono text-slate-400">
                            {asset.asset_type} • Priority {asset.visual_priority}
                          </p>
                        </div>
                        <button
                          onClick={() => handleAssignExistingAsset(asset)}
                          className="px-2.5 py-1 text-xs rounded bg-indigo-600 hover:bg-indigo-500 text-white shrink-0"
                        >
                          Select
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manual Scene Edit Modal */}
      {showSceneModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-5 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">
                {editingScene ? t("sceneStudioPage.saveScene", "Edit Scene") : t("sceneStudioPage.addScene", "Add Scene")}
              </h3>
              <button onClick={() => setShowSceneModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1 font-medium">
                  {t("sceneStudioPage.narration", "Voiceover Narration")}
                </label>
                <textarea
                  rows={3}
                  value={manualNarration}
                  onChange={(e) => setManualNarration(e.target.value)}
                  placeholder="Narration script text for this scene..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-200"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    {t("sceneStudioPage.timing", "Duration (sec)")}
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="60"
                    value={manualTiming}
                    onChange={(e) => setManualTiming(parseFloat(e.target.value) || 3.0)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1 font-medium">
                    {t("sceneStudioPage.visualPriority.label", "Visual Priority")}
                  </label>
                  <select
                    value={manualVisualType}
                    onChange={(e) => setManualVisualType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                  >
                    <option value="real_screen_recording">Rank 1: Screen Recording</option>
                    <option value="benchmark_chart">Rank 2: Benchmark Chart</option>
                    <option value="code_terminal">Rank 3: Code / Terminal</option>
                    <option value="workflow_diagram">Rank 4: Workflow Diagram</option>
                    <option value="product_screenshot">Rank 5: Screenshot</option>
                    <option value="original_motion_graphic">Rank 6: Motion Graphic</option>
                    <option value="generated_visual">Rank 7: Generated Visual</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1 font-medium">
                  {t("sceneStudioPage.onScreenText", "On-Screen Caption / Punch Text")}
                </label>
                <input
                  type="text"
                  value={manualOnScreenText}
                  onChange={(e) => setManualOnScreenText(e.target.value)}
                  placeholder="Optional punchy text e.g. 142 TOKENS/S"
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowSceneModal(false)}
                className="px-3 py-1.5 rounded-lg text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveScene}
                disabled={!manualNarration.trim()}
                className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold"
              >
                {t("sceneStudioPage.saveScene", "Save Scene")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
