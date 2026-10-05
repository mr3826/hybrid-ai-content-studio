"use client";

import { useEffect, useState } from "react";
import {
  Lightbulb,
  CheckCircle,
  XCircle,
  Clock,
  Sparkles,
  AlertTriangle,
  RefreshCw,
  Plus,
  ArrowRight,
  Info,
  ShieldCheck,
  ChevronDown,
  Layers,
} from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import {
  FeedbackLesson,
  FeedbackSummary,
  listFeedbackLessons,
  getFeedbackSummary,
  approveFeedbackLesson,
  rejectFeedbackLesson,
  applyFeedbackLesson,
  evaluateFeedback,
  createFeedbackLesson,
  explainFeedbackLesson,
  FeedbackExplainResponse,
} from "@/lib/api";

export default function FeedbackPage() {
  const { t } = useLanguage();

  const [lessons, setLessons] = useState<FeedbackLesson[]>([]);
  const [summary, setSummary] = useState<FeedbackSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("all");
  const [creatorNotesMap, setCreatorNotesMap] = useState<Record<string, string>>({});
  const [explanation, setExplanation] = useState<FeedbackExplainResponse | null>(null);

  // Manual Lesson Modal
  const [showManualModal, setShowManualModal] = useState(false);
  const [manualSaving, setManualSaving] = useState(false);
  const [manualForm, setManualForm] = useState({
    lesson_type: "hook_optimization",
    title: "",
    observation: "",
    impact_level: "MEDIUM",
    confidence_score: 0.85,
    target: "brand_profile",
    field: "avoid_vocabulary",
    action: "append",
    value: "",
    summary: "",
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [sumRes, lessonsRes] = await Promise.all([
        getFeedbackSummary(),
        listFeedbackLessons(),
      ]);
      setSummary(sumRes);
      setLessons(lessonsRes);
    } catch (err) {
      console.error("Failed to load feedback data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleEvaluate = async () => {
    try {
      setEvaluating(true);
      await evaluateFeedback(30, 25);
      await fetchData();
    } catch (err) {
      console.error("Evaluation failed:", err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      setActionLoading(id);
      const notes = creatorNotesMap[id];
      await approveFeedbackLesson(id, notes);
      await fetchData();
    } catch (err) {
      console.error("Approve failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (id: string) => {
    try {
      setActionLoading(id);
      const notes = creatorNotesMap[id];
      await rejectFeedbackLesson(id, notes);
      await fetchData();
    } catch (err) {
      console.error("Reject failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleApply = async (id: string) => {
    try {
      setActionLoading(id);
      await applyFeedbackLesson(id);
      await fetchData();
    } catch (err) {
      console.error("Apply failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleExplain = async (id: string) => {
    try {
      const exp = await explainFeedbackLesson(id);
      setExplanation(exp);
    } catch (err) {
      console.error("Explain failed:", err);
    }
  };

  const handleCreateManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualForm.title || !manualForm.observation || !manualForm.value) return;

    try {
      setManualSaving(true);
      await createFeedbackLesson({
        lesson_type: manualForm.lesson_type,
        title: manualForm.title,
        observation: manualForm.observation,
        impact_level: manualForm.impact_level,
        confidence_score: manualForm.confidence_score,
        proposed_adjustment: {
          target: manualForm.target,
          field: manualForm.field,
          action: manualForm.action,
          value: manualForm.value,
          summary: manualForm.summary || `Manual creator lesson: ${manualForm.title}`,
        },
      });
      setShowManualModal(false);
      setManualForm({
        lesson_type: "hook_optimization",
        title: "",
        observation: "",
        impact_level: "MEDIUM",
        confidence_score: 0.85,
        target: "brand_profile",
        field: "avoid_vocabulary",
        action: "append",
        value: "",
        summary: "",
      });
      await fetchData();
    } catch (err) {
      console.error("Failed to save manual lesson:", err);
    } finally {
      setManualSaving(false);
    }
  };

  const filteredLessons = lessons.filter((l) => {
    if (activeTab === "all") return true;
    return l.status === activeTab;
  });

  const getImpactBadgeClass = (impact: string) => {
    switch (impact) {
      case "HIGH":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "MEDIUM":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      default:
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PENDING":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5" />
            {t("feedbackPage.status.PENDING")}
          </span>
        );
      case "APPROVED":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <CheckCircle className="w-3.5 h-3.5" />
            {t("feedbackPage.status.APPROVED")}
          </span>
        );
      case "APPLIED":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Sparkles className="w-3.5 h-3.5" />
            {t("feedbackPage.status.APPLIED")}
          </span>
        );
      case "REJECTED":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="w-3.5 h-3.5" />
            {t("feedbackPage.status.REJECTED")}
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center font-bold">
              <Lightbulb className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              {t("feedbackPage.title")}
            </h1>
          </div>
          <p className="text-sm text-slate-400 max-w-2xl">
            {t("feedbackPage.subtitle")}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${evaluating ? "animate-spin" : ""}`} />
            {evaluating ? t("feedbackPage.evaluating") : t("feedbackPage.evaluateBtn")}
          </button>

          <button
            onClick={() => setShowManualModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm border border-slate-700 transition-all"
          >
            <Plus className="w-4 h-4" />
            {t("feedbackPage.addManualBtn")}
          </button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-amber-400" />
            {t("feedbackPage.kpis.pending")}
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.pending_count || 0}
          </div>
          <div className="text-xs text-amber-400/80 mt-2">
            Awaiting creator decision
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
            <CheckCircle className="w-4 h-4 text-sky-400" />
            {t("feedbackPage.kpis.approved")}
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.approved_count || 0}
          </div>
          <div className="text-xs text-sky-400/80 mt-2">
            Ready to apply to Brand DNA
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            {t("feedbackPage.kpis.applied")}
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.applied_count || 0}
          </div>
          <div className="text-xs text-emerald-400/80 mt-2">
            Integrated into memory & rules
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1.5">
            <XCircle className="w-4 h-4 text-rose-400" />
            {t("feedbackPage.kpis.rejected")}
          </div>
          <div className="text-2xl font-bold text-white">
            {summary?.rejected_count || 0}
          </div>
          <div className="text-xs text-rose-400/80 mt-2">
            Discarded by human creator
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-2">
        {["all", "PENDING", "APPROVED", "APPLIED", "REJECTED"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === tab
                ? "border-amber-500 text-amber-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab === "all" && t("feedbackPage.tabs.all")}
            {tab === "PENDING" && t("feedbackPage.tabs.pending")}
            {tab === "APPROVED" && t("feedbackPage.tabs.approved")}
            {tab === "APPLIED" && t("feedbackPage.tabs.applied")}
            {tab === "REJECTED" && t("feedbackPage.tabs.rejected")}
          </button>
        ))}
      </div>

      {/* Lessons List */}
      {loading ? (
        <div className="flex items-center justify-center p-12 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          {t("common.loading")}
        </div>
      ) : filteredLessons.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center">
          <Lightbulb className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-white mb-1">
            {t("feedbackPage.emptyState.title")}
          </h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mb-4">
            {t("feedbackPage.emptyState.desc")}
          </p>
          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-md shadow-indigo-600/20"
          >
            <RefreshCw className={`w-4 h-4 ${evaluating ? "animate-spin" : ""}`} />
            {t("feedbackPage.evaluateBtn")}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredLessons.map((lesson) => {
            const adj = lesson.proposed_adjustment || {};
            const isPending = lesson.status === "PENDING";
            const isApproved = lesson.status === "APPROVED";
            const isApplied = lesson.status === "APPLIED";
            const isRejected = lesson.status === "REJECTED";

            return (
              <div
                key={lesson.id}
                className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all space-y-4"
              >
                {/* Card Header */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {getStatusBadge(lesson.status)}

                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getImpactBadgeClass(
                          lesson.impact_level
                        )}`}
                      >
                        {t(`feedbackPage.impact.${lesson.impact_level}`) || lesson.impact_level}
                      </span>

                      <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                        {t(`feedbackPage.types.${lesson.lesson_type}`) || lesson.lesson_type}
                      </span>

                      {lesson.content_item_title && (
                        <span className="text-xs text-indigo-400 bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-800/40 truncate max-w-xs">
                          {lesson.content_item_title}
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-semibold text-white pt-1">
                      {lesson.title}
                    </h3>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <div className="text-right">
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider">
                        {t("feedbackPage.card.confidence")}
                      </div>
                      <div className="text-xs font-mono font-bold text-amber-400">
                        {Math.round(lesson.confidence_score * 100)}%
                      </div>
                    </div>

                    <button
                      onClick={() => handleExplain(lesson.id)}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-all border border-slate-700"
                      title={t("feedbackPage.card.explainBtn")}
                    >
                      <Info className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Observation Box */}
                <div className="bg-slate-950/50 border border-slate-800/80 rounded-lg p-3.5 space-y-2">
                  <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                    {t("feedbackPage.card.observationTitle")}
                  </div>
                  <p className="text-sm text-slate-300 leading-relaxed">
                    {lesson.observation}
                  </p>

                  {/* Evidence Pills */}
                  {lesson.evidence_data && Object.keys(lesson.evidence_data).length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1 border-t border-slate-800/50 mt-2">
                      {lesson.evidence_data.platform && (
                        <span className="text-[11px] bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                          Platform: <strong className="text-white">{lesson.evidence_data.platform}</strong>
                        </span>
                      )}
                      {lesson.evidence_data.views !== undefined && (
                        <span className="text-[11px] bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                          Views: <strong className="text-white">{lesson.evidence_data.views}</strong>
                        </span>
                      )}
                      {lesson.evidence_data.hook_retention_3s_pct !== undefined && (
                        <span className="text-[11px] bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                          3s Hook: <strong className="text-amber-400">{lesson.evidence_data.hook_retention_3s_pct}%</strong>
                        </span>
                      )}
                      {lesson.evidence_data.engagement_rate_pct !== undefined && (
                        <span className="text-[11px] bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                          Eng Rate: <strong className="text-sky-400">{lesson.evidence_data.engagement_rate_pct.toFixed(1)}%</strong>
                        </span>
                      )}
                      {lesson.evidence_data.hook_text && (
                        <span className="text-[11px] bg-slate-800 px-2 py-0.5 rounded text-slate-400 truncate max-w-md">
                          Hook: &ldquo;{lesson.evidence_data.hook_text}&rdquo;
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Proposed Adjustment Box */}
                <div className="bg-slate-950/40 border border-indigo-900/30 rounded-lg p-3.5 space-y-2">
                  <div className="text-xs font-semibold text-indigo-400 flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" />
                      {t("feedbackPage.card.proposedAdjTitle")}
                    </span>
                    <span className="font-mono text-[10px] bg-indigo-950/70 border border-indigo-800/50 px-2 py-0.5 rounded text-indigo-300">
                      {adj.target} • {adj.field} ({adj.action})
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 font-medium">
                    {adj.summary}
                  </p>

                  <div className="bg-slate-900 rounded p-2.5 font-mono text-xs text-emerald-400 overflow-x-auto border border-slate-800">
                    {typeof adj.value === "object"
                      ? JSON.stringify(adj.value, null, 2)
                      : String(adj.value)}
                  </div>
                </div>

                {/* Action Section */}
                {isPending && (
                  <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    <input
                      type="text"
                      placeholder={t("feedbackPage.card.creatorNotesPlaceholder")}
                      value={creatorNotesMap[lesson.id] || ""}
                      onChange={(e) =>
                        setCreatorNotesMap({
                          ...creatorNotesMap,
                          [lesson.id]: e.target.value,
                        })
                      }
                      className="flex-1 bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleApprove(lesson.id)}
                        disabled={actionLoading === lesson.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-all shadow-sm disabled:opacity-50"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        {t("feedbackPage.card.approveBtn")}
                      </button>

                      <button
                        onClick={() => handleReject(lesson.id)}
                        disabled={actionLoading === lesson.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-400 text-xs font-medium border border-slate-700 transition-all disabled:opacity-50"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        {t("feedbackPage.card.rejectBtn")}
                      </button>
                    </div>
                  </div>
                )}

                {isApproved && (
                  <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="text-xs text-slate-400">
                      {lesson.creator_notes && (
                        <span>
                          <strong>Note:</strong> {lesson.creator_notes}
                        </span>
                      )}
                    </div>

                    <button
                      onClick={() => handleApply(lesson.id)}
                      disabled={actionLoading === lesson.id}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                    >
                      <Sparkles className="w-4 h-4 text-amber-300" />
                      {t("feedbackPage.card.applyBtn")}
                    </button>
                  </div>
                )}

                {isApplied && (
                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-emerald-400">
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4" />
                      {t("feedbackPage.card.appliedBadge")}
                    </span>
                    <span className="text-slate-500 font-mono text-[11px]">
                      {lesson.applied_at ? new Date(lesson.applied_at).toLocaleString() : ""}
                    </span>
                  </div>
                )}

                {isRejected && (
                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-rose-400">
                    <span className="flex items-center gap-1.5">
                      <XCircle className="w-4 h-4" />
                      {t("feedbackPage.card.rejectedBadge")}
                    </span>
                    {lesson.creator_notes && (
                      <span className="text-slate-400 text-xs italic truncate max-w-sm">
                        &ldquo;{lesson.creator_notes}&rdquo;
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Manual Lesson Modal */}
      {showManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-amber-400" />
                {t("feedbackPage.manualModal.title")}
              </h3>
              <button
                onClick={() => setShowManualModal(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateManual} className="space-y-3.5">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    {t("feedbackPage.manualModal.lessonType")}
                  </label>
                  <select
                    value={manualForm.lesson_type}
                    onChange={(e) =>
                      setManualForm({ ...manualForm, lesson_type: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                  >
                    <option value="hook_optimization">Hook Optimization</option>
                    <option value="banned_phrase_addition">Banned Phrase Addition</option>
                    <option value="preferred_vocabulary_addition">Preferred Vocabulary</option>
                    <option value="pacing_adjustment">Pacing & Retention</option>
                    <option value="topic_reinforcement">Topic Reinforcement</option>
                    <option value="cta_refinement">CTA Refinement</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    {t("feedbackPage.manualModal.impact")}
                  </label>
                  <select
                    value={manualForm.impact_level}
                    onChange={(e) =>
                      setManualForm({ ...manualForm, impact_level: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                  >
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  {t("feedbackPage.manualModal.lessonTitle")}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ban 'game-changer' from all opening hooks"
                  value={manualForm.title}
                  onChange={(e) =>
                    setManualForm({ ...manualForm, title: e.target.value })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  {t("feedbackPage.manualModal.observation")}
                </label>
                <textarea
                  rows={2}
                  required
                  placeholder="Audience feedback indicated that opening with this cliché sounds artificial..."
                  value={manualForm.observation}
                  onChange={(e) =>
                    setManualForm({ ...manualForm, observation: e.target.value })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    {t("feedbackPage.manualModal.target")}
                  </label>
                  <select
                    value={manualForm.target}
                    onChange={(e) =>
                      setManualForm({ ...manualForm, target: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                  >
                    <option value="brand_profile">Brand Profile</option>
                    <option value="brand_memory">Brand Memory</option>
                    <option value="brand_exemplar">Brand Exemplar</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    {t("feedbackPage.manualModal.field")}
                  </label>
                  <select
                    value={manualForm.field}
                    onChange={(e) =>
                      setManualForm({ ...manualForm, field: e.target.value })
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                  >
                    <option value="avoid_vocabulary">avoid_vocabulary</option>
                    <option value="banned_cliches">banned_cliches</option>
                    <option value="preferred_vocabulary">preferred_vocabulary</option>
                    <option value="cta_style">cta_style</option>
                    <option value="hook">hook (memory)</option>
                    <option value="topic">topic (memory)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  {t("feedbackPage.manualModal.value")}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. game-changer"
                  value={manualForm.value}
                  onChange={(e) =>
                    setManualForm({ ...manualForm, value: e.target.value })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowManualModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={manualSaving}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium disabled:opacity-50"
                >
                  {manualSaving
                    ? t("feedbackPage.manualModal.saving")
                    : t("feedbackPage.manualModal.submit")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Explanation Modal */}
      {explanation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Info className="w-5 h-5 text-indigo-400" />
                {explanation.title}
              </h3>
              <button
                onClick={() => setExplanation(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 font-semibold block mb-0.5">Observation:</span>
                <p className="text-slate-300">{explanation.observation}</p>
              </div>

              <div>
                <span className="text-slate-400 font-semibold block mb-0.5">Reasoning:</span>
                <p className="text-slate-300">{explanation.reasoning}</p>
              </div>

              <div className="grid grid-cols-2 gap-2 bg-slate-950 p-2.5 rounded border border-slate-800">
                <div>
                  <span className="text-slate-400 block text-[10px]">Data Source:</span>
                  <span className="text-white font-mono text-[11px]">{explanation.data_source}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">Rule Trigger:</span>
                  <span className="text-white font-mono text-[11px]">{explanation.rule_triggered}</span>
                </div>
              </div>

              <div className="bg-amber-500/10 border border-amber-500/20 rounded p-2.5 text-amber-300 text-[11px] flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 shrink-0" />
                Human Quality Gate: Explicit creator approval is required before applying this change.
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setExplanation(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
