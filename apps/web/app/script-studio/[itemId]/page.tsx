"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Wand2,
  ChevronDown,
  ChevronUp,
  History,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Scissors,
  Expand,
  Eye,
  FlaskConical,
  Repeat,
  XCircle,
  Check,
  FileText,
  Clock,
  BarChart3,
  Layers,
  Share2,
} from "lucide-react";
import {
  ScriptDraft,
  ScriptSectionDetail,
  ScriptQualityVerdict,
  ScriptRevisionSummary,
  DimensionCheckResult,
  RefinementType,
  getContentItem,
  getScriptByItem,
  generateScriptDraft,
  updateScriptSection,
  refineScriptSection,
  checkScriptQuality,
  approveScript,
  getScriptRevisions,
  restoreScriptRevision,
  ContentChildItem,
} from "@/lib/api";

const SECTION_LABELS: Record<string, string> = {
  hook: "Hook",
  problem_context: "Problem Context",
  method_test: "Method & Test",
  evidence: "Evidence",
  result: "Result",
  interpretation: "Interpretation",
  cta: "Call to Action",
};

const SECTION_COLORS: Record<string, string> = {
  hook: "border-amber-500/30 bg-amber-500/5",
  problem_context: "border-slate-500/30 bg-slate-500/5",
  method_test: "border-blue-500/30 bg-blue-500/5",
  evidence: "border-emerald-500/30 bg-emerald-500/5",
  result: "border-purple-500/30 bg-purple-500/5",
  interpretation: "border-cyan-500/30 bg-cyan-500/5",
  cta: "border-rose-500/30 bg-rose-500/5",
};

const DIMENSION_COLORS: Record<string, { bg: string; text: string; bar: string }> = {
  evidence: { bg: "bg-emerald-500/10", text: "text-emerald-400", bar: "bg-emerald-500" },
  brand: { bg: "bg-purple-500/10", text: "text-purple-400", bar: "bg-purple-500" },
  originality: { bg: "bg-amber-500/10", text: "text-amber-400", bar: "bg-amber-500" },
  viewer_value: { bg: "bg-blue-500/10", text: "text-blue-400", bar: "bg-blue-500" },
  niche_fit: { bg: "bg-cyan-500/10", text: "text-cyan-400", bar: "bg-cyan-500" },
  repetition: { bg: "bg-slate-500/10", text: "text-slate-400", bar: "bg-slate-400" },
};

const REFINEMENT_ACTIONS: { type: RefinementType; label: string; icon: any; desc: string }[] = [
  { type: "shorten", label: "Shorten", icon: Scissors, desc: "Tighten phrasing" },
  { type: "expand", label: "Expand", icon: Expand, desc: "Add detail" },
  { type: "make_clearer", label: "Clearer", icon: Eye, desc: "Simplify language" },
  { type: "more_evidence", label: "More Evidence", icon: FlaskConical, desc: "Inject data" },
  { type: "regenerate", label: "Regenerate", icon: Repeat, desc: "Fresh phrasing" },
];

