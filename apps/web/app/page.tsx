"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Compass,
  Sparkles,
  DollarSign,
  HardDrive,
  Activity,
  CheckCircle2,
  XCircle,
  Eye,
  ArrowRight,
  Flame,
  TrendingUp,
  Rss,
  RefreshCw,
  Boxes,
} from "lucide-react";
import {
  CockpitSummary,
  StudioStatus,
  ContentFamilyDetail,
  ContentFamilyItem,
  getCockpitSummary,
  getStudioStatus,
  getContentFamily,
  listContentFamilies,
  approveOpportunityResearch,
  watchOpportunity,
  rejectOpportunity,
  runOpportunities,
} from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";
import { CreatorWorkflow } from "@/components/CreatorWorkflow";

export default function CreatorCockpitPage() {
  const { t } = useLanguage();
  const [summary, setSummary] = useState<CockpitSummary | null>(null);
  const [studioStatus, setStudioStatus] = useState<StudioStatus | null>(null);
  const [families, setFamilies] = useState<ContentFamilyItem[]>([]);
  const [currentFamily, setCurrentFamily] = useState<ContentFamilyDetail | null>(null);
  const [workflowLoadError, setWorkflowLoadError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<{ type: "success" | "info" | "error"; text: string } | null>(null);

  const fetchCockpitData = async () => {
    try {
      setLoading(true);
      setWorkflowLoadError(false);
      const [sumData, statusData, familiesData] = await Promise.all([
        getCockpitSummary(),
        getStudioStatus(),
        listContentFamilies({ limit: 50 }).catch(() => {
          setWorkflowLoadError(true);
          return [] as ContentFamilyItem[];
        }),
      ]);
      setSummary(sumData);
      setStudioStatus(statusData);
      setFamilies(familiesData);

      const activeFamily = familiesData.find(
        (family) => family.status !== "COMPLETED" && family.status !== "ARCHIVED"
      );
      if (activeFamily) {
        try {
          setCurrentFamily(await getContentFamily(activeFamily.id));
        } catch {
          setCurrentFamily(null);
          setWorkflowLoadError(true);
        }
      } else {
        setCurrentFamily(null);
      }
    } catch (e: any) {
      console.error("Cockpit load error:", e);
      setCurrentFamily(null);
      setWorkflowLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  const activeFamiliesCount = families.filter(
    (f) => f.status === "ACTIVE" || f.status === "READY_FOR_CONTENT"
  ).length;

  const plannedItemsCount = families.reduce(
    (acc, f) => acc + (f.item_count || 0),
    0
  );

  useEffect(() => {
    fetchCockpitData();
  }, []);

  const handleApprove = async (oppId: string, topicName: string) => {
    try {
      await approveOpportunityResearch(oppId);
      setActionFeedback({
        type: "success",
        text: `"${topicName}" — ${t("cockpit.approvedFeedback", "Approved for Research. Status is now Research Ready.")}`,
      });
      await fetchCockpitData();
    } catch (err: any) {
      setActionFeedback({
        type: "error",
        text: `${t("cockpit.failedApprove", "Failed to approve opportunity:")} ${err.message}`,
      });
    }
  };

  const handleWatch = async (oppId: string, topicName: string) => {
    try {
      await watchOpportunity(oppId);
      setActionFeedback({
        type: "info",
        text: `"${topicName}" — ${t("cockpit.watchedFeedback", "Moved to Watch list. Monitoring trend momentum.")}`,
      });
      await fetchCockpitData();
    } catch (err: any) {
      setActionFeedback({
        type: "error",
        text: `${t("cockpit.failedWatch", "Failed to watch opportunity:")} ${err.message}`,
      });
    }
  };

  const handleReject = async (oppId: string, topicName: string) => {
    try {
      await rejectOpportunity(oppId, "Dismissed from Cockpit");
      setActionFeedback({
        type: "info",
        text: `"${topicName}" — ${t("cockpit.rejectedFeedback", "Rejected topic. Removed from review queue.")}`,
      });
      await fetchCockpitData();
    } catch (err: any) {
      setActionFeedback({
        type: "error",
        text: `${t("cockpit.failedReject", "Failed to reject opportunity:")} ${err.message}`,
      });
    }
  };

  const handleRunOpportunityAnalysis = async () => {
    try {
      setRunningAnalysis(true);
      setActionFeedback({
        type: "info",
        text: t("cockpit.evaluatingSignals", "Evaluating fresh signals against Niche Guard and Brand memory..."),
      });
      const res = await runOpportunities();
      setActionFeedback({
        type: "success",
        text: res.summary || t("cockpit.analysisCompleted", "Opportunity intelligence analysis completed!"),
      });
      await fetchCockpitData();
    } catch (err: any) {
      setActionFeedback({
        type: "error",
        text: `${t("cockpit.analysisFailed", "Analysis failed:")} ${err.message}`,
      });
    } finally {
      setRunningAnalysis(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-12">
      {/* Cockpit Executive Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
                {t("cockpit.title", "Creator Cockpit")}
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {t("cockpit.humanQualityGate", "Human Quality Gate")}
                </span>
              </h1>
              <p className="text-sm text-zinc-400 mt-1">
                {t("cockpit.singleNiche", "Single Niche:")} <span className="text-zinc-200 font-medium">{studioStatus?.active_niche_name || t("common.configuring", "Configuring...")}</span>
                <span className="mx-2 text-zinc-600">|</span>
                {t("cockpit.singleBrand", "Single Brand:")} <span className="text-zinc-200 font-medium">{studioStatus?.active_brand_name || t("common.configuring", "Configuring...")}</span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <Link
            href="/sources"
            className="px-3.5 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium border border-zinc-700 transition flex items-center gap-2"
          >
            <Rss className="w-4 h-4 text-zinc-400" />
            {t("cockpit.sourcesBtn", "Sources")}
          </Link>
          <Link
            href="/trends"
            className="px-3.5 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium border border-zinc-700 transition flex items-center gap-2"
          >
            <TrendingUp className="w-4 h-4 text-rose-400" />
            {t("cockpit.trendsBtn", "Trends")}
          </Link>
          <button
            onClick={handleRunOpportunityAnalysis}
            disabled={runningAnalysis}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-indigo-600/20 flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${runningAnalysis ? "animate-spin" : ""}`} />
            {runningAnalysis ? t("cockpit.runningAnalysis", "Running Analysis...") : t("cockpit.evaluateBtn", "Evaluate Opportunities")}
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionFeedback && (
        <div
          className={`p-4 rounded-xl text-sm flex items-start justify-between border ${
            actionFeedback.type === "success"
              ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
              : actionFeedback.type === "error"
              ? "bg-rose-950/40 border-rose-500/30 text-rose-300"
              : "bg-blue-950/40 border-blue-500/30 text-blue-300"
          }`}
        >
          <span>{actionFeedback.text}</span>
          <button
            onClick={() => setActionFeedback(null)}
            className="text-xs hover:underline opacity-80"
          >
            {t("common.dismiss", "Dismiss")}
          </button>
        </div>
      )}

      <CreatorWorkflow
        summary={summary}
        studioStatus={studioStatus}
        activeFamiliesCount={activeFamiliesCount}
        currentFamily={currentFamily}
        workflowLoadError={workflowLoadError}
        loading={loading}
      />

      {/* Decision Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {/* Signals Today */}
        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
          <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
            {t("cockpit.signalsToday", "Signals Today")}
          </span>
          <div className="mt-2 text-2xl font-bold text-white">
            {summary?.signals_today ?? 0}
          </div>
        </div>

        {/* Needs Review */}
        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30">
          <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider block">
            {t("cockpit.needsReview", "Needs Review")}
          </span>
          <div className="mt-2 text-2xl font-bold text-amber-400">
            {summary?.needs_review ?? 0}
          </div>
        </div>

        {/* Research Ready */}
        <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/30">
          <span className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider block">
            {t("cockpit.researchReady", "Research Ready")}
          </span>
          <div className="mt-2 text-2xl font-bold text-indigo-400">
            {summary?.research_ready ?? 0}
          </div>
        </div>

        {/* In Production */}
        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
          <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
            {t("cockpit.inProduction", "In Production")}
          </span>
          <div className="mt-2 text-2xl font-bold text-sky-400">
            {summary?.in_production ?? 0}
          </div>
        </div>

        {/* Ready to Publish */}
        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
          <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block">
            {t("cockpit.readyToPublish", "Ready to Publish")}
          </span>
          <div className="mt-2 text-2xl font-bold text-emerald-400">
            {summary?.ready_to_publish ?? 0}
          </div>
        </div>

        {/* Published */}
        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
          <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block">
            {t("cockpit.published", "Published")}
          </span>
          <div className="mt-2 text-2xl font-bold text-zinc-300">
            {summary?.published ?? 0}
          </div>
        </div>

        {/* AI Spend */}
        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
          <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block flex items-center gap-1">
            <DollarSign className="w-3 h-3 text-emerald-400" />
            {t("cockpit.aiSpend", "AI Spend")}
          </span>
          <div className="mt-2 text-2xl font-bold text-emerald-400">
            ${summary?.ai_spend.toFixed(2) ?? "0.00"}
          </div>
        </div>

        {/* Disk Usage */}
        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800">
          <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block flex items-center gap-1">
            <HardDrive className="w-3 h-3 text-zinc-400" />
            {t("cockpit.diskUsage", "Disk Usage")}
          </span>
          <div className="mt-2 text-2xl font-bold text-zinc-300">
            {summary?.disk_usage.database_mb ?? 0} MB
          </div>
        </div>
      </div>

      {/* Content Families Portfolio Status */}
      <div className="p-5 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-zinc-900/60 border border-indigo-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-indigo-600/20 border border-indigo-500/30 rounded-xl text-indigo-400">
            <Boxes className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white">
                {t("cockpit.contentFamilyEngine", "Content Family Engine")}
              </h3>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {t("cockpit.amortizedResearch", "Amortized Research")}
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-0.5">
              {t("cockpit.contentFamilyDesc", "Turn one evidence investment into multi-format, platform-tailored content items.")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-xs">
            <div className="px-3 py-1.5 rounded-lg bg-zinc-900/90 border border-zinc-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-400" />
              <span className="text-zinc-400 font-medium">
                <strong className="text-white font-bold">{activeFamiliesCount}</strong> {t("cockpit.familiesActive", "Content Families Active")}
              </span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-zinc-900/90 border border-zinc-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-zinc-400 font-medium">
                <strong className="text-white font-bold">{plannedItemsCount}</strong> {t("cockpit.plannedItems", "Planned Content Items")}
              </span>
            </div>
          </div>

          <Link
            href="/content-families"
            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
          >
            <span>{t("cockpit.openFamilies", "Open Families")}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Top Opportunity Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              {t("cockpit.topOpportunityTitle", "Top Opportunity Decisions")}
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              {t("cockpit.topOpportunityDesc", "Ranked by 10-factor opportunity intelligence. Explicit human approval required before research begins.")}
            </p>
          </div>
          <Link
            href="/opportunities"
            className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            {t("cockpit.viewAllOpportunities", "View All Opportunities")}
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="p-12 text-center text-sm text-zinc-500 flex items-center justify-center gap-2">
            <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
            {t("cockpit.loadingOpportunities", "Loading high-priority opportunities...")}
          </div>
        ) : summary?.top_opportunities && summary.top_opportunities.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {summary.top_opportunities.map((opp) => (
              <div
                key={opp.id}
                className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-6 flex flex-col justify-between space-y-5 hover:border-zinc-700 transition"
              >
                <div className="space-y-3.5">
                  {/* Score & Pillar Header */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="px-2.5 py-1 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-sm font-bold flex items-center gap-1">
                        <Compass className="w-3.5 h-3.5" />
                        <span>{Math.round(opp.opportunity_score)}/100</span>
                      </div>
                      <div className="px-2 py-0.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-semibold flex items-center gap-1">
                        <Flame className="w-3 h-3" />
                        <span>{t("cockpit.trendScore", "Trend:")} {Math.round(opp.trend_score)}</span>
                      </div>
                    </div>

                    {opp.pillar && (
                      <span className="text-[11px] px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-400 font-medium border border-zinc-700">
                        {opp.pillar}
                      </span>
                    )}
                  </div>

                  {/* Topic Title */}
                  <h3 className="text-base font-bold text-white tracking-tight leading-snug line-clamp-2">
                    {opp.topic}
                  </h3>

                  {/* Original Test Angle / Idea */}
                  <div className="p-3 rounded-xl bg-zinc-950/80 border border-zinc-800/80 space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 font-mono">
                      {t("cockpit.originalTestIdea", "Original Test Idea:")}
                    </span>
                    <p className="text-xs text-zinc-300 leading-relaxed font-mono">
                      {opp.suggested_original_angle}
                    </p>
                  </div>

                  {/* Content Family & Estimates */}
                  <div className="flex items-center justify-between text-xs text-zinc-400 pt-1">
                    <span className="font-medium text-zinc-300">
                      {t("cockpit.family", "Family:")} {opp.suggested_content_family}
                    </span>
                    <div className="flex items-center gap-3">
                      <span>{t("cockpit.effort", "Effort:")} <strong className="text-zinc-200 capitalize">{opp.production_effort}</strong></span>
                      <span>{t("cockpit.cost", "Cost:")} <strong className="text-emerald-400">${opp.estimated_cost.toFixed(2)}</strong></span>
                    </div>
                  </div>
                </div>

                {/* Human Gate Decision Buttons */}
                <div className="pt-4 border-t border-zinc-800/80 flex items-center justify-between gap-2">
                  {opp.status === "research_ready" || opp.status === "approved" ? (
                    <Link
                      href={`/content-families?new=1&topic_id=${opp.id}&title=${encodeURIComponent(opp.topic)}&pillar=${encodeURIComponent(opp.pillar || "Core")}`}
                      className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      <Boxes className="w-3.5 h-3.5" />
                      {t("cockpit.createContentFamily", "Create Content Family")}
                    </Link>
                  ) : (
                    <button
                      onClick={() => handleApprove(opp.id, opp.topic)}
                      className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5 shadow-sm"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {t("cockpit.approveResearch", "Research")}
                    </button>
                  )}

                  <button
                    onClick={() => handleWatch(opp.id, opp.topic)}
                    className="flex-1 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-xs font-semibold border border-zinc-700 transition flex items-center justify-center gap-1.5"
                  >
                    <Eye className="w-3.5 h-3.5 text-amber-400" />
                    {t("cockpit.watch", "Watch")}
                  </button>

                  <button
                    onClick={() => handleReject(opp.id, opp.topic)}
                    className="p-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-rose-400 rounded-lg border border-zinc-700 transition"
                    title={t("cockpit.rejectTopic", "Reject topic")}
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 rounded-2xl border border-dashed border-zinc-800 text-center space-y-3">
            <Compass className="w-10 h-10 text-zinc-600 mx-auto" />
            <h4 className="text-sm font-semibold text-white">
              {t("cockpit.noActiveOpportunities", "No active opportunities in review")}
            </h4>
            <p className="text-xs text-zinc-400 max-w-sm mx-auto">
              {t("cockpit.noActiveOpportunitiesDesc", "Run Opportunity intelligence analysis on discovered RSS candidates and trend topics to generate new proposals.")}
            </p>
            <button
              onClick={handleRunOpportunityAnalysis}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg transition"
            >
              {t("cockpit.analyzeOpportunitiesNow", "Analyze Opportunities Now")}
            </button>
          </div>
        )}
      </div>

      {/* Engine Health Summary Bar */}
      <div className="p-5 rounded-2xl bg-zinc-900/40 border border-zinc-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
              {t("cockpit.engineHealthSummary", "Engine Health Summary")}
            </h4>
          </div>
          <Link
            href="/engines"
            className="text-xs font-medium text-zinc-400 hover:text-white flex items-center gap-1"
          >
            {t("cockpit.configureEngines", "Configure Engines")}
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
          {summary?.engine_health_summary && summary.engine_health_summary.length > 0 ? (
            summary.engine_health_summary.map((eng) => (
              <div
                key={eng.id}
                className="p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 flex items-center justify-between text-xs"
              >
                <span className="font-medium text-zinc-300 truncate mr-2">{eng.name}</span>
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    eng.status === "healthy"
                      ? "bg-emerald-400 shadow-sm shadow-emerald-500/50"
                      : "bg-amber-400"
                  }`}
                  title={`${eng.name}: ${eng.status}`}
                />
              </div>
            ))
          ) : (
            <div className="text-xs text-zinc-500 col-span-full">
              {t("cockpit.engineCatalogInit", "Engine catalog initializing...")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
