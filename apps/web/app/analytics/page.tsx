"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart3,
  TrendingUp,
  Eye,
  DollarSign,
  Zap,
  Plus,
  FileSpreadsheet,
  Play,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  Layers,
  ArrowUpRight,
  Filter,
} from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import {
  AnalyticsSummaryReport,
  HookPerformanceInsight,
  SnapshotResponse,
  PublishableItemSummary,
  getAnalyticsSummary,
  getHookRankings,
  listSnapshots,
  recordSnapshot,
  deleteSnapshot,
  importCSVSnapshots,
  runAnalyticsEngine,
  listPublishableItems,
  SnapshotCreatePayload,
} from "@/lib/api";

export default function AnalyticsPage() {
  const { t } = useLanguage();

  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<AnalyticsSummaryReport | null>(null);
  const [hooks, setHooks] = useState<HookPerformanceInsight[]>([]);
  const [snapshots, setSnapshots] = useState<SnapshotResponse[]>([]);
  const [items, setItems] = useState<PublishableItemSummary[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");

  // Modals
  const [showLogModal, setShowLogModal] = useState(false);
  const [showCsvModal, setShowCsvModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [runningEngine, setRunningEngine] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New Snapshot Form State
  const [formData, setFormData] = useState<SnapshotCreatePayload>({
    content_item_id: "",
    platform: "youtube",
    snapshot_label: "24h",
    views: 1000,
    impressions: 5000,
    watch_time_seconds: 3600,
    average_view_duration_seconds: 45,
    retention_rate_pct: 65.0,
    hook_retention_3s_pct: 72.0,
    hook_retention_30s_pct: 48.0,
    likes: 60,
    comments: 12,
    shares: 8,
    saves: 15,
    clicks: 25,
    subscribers_gained: 10,
    revenue_estimated_usd: 15.0,
    notes: "",
  });

  // CSV State
  const [csvText, setCsvText] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [sumRes, hooksRes, snapsRes, itemsRes] = await Promise.all([
        getAnalyticsSummary(30),
        getHookRankings(20),
        listSnapshots(undefined, selectedPlatform === "all" ? undefined : selectedPlatform, 100),
        listPublishableItems(),
      ]);
      setSummary(sumRes);
      setHooks(hooksRes);
      setSnapshots(snapsRes);
      setItems(itemsRes);

      // Default item if none selected
      if (!formData.content_item_id && itemsRes.length > 0) {
        setFormData((prev) => ({ ...prev, content_item_id: itemsRes[0].id }));
      }
    } catch (err: any) {
      console.error("Error loading analytics data:", err);
      setFeedbackMessage({ type: "error", text: err.message || "Failed to load analytics" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedPlatform]);

  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.content_item_id) {
      alert("Please select a content item.");
      return;
    }
    setSubmitting(true);
    try {
      await recordSnapshot(formData);
      setFeedbackMessage({ type: "success", text: "Metrics snapshot logged successfully!" });
      setShowLogModal(false);
      await loadData();
    } catch (err: any) {
      setFeedbackMessage({ type: "error", text: err.message || "Failed to log snapshot" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleImportCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvText.trim()) return;
    setSubmitting(true);
    try {
      const res = await importCSVSnapshots(csvText);
      setFeedbackMessage({
        type: "success",
        text: `CSV imported: ${res.imported_count} snapshots created (${res.failed_count} failed).`,
      });
      setShowCsvModal(false);
      setCsvText("");
      await loadData();
    } catch (err: any) {
      setFeedbackMessage({ type: "error", text: err.message || "CSV import failed" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSnapshot = async (id: string) => {
    if (!confirm(t("analyticsPage.deleteConfirm", "Are you sure you want to delete this snapshot?"))) return;
    try {
      await deleteSnapshot(id);
      setSnapshots((prev) => prev.filter((s) => s.id !== id));
      setFeedbackMessage({ type: "success", text: "Snapshot deleted." });
      const sumRes = await getAnalyticsSummary(30);
      setSummary(sumRes);
    } catch (err: any) {
      setFeedbackMessage({ type: "error", text: err.message || "Delete failed" });
    }
  };

  const handleRunEngine = async () => {
    setRunningEngine(true);
    try {
      await runAnalyticsEngine();
      setFeedbackMessage({ type: "success", text: "Analytics Engine executed successfully!" });
      await loadData();
    } catch (err: any) {
      setFeedbackMessage({ type: "error", text: err.message || "Engine run failed" });
    } finally {
      setRunningEngine(false);
    }
  };

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case "VIRAL":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">🔥 {t("analyticsPage.verdicts.viral", "Viral Hook")}</span>;
      case "STRONG":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">⚡ {t("analyticsPage.verdicts.strong", "Strong Hold")}</span>;
      case "ACCEPTABLE":
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">✓ {t("analyticsPage.verdicts.acceptable", "Acceptable")}</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">⚠️ {t("analyticsPage.verdicts.criticalDrop", "Critical Dropoff")}</span>;
    }
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case "youtube":
        return <span className="text-red-400 font-bold text-xs uppercase bg-red-950/60 px-2 py-0.5 rounded border border-red-800/40">YouTube</span>;
      case "tiktok":
        return <span className="text-pink-400 font-bold text-xs uppercase bg-pink-950/60 px-2 py-0.5 rounded border border-pink-800/40">TikTok</span>;
      case "facebook":
        return <span className="text-blue-400 font-bold text-xs uppercase bg-blue-950/60 px-2 py-0.5 rounded border border-blue-800/40">Facebook</span>;
      case "instagram":
        return <span className="text-purple-400 font-bold text-xs uppercase bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/40">Instagram</span>;
      default:
        return <span className="text-slate-400 font-bold text-xs uppercase bg-slate-800 px-2 py-0.5 rounded border border-slate-700">{platform}</span>;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Header & Main Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                {t("analyticsPage.title", "Creator Business Analytics")}
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                {t("analyticsPage.subtitle", "Manual publication metrics tracking, 3-second hook retention benchmarks, and creator ROI economics")}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={() => setShowLogModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-md shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" />
            {t("analyticsPage.logSnapshotBtn", "Log Metrics Snapshot")}
          </button>

          <button
            onClick={() => setShowCsvModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-sm transition-all"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            {t("analyticsPage.importCsvBtn", "Import CSV")}
          </button>

          <button
            onClick={handleRunEngine}
            disabled={runningEngine}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-sm transition-all disabled:opacity-50"
          >
            <Play className="w-4 h-4 text-amber-400" />
            {runningEngine ? "..." : t("analyticsPage.runEngineBtn", "Run Analytics Engine")}
          </button>
        </div>
      </div>

      {/* Feedback Banner */}
      {feedbackMessage && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between border ${
            feedbackMessage.type === "success"
              ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-200"
              : "bg-rose-950/40 border-rose-500/30 text-rose-200"
          }`}
        >
          <div className="flex items-center gap-2.5 text-sm">
            {feedbackMessage.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            )}
            <span>{feedbackMessage.text}</span>
          </div>
          <button
            onClick={() => setFeedbackMessage(null)}
            className="text-xs opacity-75 hover:opacity-100 uppercase font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Executive KPIs Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">{t("analyticsPage.totalViews", "Total Views")}</span>
            <Eye className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {summary ? summary.total_views.toLocaleString() : "0"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Across all published items</p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">{t("analyticsPage.totalEngagements", "Avg Engagement")}</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 tracking-tight">
            {summary ? `${summary.overall_engagement_rate_pct}%` : "0%"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Likes, comments, shares</p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">{t("analyticsPage.avgHookRetention", "Avg 3s Hold")}</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 tracking-tight">
            {summary ? `${summary.avg_3s_hook_retention_pct}%` : "0%"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Benchmark: &gt;70% strong</p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">{t("analyticsPage.totalRevenue", "Total Revenue")}</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            ${summary ? summary.total_revenue_usd.toFixed(2) : "0.00"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Direct & affiliate earnings</p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl relative overflow-hidden col-span-2 md:col-span-1">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">{t("analyticsPage.overallRoi", "Production ROI")}</span>
            <Sparkles className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-indigo-400 tracking-tight">
            {summary ? `${summary.overall_roi_multiplier}x` : "0.0x"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Return on creation labor</p>
        </div>
      </div>

      {/* Platform Breakdown Cards */}
      {summary && summary.platforms.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              Platform Distribution & Economics
            </h3>
            <div className="flex items-center gap-1.5">
              {["all", "youtube", "tiktok", "facebook", "instagram"].map((p) => (
                <button
                  key={p}
                  onClick={() => setSelectedPlatform(p)}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                    selectedPlatform === p
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "bg-slate-800/80 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {p === "all" ? t("analyticsPage.filterAll", "All Platforms") : p.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {summary.platforms.map((plat) => (
              <div
                key={plat.platform}
                className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl space-y-2 hover:border-slate-700 transition-all"
              >
                <div className="flex items-center justify-between">
                  {getPlatformIcon(plat.platform)}
                  <span className="text-xs text-slate-400">{plat.total_posts} snapshots</span>
                </div>
                <div className="text-xl font-bold text-white">
                  {plat.total_views.toLocaleString()} <span className="text-xs font-normal text-slate-400">views</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800/60 text-slate-400">
                  <div>
                    <span className="block text-[10px] text-slate-500">ENGAGEMENT</span>
                    <span className="font-semibold text-slate-200">{plat.avg_engagement_rate}%</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-slate-500">REVENUE</span>
                    <span className="font-semibold text-emerald-400">${plat.total_revenue.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3-Second Hook Retention Benchmark Studio */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              {t("analyticsPage.hookAnalysisTitle", "Hook Performance & Retention Rankings")}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t("analyticsPage.hookAnalysisSubtitle", "Benchmarking script opening hold rates against creator velocity standards")}
            </p>
          </div>
          <span className="text-xs text-slate-500">Ranked by 3s retention hold</span>
        </div>

        {hooks.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">
            {t("analyticsPage.noHooks", "No snapshots with 3-second hook retention data found yet.")}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[650px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-xs font-medium uppercase tracking-wider">
                  <th className="pb-3 px-3">{t("analyticsPage.hookTable.hook", "Script Opening Hook")}</th>
                  <th className="pb-3 px-3">{t("analyticsPage.hookTable.platform", "Platform")}</th>
                  <th className="pb-3 px-3">{t("analyticsPage.hookTable.views", "Views")}</th>
                  <th className="pb-3 px-3">{t("analyticsPage.hookTable.retention3s", "3s Hold")}</th>
                  <th className="pb-3 px-3">{t("analyticsPage.hookTable.verdict", "Verdict")}</th>
                  <th className="pb-3 px-3">{t("analyticsPage.hookTable.recommendation", "Recommendation")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {hooks.map((h, i) => (
                  <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 font-medium text-white max-w-xs truncate" title={h.hook_text}>
                      <span className="text-slate-400 text-xs block truncate">{h.content_title}</span>
                      &ldquo;{h.hook_text}&rdquo;
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">{getPlatformIcon(h.platform)}</td>
                    <td className="py-3 px-3 text-slate-300 font-mono">{h.views.toLocaleString()}</td>
                    <td className="py-3 px-3 font-mono font-semibold">
                      <span className={h.hook_retention_3s_pct >= 70 ? "text-emerald-400" : h.hook_retention_3s_pct >= 55 ? "text-amber-400" : "text-rose-400"}>
                        {h.hook_retention_3s_pct}%
                      </span>
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">{getVerdictBadge(h.verdict)}</td>
                    <td className="py-3 px-3 text-xs text-slate-400 max-w-sm">{h.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Snapshots Timeline & Logged History */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              {t("analyticsPage.timelineTitle", "Publication Performance Snapshots Timeline")}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {t("analyticsPage.timelineSubtitle", "Historical performance snapshots across target social platforms")}
            </p>
          </div>
          <span className="text-xs text-slate-400 font-mono">{snapshots.length} records</span>
        </div>

        {snapshots.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">
            {t("analyticsPage.noSnapshots", "No publication snapshots found. Log your first snapshot or import metrics from a CSV file.")}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[750px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-xs font-medium uppercase tracking-wider">
                  <th className="pb-3 px-3">Date</th>
                  <th className="pb-3 px-3">Platform</th>
                  <th className="pb-3 px-3">Label</th>
                  <th className="pb-3 px-3">Views</th>
                  <th className="pb-3 px-3">Likes</th>
                  <th className="pb-3 px-3">Comments</th>
                  <th className="pb-3 px-3">Shares</th>
                  <th className="pb-3 px-3">Engagement</th>
                  <th className="pb-3 px-3">Revenue</th>
                  <th className="pb-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {snapshots.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-3 text-xs text-slate-400 whitespace-nowrap">
                      {new Date(s.snapshot_timestamp).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">{getPlatformIcon(s.platform)}</td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-xs font-mono text-indigo-300 border border-slate-700">
                        {s.snapshot_label}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono font-medium text-white">{s.views.toLocaleString()}</td>
                    <td className="py-3 px-3 font-mono text-slate-300">{s.likes.toLocaleString()}</td>
                    <td className="py-3 px-3 font-mono text-slate-300">{s.comments.toLocaleString()}</td>
                    <td className="py-3 px-3 font-mono text-slate-300">{s.shares.toLocaleString()}</td>
                    <td className="py-3 px-3 font-mono text-emerald-400 font-semibold">{s.engagement_rate_pct}%</td>
                    <td className="py-3 px-3 font-mono text-white">${s.revenue_estimated_usd.toFixed(2)}</td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => handleDeleteSnapshot(s.id)}
                        className="p-1.5 rounded hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors"
                        title="Delete snapshot"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal: Log Manual Snapshot */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 space-y-5 my-8 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" />
                {t("analyticsPage.logModal.title", "Log Manual Publication Metrics Snapshot")}
              </h3>
              <button
                onClick={() => setShowLogModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSnapshot} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                  {t("analyticsPage.logModal.selectItem", "Select Content Item")} *
                </label>
                <select
                  value={formData.content_item_id}
                  onChange={(e) => setFormData({ ...formData, content_item_id: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  required
                >
                  <option value="">-- Choose content item --</option>
                  {items.map((it) => (
                    <option key={it.id} value={it.id}>
                      [{it.platform_target.toUpperCase()}] {it.working_title} ({it.family_title})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    {t("analyticsPage.logModal.platform", "Platform")} *
                  </label>
                  <select
                    value={formData.platform}
                    onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="youtube">YouTube</option>
                    <option value="tiktok">TikTok</option>
                    <option value="facebook">Facebook</option>
                    <option value="instagram">Instagram</option>
                    <option value="blog">Blog</option>
                    <option value="newsletter">Newsletter</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    {t("analyticsPage.logModal.label", "Snapshot Label")} *
                  </label>
                  <select
                    value={formData.snapshot_label}
                    onChange={(e) => setFormData({ ...formData, snapshot_label: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="24h">24h (First Day)</option>
                    <option value="48h">48h (Momentum)</option>
                    <option value="7d">7d (One Week)</option>
                    <option value="14d">14d (Two Weeks)</option>
                    <option value="30d">30d (Month 1)</option>
                    <option value="90d">90d (Quarterly)</option>
                    <option value="lifetime">Lifetime</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    {t("analyticsPage.logModal.views", "Views")}
                  </label>
                  <input
                    type="number"
                    value={formData.views}
                    onChange={(e) => setFormData({ ...formData, views: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    {t("analyticsPage.logModal.impressions", "Impressions")}
                  </label>
                  <input
                    type="number"
                    value={formData.impressions}
                    onChange={(e) => setFormData({ ...formData, impressions: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    {t("analyticsPage.logModal.revenue", "Revenue ($)")}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.revenue_estimated_usd}
                    onChange={(e) => setFormData({ ...formData, revenue_estimated_usd: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    {t("analyticsPage.logModal.hook3s", "3s Hook Hold (%)")}
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.hook_retention_3s_pct || 0}
                    onChange={(e) => setFormData({ ...formData, hook_retention_3s_pct: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    {t("analyticsPage.logModal.hook30s", "30s Hold (%)")}
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.hook_retention_30s_pct || 0}
                    onChange={(e) => setFormData({ ...formData, hook_retention_30s_pct: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                    {t("analyticsPage.logModal.retentionRate", "Overall Retention (%)")}
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.retention_rate_pct}
                    onChange={(e) => setFormData({ ...formData, retention_rate_pct: parseFloat(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-4 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Likes</label>
                  <input
                    type="number"
                    value={formData.likes}
                    onChange={(e) => setFormData({ ...formData, likes: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Comments</label>
                  <input
                    type="number"
                    value={formData.comments}
                    onChange={(e) => setFormData({ ...formData, comments: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Shares</label>
                  <input
                    type="number"
                    value={formData.shares}
                    onChange={(e) => setFormData({ ...formData, shares: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Saves</label>
                  <input
                    type="number"
                    value={formData.saves}
                    onChange={(e) => setFormData({ ...formData, saves: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">
                  {t("analyticsPage.logModal.notes", "Notes")}
                </label>
                <textarea
                  value={formData.notes || ""}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="e.g. Algorithmic spike at hour 14, pinned comment driving conversions..."
                  rows={2}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50"
                >
                  {submitting ? t("analyticsPage.logModal.saving", "Saving...") : t("analyticsPage.logModal.submit", "Save Snapshot")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: CSV Import */}
      {showCsvModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
                {t("analyticsPage.csvModal.title", "Import Metrics from CSV File")}
              </h3>
              <button
                onClick={() => setShowCsvModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              {t("analyticsPage.csvModal.desc", "Supported columns: content_item_id, platform, snapshot_label, views, likes, comments, shares, revenue_estimated_usd, hook_retention_3s_pct")}
            </p>

            <form onSubmit={handleImportCsv} className="space-y-4">
              <textarea
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                placeholder={t("analyticsPage.csvModal.placeholder", "content_item_id,platform,snapshot_label,views,likes,comments,shares,revenue_estimated_usd,hook_retention_3s_pct\n...")}
                rows={10}
                className="w-full bg-slate-950 font-mono text-xs border border-slate-800 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-indigo-500"
                required
              />

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCsvModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-all shadow-md shadow-emerald-600/20 disabled:opacity-50"
                >
                  {submitting ? t("analyticsPage.csvModal.importing", "Importing...") : t("analyticsPage.csvModal.submit", "Import CSV Records")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
