"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  CheckSquare,
  Clock,
  DollarSign,
  ExternalLink,
  Film,
  FolderArchive,
  Headphones,
  HelpCircle,
  Layers,
  Mic,
  RefreshCw,
  Share2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Tag,
  Video,
  Wand2,
} from "lucide-react";
import {
  PublishableItemSummary,
  QualityDimension,
  QualityGateAudit,
  QualityGateSummary,
  approveFinalQualityGate,
  evaluateQualityGate,
  getQualityGateAudit,
  getQualityGateSummary,
  listPublishableItems,
} from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

const DIMENSION_ICONS: Record<string, any> = {
  evidence_quality: BookOpen,
  brand_fit: Sparkles,
  originality: Wand2,
  viewer_value: Film,
  niche_fit: Layers,
  repetition_intelligence: RefreshCw,
  asset_rights: ShieldCheck,
  media_qc: Headphones,
  estimated_cost: DollarSign,
};

export default function QualityGatePage() {
  const { t } = useLanguage();

  // State: Items & Summary
  const [items, setItems] = useState<PublishableItemSummary[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<string>("");
  const [summary, setSummary] = useState<QualityGateSummary | null>(null);

  // State: Audit Data
  const [audit, setAudit] = useState<QualityGateAudit | null>(null);
  const [loadingAudit, setLoadingAudit] = useState<boolean>(false);
  const [evaluating, setEvaluating] = useState<boolean>(false);

  // State: Approval Modal / Action
  const [approving, setApproving] = useState<boolean>(false);
  const [showOverrideModal, setShowOverrideModal] = useState<boolean>(false);
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [approvalSuccess, setApprovalSuccess] = useState<string | null>(null);

  // Load items and summary on mount
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [itemList, summaryData] = await Promise.all([
        listPublishableItems(),
        getQualityGateSummary(),
      ]);
      setItems(itemList);
      setSummary(summaryData);
      if (itemList.length > 0 && !selectedItemId) {
        setSelectedItemId(itemList[0].id);
      }
    } catch (e) {
      console.error("Failed to load initial quality gate data:", e);
    }
  };

  // Load audit when selected item changes
  useEffect(() => {
    if (selectedItemId) {
      loadAudit(selectedItemId);
    }
  }, [selectedItemId]);

  const loadAudit = async (itemId: string) => {
    try {
      setLoadingAudit(true);
      setApprovalSuccess(null);
      const data = await getQualityGateAudit(itemId);
      setAudit(data);
    } catch (e) {
      console.error("Failed to load quality gate audit:", e);
      setAudit(null);
    } finally {
      setLoadingAudit(false);
    }
  };

  // Force re-evaluation
  const handleReevaluate = async () => {
    if (!selectedItemId) return;
    try {
      setEvaluating(true);
      const data = await evaluateQualityGate(selectedItemId);
      setAudit(data);
      const sum = await getQualityGateSummary();
      setSummary(sum);
    } catch (e: any) {
      alert("Evaluation failed: " + (e.message || e));
    } finally {
      setEvaluating(false);
    }
  };

  // Approve Final Quality Gate
  const handleApproveFinal = async () => {
    if (!selectedItemId) return;
    if (audit?.status === "BLOCKED" && !overrideReason.trim()) {
      setShowOverrideModal(true);
      return;
    }

    try {
      setApproving(true);
      const res = await approveFinalQualityGate(selectedItemId, {
        approved_by: "Lead Creator",
        override_reason: overrideReason.trim() || undefined,
      });
      setApprovalSuccess(res.message);
      setShowOverrideModal(false);
      setOverrideReason("");

      // Refresh audit and summary
      await loadAudit(selectedItemId);
      const sum = await getQualityGateSummary();
      setSummary(sum);
    } catch (e: any) {
      alert("Approval failed: " + (e.message || e));
    } finally {
      setApproving(false);
    }
  };

  // Status Badge Helper
  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "FINAL_APPROVED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {t("qualityGatePage.statusApproved", "Final Approved")}
          </span>
        );
      case "PASSED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {t("qualityGatePage.statusPassed", "Passed")}
          </span>
        );
      case "WARNING":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            {t("qualityGatePage.statusWarning", "Warning")}
          </span>
        );
      case "BLOCKED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <ShieldAlert className="w-3.5 h-3.5" />
            {t("qualityGatePage.statusBlocked", "Blocked")}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {t("qualityGatePage.statusPending", "Pending Review")}
          </span>
        );
    }
  };

  // Score Badge Helper
  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-emerald-400";
    if (score >= 65) return "text-amber-400";
    return "text-rose-400";
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-emerald-500/20">
              <CheckSquare className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                {t("qualityGatePage.title", "Final Creator Quality Gate")}
                <span className="text-xs font-medium px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Phase 17
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                {t("qualityGatePage.subtitle", "Comprehensive 9-dimension verification audit required before unlocking export packages")}
              </p>
            </div>
          </div>
        </div>

        {/* Global Summary Badge */}
        {summary && (
          <div className="flex items-center gap-4 bg-slate-900/80 border border-slate-800 px-4 py-2 rounded-xl text-xs">
            <div>
              <span className="text-slate-500 block">Total Items</span>
              <span className="font-semibold text-slate-200">{summary.total_items}</span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-slate-500 block">Final Approved</span>
              <span className="font-semibold text-emerald-400">{summary.final_approved_count}</span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-slate-500 block">Approval Rate</span>
              <span className="font-semibold text-indigo-400">{summary.approval_rate_percent}%</span>
            </div>
          </div>
        )}
      </div>

      {/* Item Selector & Action Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm backdrop-blur-sm">
        <div className="flex-1 max-w-xl">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            {t("qualityGatePage.itemSelector", "Select Content Item")}
          </label>
          <select
            value={selectedItemId}
            onChange={(e) => setSelectedItemId(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all"
          >
            <option value="" disabled>
              {t("qualityGatePage.selectPlaceholder", "-- Choose a content item for quality gate audit --")}
            </option>
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.working_title || item.family_title || "Untitled"} ({item.platform_target || item.format || "Script"})
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleReevaluate}
            disabled={evaluating || !selectedItemId}
            className="px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${evaluating ? "animate-spin" : ""}`} />
            {evaluating ? t("qualityGatePage.evaluating", "Evaluating...") : t("qualityGatePage.evaluateBtn", "Re-Evaluate Gate")}
          </button>

          <button
            onClick={handleApproveFinal}
            disabled={approving || !selectedItemId || audit?.is_approved}
            className={`px-5 py-2.5 rounded-lg text-xs font-bold flex items-center gap-2 shadow-md transition-all ${
              audit?.is_approved
                ? "bg-emerald-950/60 text-emerald-400 border border-emerald-500/40 cursor-default"
                : audit?.status === "BLOCKED"
                ? "bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/20"
                : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20"
            } disabled:opacity-50`}
          >
            {approving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                {t("qualityGatePage.approving", "Approving...")}
              </>
            ) : audit?.is_approved ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                {t("qualityGatePage.statusApproved", "Final Approved")}
              </>
            ) : (
              <>
                <CheckSquare className="w-4 h-4" />
                {t("qualityGatePage.approveBtn", "Approve Final")}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Approval Success Banner */}
      {approvalSuccess && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-sm flex items-center justify-between shadow-lg shadow-emerald-950/20 animate-in fade-in duration-300">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <div className="font-semibold">{t("qualityGatePage.approvedSuccess", "Final Creator Quality Gate cleared! Export package generation is unlocked.")}</div>
              <div className="text-xs text-emerald-400/80 mt-0.5">{approvalSuccess}</div>
            </div>
          </div>
          <Link
            href={`/publishing/${selectedItemId}`}
            className="px-3.5 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold text-xs flex items-center gap-1.5 hover:bg-emerald-400 transition-colors shrink-0"
          >
            <span>Proceed to Export</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {!audit && !loadingAudit && (
        <div className="p-12 text-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30">
          <FolderArchive className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">
            {t("qualityGatePage.noItemSelected", "No content item selected.")}
          </h3>
          <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
            Please choose a content item from the dropdown above to inspect the 9 creator quality dimensions.
          </p>
        </div>
      )}

      {audit && (
        <div className="space-y-8">
          {/* Readiness Score Card */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 border border-slate-800 shadow-xl backdrop-blur-md flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              <div className="relative w-20 h-20 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-center shrink-0 shadow-inner">
                <span className={`text-2xl font-black font-mono ${getScoreColor(audit.overall_score)}`}>
                  {audit.overall_score}%
                </span>
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-bold text-white tracking-tight">
                    {audit.item_title}
                  </h2>
                  {getStatusBadge(audit.status)}
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Format: <span className="font-semibold text-slate-300">{audit.format}</span> • Target Platform:{" "}
                  <span className="font-semibold text-slate-300">{audit.platform_target}</span>
                  {audit.approved_by && (
                    <span> • Approved by <span className="text-emerald-400 font-semibold">{audit.approved_by}</span></span>
                  )}
                </p>
              </div>
            </div>

            {/* Quick Action Navigation Buttons */}
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href={`/script-studio/${selectedItemId}`}
                className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-colors"
                title="Return to script studio"
              >
                <span>Script Studio</span>
                <ExternalLink className="w-3 h-3 text-slate-400" />
              </Link>
              <Link
                href={`/scene-studio?itemId=${selectedItemId}`}
                className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-colors"
                title="Return to scene studio"
              >
                <span>Scene Studio</span>
                <ExternalLink className="w-3 h-3 text-slate-400" />
              </Link>
              <Link
                href="/media-studio"
                className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-colors"
                title="Return to media studio"
              >
                <span>Media Studio</span>
                <ExternalLink className="w-3 h-3 text-slate-400" />
              </Link>
              <Link
                href="/evidence"
                className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-colors"
                title="View evidence provenance"
              >
                <span>Evidence</span>
                <ExternalLink className="w-3 h-3 text-slate-400" />
              </Link>
              <Link
                href="/asset-rights"
                className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs font-semibold text-slate-300 flex items-center gap-1.5 transition-colors"
                title="Check asset rights registry"
              >
                <span>Asset Rights</span>
                <ExternalLink className="w-3 h-3 text-slate-400" />
              </Link>
            </div>
          </div>

          {/* Actionable Recommendations Banner (if any) */}
          {audit.recommendations && audit.recommendations.length > 0 && (
            <div className="p-5 rounded-xl bg-slate-900/60 border border-amber-500/30 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-wider">
                <AlertTriangle className="w-4 h-4" />
                <span>{t("qualityGatePage.quickActions", "Actionable Corrections & Direct Routing")} ({audit.recommendations.length})</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {audit.recommendations.map((rec, ridx) => (
                  <Link
                    key={ridx}
                    href={rec.target_route}
                    className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 hover:border-amber-500/50 flex items-center justify-between group transition-all"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-200 group-hover:text-amber-300 transition-colors">
                        {rec.title}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        {rec.description}
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-amber-400 transition-colors shrink-0 ml-3" />
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* THE 9 CREATOR QUALITY DIMENSIONS */}
          {/* ========================================================================= */}
          <div className="space-y-4">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <span>{t("qualityGatePage.dimensionsTitle", "9 Creator Quality Dimensions")}</span>
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {audit.dimensions.map((dim) => {
                const IconComponent = DIMENSION_ICONS[dim.id] || HelpCircle;
                const isBlocked = dim.status === "BLOCKED";
                const isWarning = dim.status === "WARNING";

                return (
                  <div
                    key={dim.id}
                    className={`rounded-xl p-5 border flex flex-col justify-between transition-all ${
                      isBlocked
                        ? "bg-rose-950/20 border-rose-500/40"
                        : isWarning
                        ? "bg-amber-950/15 border-amber-500/40"
                        : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <div
                            className={`p-2 rounded-lg border ${
                              isBlocked
                                ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                : isWarning
                                ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            }`}
                          >
                            <IconComponent className="w-4 h-4" />
                          </div>
                          <div>
                            <h3 className="text-xs font-bold text-white leading-tight">
                              {dim.name}
                            </h3>
                            <div className="text-[10px] font-mono text-slate-500">
                              {dim.id}
                            </div>
                          </div>
                        </div>

                        <span className={`text-sm font-bold font-mono ${getScoreColor(dim.score)}`}>
                          {Math.round(dim.score)}%
                        </span>
                      </div>

                      <p className="text-xs text-slate-300 font-medium leading-relaxed">
                        {dim.summary}
                      </p>

                      {dim.details && dim.details.length > 0 && (
                        <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
                          {dim.details.map((detail, didx) => (
                            <div
                              key={didx}
                              className="text-[11px] text-slate-400 flex items-start gap-1.5"
                            >
                              <span className="text-slate-600 shrink-0">•</span>
                              <span>{detail}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                      <span className="text-slate-500">Status</span>
                      <span
                        className={`font-semibold uppercase tracking-wider text-[10px] px-2 py-0.5 rounded ${
                          isBlocked
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : isWarning
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        }`}
                      >
                        {dim.status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Override Reason Modal (when blocked) */}
      {showOverrideModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-slate-900 border border-amber-500/40 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-base font-bold text-white">
                Quality Gate Override Required
              </h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {t(
                "qualityGatePage.overridePrompt",
                "Blocking issues detected. Provide an explicit override reason explaining why this item meets creator quality standards despite warnings:"
              )}
            </p>

            <textarea
              rows={4}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder={t(
                "qualityGatePage.overridePlaceholder",
                "Explain why this item meets creator quality standards despite warnings..."
              )}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
            />

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowOverrideModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 text-xs font-semibold transition-colors"
              >
                {t("common.cancel", "Cancel")}
              </button>
              <button
                onClick={handleApproveFinal}
                disabled={!overrideReason.trim() || approving}
                className="px-5 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold shadow-md shadow-amber-600/20 disabled:opacity-50 transition-colors"
              >
                {approving ? t("qualityGatePage.approving", "Approving...") : "Confirm & Approve Final"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