export default function ScriptStudioPage() {
  const params = useParams();
  const router = useRouter();
  const itemId = params.itemId as string;

  const [item, setItem] = useState<ContentChildItem | null>(null);
  const [script, setScript] = useState<ScriptDraft | null>(null);
  const [quality, setQuality] = useState<ScriptQualityVerdict | null>(null);
  const [revisions, setRevisions] = useState<ScriptRevisionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [refining, setRefining] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editNarration, setEditNarration] = useState("");
  const [editVisualCue, setEditVisualCue] = useState("");
  const [showRevisions, setShowRevisions] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [reviewer, setReviewer] = useState("creator");

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const contentItem = await getContentItem(itemId);
      setItem(contentItem as ContentChildItem);

      const existingScript = await getScriptByItem(itemId);
      if (existingScript) {
        setScript(existingScript);
        if (existingScript.quality_scores) {
          setQuality(existingScript.quality_scores);
        }
        const revs = await getScriptRevisions(existingScript.id);
        setRevisions(revs);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [itemId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      const draft = await generateScriptDraft(itemId, 60);
      setScript(draft);
      if (draft.quality_scores) setQuality(draft.quality_scores);
      const revs = await getScriptRevisions(draft.id);
      setRevisions(revs);
    } catch (err: any) {
      setError(err.message || "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleRefine = async (sectionId: string, type: RefinementType) => {
    if (!script) return;
    try {
      setRefining(sectionId);
      setError(null);
      const result = await refineScriptSection(script.id, sectionId, type);
      setScript(result.script);
      const revs = await getScriptRevisions(script.id);
      setRevisions(revs);
    } catch (err: any) {
      setError(err.message || "Refinement failed");
    } finally {
      setRefining(null);
    }
  };

  const handleSaveSection = async (sectionId: string) => {
    if (!script) return;
    try {
      setError(null);
      const updated = await updateScriptSection(script.id, sectionId, {
        narration: editNarration,
        visual_cue: editVisualCue,
      });
      setScript(updated);
      setEditingSection(null);
      const revs = await getScriptRevisions(script.id);
      setRevisions(revs);
    } catch (err: any) {
      setError(err.message || "Save failed");
    }
  };

  const handleQualityCheck = async () => {
    if (!script) return;
    try {
      setChecking(true);
      setError(null);
      const verdict = await checkScriptQuality(script.id);
      setQuality(verdict);
    } catch (err: any) {
      setError(err.message || "Quality check failed");
    } finally {
      setChecking(false);
    }
  };

  const handleApprove = async () => {
    if (!script) return;
    try {
      setApproving(true);
      setError(null);
      const approved = await approveScript(script.id, reviewer, overrideReason || undefined);
      setScript(approved);
      setShowApproveModal(false);
      setOverrideReason("");
    } catch (err: any) {
      const msg = err.message || "Approval failed";
      if (msg.includes("422")) {
        setShowApproveModal(true);
      }
      setError(msg);
    } finally {
      setApproving(false);
    }
  };

  const handleRestore = async (revisionId: string) => {
    if (!script) return;
    try {
      setError(null);
      const restored = await restoreScriptRevision(script.id, revisionId);
      setScript(restored);
      const revs = await getScriptRevisions(script.id);
      setRevisions(revs);
    } catch (err: any) {
      setError(err.message || "Restore failed");
    }
  };

  const startEditing = (section: ScriptSectionDetail) => {
    setEditingSection(section.id);
    setEditNarration(section.narration);
    setEditVisualCue(section.visual_cue);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-3 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span className="text-sm">Loading Script Studio…</span>
        </div>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center space-y-4">
        <XCircle className="w-12 h-12 text-rose-400 mx-auto" />
        <h2 className="text-lg font-bold text-white">Content Item Not Found</h2>
        <Link href="/content-families" className="text-indigo-400 hover:underline text-sm">
          ← Back to Content Families
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-full flex flex-col gap-4">
      {/* Header */}
      <div className="shrink-0 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors shrink-0"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-purple-400 shrink-0" />
              <h1 className="text-base sm:text-lg font-bold text-white">Script Studio</h1>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              {item.working_title} · <span className="text-purple-300">{item.format?.replace(/_/g, " ")}</span> · {item.platform_target}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {script && (
            <>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                v{script.version} · {script.status}
              </span>
              <span className="text-[11px] text-slate-500">
                {script.total_word_count} words · ~{script.estimated_duration_sec}s
              </span>
            </>
          )}
          {script?.is_approved && (
            <>
              <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                APPROVED
              </span>
              <Link
                href={`/publishing/${itemId}`}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition-colors"
              >
                <Share2 className="w-3.5 h-3.5" />
                Publishing Assistant &rarr;
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="shrink-0 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-rose-400 hover:text-rose-200 font-bold">×</button>
        </div>
      )}

      {/* No Script — Generate */}
      {!script && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-4 max-w-md">
            <div className="w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center mx-auto">
              <Sparkles className="w-8 h-8 text-purple-400" />
            </div>
            <h2 className="text-lg font-bold text-white">Generate Evidence-Grounded Script</h2>
            <p className="text-sm text-slate-400">
              Creates a structured {item.format?.replace(/_/g, " ")} script with sections grounded in verified research claims, 
              brand voice rules, and niche boundaries.
            </p>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-6 py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20 flex items-center gap-2 mx-auto transition-all"
            >
              {generating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Generating…
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4" />
                  Generate Script Draft
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Script Editor — Responsive Layout */}
      {script && (
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">

          {/* LEFT COLUMN: Evidence Reference Drawer */}
          <div className="col-span-1 lg:col-span-3 order-3 lg:order-1 overflow-y-auto rounded-xl bg-slate-900/60 border border-slate-800 p-4 space-y-4">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Evidence Context
            </h3>

            <div className="space-y-2">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                <p className="font-semibold text-slate-300">Parent Family</p>
                <p className="text-slate-400">{item.family_title || "—"}</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                <p className="font-semibold text-slate-300">Angle</p>
                <p className="text-slate-400 leading-relaxed">{item.angle}</p>
              </div>

              {item.original_value_connection && (
                <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-500/20 text-xs space-y-1">
                  <p className="font-semibold text-indigo-300">Original Value</p>
                  <p className="text-indigo-200/70 leading-relaxed">{item.original_value_connection}</p>
                </div>
              )}

              {item.viewer_value && (
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                  <p className="font-semibold text-slate-300">Viewer Value</p>
                  <p className="text-slate-400 leading-relaxed">{item.viewer_value}</p>
                </div>
              )}
            </div>

            {/* Linked Claims */}
            {item.evidence_selections && item.evidence_selections.length > 0 && (
              <div className="space-y-2">
                <p className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">
                  Linked Claims ({item.evidence_selections.length})
                </p>
                {item.evidence_selections.map((sel: any) => (
                  <div
                    key={sel.id}
                    className="p-2.5 rounded-lg bg-emerald-950/10 border border-emerald-500/20 text-xs space-y-0.5"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-1 py-0.5 rounded">
                        {sel.claim_type || "claim"}
                      </span>
                      {sel.is_verified && (
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      )}
                    </div>
                    <p className="text-slate-200 leading-relaxed">{sel.claim_text}</p>
                    {sel.relevance_note && (
                      <p className="text-slate-500 italic text-[11px]">{sel.relevance_note}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* CENTER COLUMN: Section Editor */}
          <div className="col-span-1 lg:col-span-6 order-1 lg:order-2 overflow-y-auto space-y-3">
            {script.sections
              .sort((a, b) => a.order_index - b.order_index)
              .map((section) => {
                const isEditing = editingSection === section.id;
                const isRefining = refining === section.id;
                const colorClass = SECTION_COLORS[section.section_type] || "border-slate-500/30 bg-slate-500/5";

                return (
                  <div
                    key={section.id}
                    className={`rounded-xl border p-4 transition-all ${colorClass} ${isEditing ? "ring-1 ring-purple-500/40" : ""}`}
                  >
                    {/* Section Header */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-900/80 text-slate-300 border border-slate-700">
                          {section.order_index + 1}
                        </span>
                        <h4 className="text-sm font-bold text-white">
                          {SECTION_LABELS[section.section_type] || section.section_type}
                        </h4>
                        <span className="text-[11px] text-slate-500 font-mono">
                          {section.heading}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          {section.word_count}w
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          ~{section.estimated_seconds}s
                        </span>
                      </div>
                    </div>

                    {/* Narration */}
                    {isEditing ? (
                      <div className="space-y-2">
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Narration</label>
                        <textarea
                          value={editNarration}
                          onChange={(e) => setEditNarration(e.target.value)}
                          rows={4}
                          className="w-full p-3 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 outline-none resize-none"
                        />
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Visual Cue</label>
                        <input
                          type="text"
                          value={editVisualCue}
                          onChange={(e) => setEditVisualCue(e.target.value)}
                          className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500/30 outline-none"
                        />
                        <div className="flex items-center gap-2 pt-1">
                          <button
                            onClick={() => handleSaveSection(section.id)}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-600 text-white hover:bg-purple-500 transition-colors"
                          >
                            Save Changes
                          </button>
                          <button
                            onClick={() => setEditingSection(null)}
                            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <p
                          className="text-sm text-slate-200 leading-relaxed cursor-pointer hover:bg-slate-800/30 rounded p-2 -m-2 transition-colors"
                          onClick={() => startEditing(section)}
                          title="Click to edit"
                        >
                          {section.narration}
                        </p>
                        {section.visual_cue && (
                          <p className="text-[11px] text-slate-500 italic flex items-center gap-1">
                            <Eye className="w-3 h-3" />
                            {section.visual_cue}
                          </p>
                        )}

                        {/* Linked Claims Badges */}
                        {section.linked_claim_ids.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap">
                            {section.linked_claim_ids.map((cid) => (
                              <span key={cid} className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                claim:{cid.slice(0, 6)}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Refinement Actions */}
                    {!isEditing && !script.is_approved && (
                      <div className="flex items-center gap-1.5 mt-3 pt-2 border-t border-slate-800/60">
                        {REFINEMENT_ACTIONS.map(({ type, label, icon: Icon, desc }) => (
                          <button
                            key={type}
                            onClick={() => handleRefine(section.id, type)}
                            disabled={isRefining}
                            title={desc}
                            className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-semibold text-slate-400 hover:text-white hover:bg-slate-800 border border-transparent hover:border-slate-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            {isRefining ? (
                              <RefreshCw className="w-3 h-3 animate-spin" />
                            ) : (
                              <Icon className="w-3 h-3" />
                            )}
                            {label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
          </div>

          {/* RIGHT COLUMN: Quality + Revisions + Approve */}
          <div className="col-span-1 lg:col-span-3 order-2 lg:order-3 overflow-y-auto space-y-4">

            {/* Quality Dimensions */}
            <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <BarChart3 className="w-4 h-4 text-indigo-400" />
                  Quality Dimensions
                </h3>
                <button
                  onClick={handleQualityCheck}
                  disabled={checking}
                  className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-semibold text-indigo-400 hover:bg-indigo-500/10 border border-indigo-500/30 transition-colors disabled:opacity-40"
                >
                  {checking ? <RefreshCw className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                  Recheck
                </button>
              </div>

              {quality ? (
                <div className="space-y-2">
                  {Object.entries(quality.dimension_scores).map(([key, dim]) => {
                    const color = DIMENSION_COLORS[key] || DIMENSION_COLORS.repetition;
                    return (
                      <div key={key} className={`p-2.5 rounded-lg border border-slate-800 ${color.bg}`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-[11px] font-bold uppercase tracking-wider ${color.text}`}>
                            {key.replace(/_/g, " ")}
                          </span>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[11px] font-mono text-slate-300">{dim.score.toFixed(0)}</span>
                            {dim.passed ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                            ) : dim.is_blocking ? (
                              <XCircle className="w-3.5 h-3.5 text-rose-400" />
                            ) : (
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                            )}
                          </div>
                        </div>
                        {/* Score Bar */}
                        <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden mb-1">
                          <div
                            className={`h-full rounded-full ${color.bar} transition-all duration-500`}
                            style={{ width: `${Math.min(100, dim.score)}%` }}
                          />
                        </div>
                        <p className="text-[10px] text-slate-500 leading-relaxed">{dim.notes}</p>
                        {dim.flags.length > 0 && (
                          <div className="mt-1 space-y-0.5">
                            {dim.flags.map((f, i) => (
                              <p key={i} className="text-[10px] text-rose-400/80">⚠ {f}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Summary */}
                  <div className={`p-3 rounded-lg text-xs font-medium ${quality.is_approvable ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-300" : "bg-rose-500/10 border border-rose-500/30 text-rose-300"}`}>
                    {quality.summary}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500 text-center py-4">
                  Run a quality check to see dimension scores.
                </p>
              )}
            </div>

            {/* Revision History */}
            <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4 space-y-3">
              <button
                onClick={() => setShowRevisions(!showRevisions)}
                className="flex items-center justify-between w-full"
              >
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <History className="w-4 h-4 text-amber-400" />
                  Revisions ({revisions.length})
                </h3>
                {showRevisions ? (
                  <ChevronUp className="w-4 h-4 text-slate-500" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-slate-500" />
                )}
              </button>

              {showRevisions && (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {revisions.length === 0 ? (
                    <p className="text-xs text-slate-500 text-center py-2">No revisions yet.</p>
                  ) : (
                    revisions.map((rev) => (
                      <div
                        key={rev.id}
                        className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800 text-xs"
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-[10px] text-amber-400 bg-amber-500/10 px-1 py-0.5 rounded">
                              #{rev.revision_number}
                            </span>
                            <span className="font-semibold text-slate-300">{rev.trigger}</span>
                          </div>
                          <p className="text-[10px] text-slate-500 truncate max-w-[180px]">{rev.notes}</p>
                        </div>
                        {!script.is_approved && (
                          <button
                            onClick={() => handleRestore(rev.id)}
                            className="p-1 text-slate-500 hover:text-amber-400 hover:bg-slate-800 rounded transition-colors"
                            title="Restore this revision"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Human Gate Approval */}
            {!script.is_approved ? (
              <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4 space-y-3">
                <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-purple-400" />
                  Human Quality Gate
                </h3>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Final approval transitions this script to <span className="text-purple-300 font-semibold">SCRIPT_APPROVED</span> and 
                  locks the content item status. Blocking quality issues require an explicit override reason.
                </p>
                <button
                  onClick={() => {
                    if (quality && !quality.is_approvable) {
                      setShowApproveModal(true);
                    } else {
                      handleApprove();
                    }
                  }}
                  disabled={approving || !quality}
                  className="w-full px-4 py-2.5 rounded-xl font-semibold text-white bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 transition-all text-sm"
                >
                  {approving ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Approve Script
                </button>
              </div>
            ) : (
              <div className="rounded-xl bg-emerald-950/20 border border-emerald-500/30 p-4 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="w-5 h-5 shrink-0" />
                  <h3 className="text-xs font-bold uppercase tracking-wider">
                    Script Approved by Human Gate
                  </h3>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Approved by <span className="text-slate-200 font-semibold">{script.approved_by || "creator"}</span>. Script is locked and ready for offline export assembly and manual platform distribution.
                </p>
                <Link
                  href={`/publishing/${itemId}`}
                  className="w-full px-4 py-2.5 rounded-xl font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2 transition-all text-sm"
                >
                  <Share2 className="w-4 h-4" />
                  Open Publishing Assistant &rarr;
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Override Approval Modal */}
      {showApproveModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Quality Gate Override Required
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              This script has blocking quality issues. To approve, you must provide an explicit override reason explaining 
              why the quality gate should be bypassed.
            </p>
            {quality && quality.blocking_reasons.length > 0 && (
              <div className="space-y-1">
                {quality.blocking_reasons.map((reason, i) => (
                  <div key={i} className="px-2.5 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5 shrink-0" />
                    {reason.replace(/_/g, " ")}
                  </div>
                ))}
              </div>
            )}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Reviewer Name</label>
              <input
                type="text"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-purple-500 outline-none"
                placeholder="chief_editor"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Override Reason <span className="text-rose-400">*</span></label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                rows={3}
                className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-sm focus:border-purple-500 outline-none resize-none"
                placeholder="Explain why the quality gate should be overridden…"
              />
            </div>
            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={handleApprove}
                disabled={!overrideReason.trim() || approving}
                className="flex-1 px-4 py-2 rounded-lg font-semibold text-white bg-amber-600 hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm transition-colors"
              >
                {approving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Override & Approve
              </button>
              <button
                onClick={() => {
                  setShowApproveModal(false);
                  setOverrideReason("");
                }}
                className="px-4 py-2 rounded-lg font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
