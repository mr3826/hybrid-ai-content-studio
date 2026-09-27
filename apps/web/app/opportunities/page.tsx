"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Compass,
  Sparkles,
  Flame,
  Zap,
  CheckCircle2,
  XCircle,
  Eye,
  Info,
  Layers,
  ArrowRight,
  RefreshCw,
  Search,
  Filter,
  DollarSign,
  Clock,
  AlertTriangle,
  Play,
} from "lucide-react";
import {
  Opportunity,
  listOpportunities,
  runOpportunities,
  dryRunOpportunities,
  approveOpportunityResearch,
  watchOpportunity,
  rejectOpportunity,
} from "@/lib/api";

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [explainingOpp, setExplainingOpp] = useState<Opportunity | null>(null);

  // Filters & Sorting
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [pillarFilter, setPillarFilter] = useState<string>("all");
  const [familyFilter, setFamilyFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"opportunity_score" | "trend_score" | "originality" | "recency">("opportunity_score");
  const [searchQuery, setSearchQuery] = useState("");

  const [actionFeedback, setActionFeedback] = useState<{ type: "success" | "info" | "error"; text: string } | null>(null);

  const fetchOpportunitiesData = async () => {
    try {
      setLoading(true);
      const data = await listOpportunities({
        status: statusFilter === "all" ? undefined : statusFilter,
        pillar: pillarFilter === "all" ? undefined : pillarFilter,
        content_family: familyFilter === "all" ? undefined : familyFilter,
        sort_by: sortBy,
        limit: 100,
      });
      setOpportunities(data);
    } catch (err: any) {
      console.error("Opportunity load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOpportunitiesData();
  }, [statusFilter, pillarFilter, familyFilter, sortBy]);

  const handleRunAnalysis = async (dryRun: boolean = false) => {
    try {
      setRunningAnalysis(true);
      setActionFeedback({
        type: "info",
        text: dryRun
          ? "Simulating Opportunity scoring without modifying database..."
          : "Evaluating fresh candidate signals and trend momentum...",
      });
      const res = dryRun ? await dryRunOpportunities() : await runOpportunities();
      setActionFeedback({
        type: "success",
        text: res.summary || (dryRun ? "Dry run simulation complete." : "Opportunity analysis complete!"),
      });
      await fetchOpportunitiesData();
    } catch (err: any) {
      setActionFeedback({
        type: "error",
        text: `Analysis failed: ${err.message}`,
      });
    } finally {
      setRunningAnalysis(false);
    }
  };

  const handleApprove = async (opp: Opportunity) => {
    try {
      const updated = await approveOpportunityResearch(opp.id);
      setOpportunities((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
      setActionFeedback({
        type: "success",
        text: `Approved "${opp.topic}" for Research! Promoted to Research Ready.`,
      });
    } catch (err: any) {
      setActionFeedback({
        type: "error",
        text: `Failed to approve opportunity: ${err.message}`,
      });
    }
  };

  const handleWatch = async (opp: Opportunity) => {
    try {
      const updated = await watchOpportunity(opp.id);
      setOpportunities((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
      setActionFeedback({
        type: "info",
        text: `Moved "${opp.topic}" to Watch list.`,
      });
    } catch (err: any) {
      setActionFeedback({
        type: "error",
        text: `Failed to watch opportunity: ${err.message}`,
      });
    }
  };

  const handleReject = async (opp: Opportunity) => {
    try {
      const updated = await rejectOpportunity(opp.id, "Rejected by creator");
      setOpportunities((prev) => prev.map((o) => (o.id === updated.id ? updated : o)));
      setActionFeedback({
        type: "info",
        text: `Rejected "${opp.topic}".`,
      });
    } catch (err: any) {
      setActionFeedback({
        type: "error",
        text: `Failed to reject opportunity: ${err.message}`,
      });
    }
  };

  const filteredOpps = opportunities.filter((o) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      o.topic.toLowerCase().includes(q) ||
      o.suggested_original_angle.toLowerCase().includes(q) ||
      (o.pillar && o.pillar.toLowerCase().includes(q)) ||
      o.suggested_content_family.toLowerCase().includes(q)
    );
  });

  const availablePillars = Array.from(
    new Set(opportunities.map((o) => o.pillar).filter(Boolean) as string[])
  );

  const availableFamilies = Array.from(
    new Set(opportunities.map((o) => o.suggested_content_family).filter(Boolean) as string[])
  );

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <Compass className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
                Opportunity Intelligence
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  10-Factor Gate
                </span>
              </h1>
              <p className="text-sm text-zinc-400">
                Is this worth creating for THIS channel? Originality potential, audience usefulness & channel saturation.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => handleRunAnalysis(true)}
            disabled={runningAnalysis}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium border border-zinc-700 transition flex items-center gap-2 disabled:opacity-50"
          >
            <Play className="w-4 h-4 text-zinc-400" />
            Dry Run
          </button>
          <button
            onClick={() => handleRunAnalysis(false)}
            disabled={runningAnalysis}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-indigo-600/20 flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${runningAnalysis ? "animate-spin" : ""}`} />
            Evaluate Opportunities
          </button>
        </div>
      </div>

      {/* Notification Toast */}
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
            Dismiss
          </button>
        </div>
      )}

      {/* Search & Filter Controls */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-zinc-900/40 border border-zinc-800">
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search opportunities, angles, families..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto flex-wrap">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs font-medium text-zinc-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="needs_review">Needs Review</option>
            <option value="watching">Watching</option>
            <option value="research_ready">Research Ready</option>
            <option value="rejected">Rejected</option>
          </select>

          {/* Pillar Filter */}
          <select
            value={pillarFilter}
            onChange={(e) => setPillarFilter(e.target.value)}
            className="px-3 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs font-medium text-zinc-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Content Pillars</option>
            {availablePillars.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>

          {/* Content Family Filter */}
          <select
            value={familyFilter}
            onChange={(e) => setFamilyFilter(e.target.value)}
            className="px-3 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs font-medium text-zinc-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Content Families</option>
            {availableFamilies.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>

          {/* Sort By */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs font-medium text-zinc-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="opportunity_score">Sort by: Opportunity Score</option>
            <option value="trend_score">Sort by: Trend Score</option>
            <option value="originality">Sort by: Originality Potential</option>
            <option value="recency">Sort by: Recency</option>
          </select>
        </div>
      </div>

      {/* Opportunities List */}
      {loading ? (
        <div className="text-center py-20 text-zinc-500 text-sm flex items-center justify-center gap-2">
          <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
          Loading evaluated opportunities...
        </div>
      ) : filteredOpps.length === 0 ? (
        <div className="text-center py-20 rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20 space-y-3">
          <Compass className="w-12 h-12 text-zinc-600 mx-auto" />
          <h3 className="text-base font-semibold text-white">No opportunities found</h3>
          <p className="text-sm text-zinc-400 max-w-md mx-auto">
            Evaluate discovered RSS candidates and trend topics to populate the Opportunity Intelligence backlog.
          </p>
          <button
            onClick={() => handleRunAnalysis(false)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
          >
            Run Opportunity Evaluation
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          {filteredOpps.map((opp) => {
            const isApproved = opp.status === "research_ready" || opp.status === "approved";
            const isRejected = opp.status === "rejected";
            const isWatching = opp.status === "watching";

            return (
              <div
                key={opp.id}
                className={`rounded-2xl border transition p-6 space-y-5 ${
                  isRejected
                    ? "bg-zinc-900/30 border-zinc-800/40 opacity-60"
                    : isApproved
                    ? "bg-gradient-to-r from-zinc-900/90 via-zinc-900/60 to-emerald-950/20 border-emerald-500/30"
                    : "bg-zinc-900/60 border-zinc-800 hover:border-zinc-700"
                }`}
              >
                {/* Top header row */}
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      {/* Opportunity Score Badge */}
                      <div
                        className={`px-3 py-1 rounded-xl text-sm font-bold flex items-center gap-1.5 border ${
                          opp.opportunity_score >= 75
                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                            : opp.opportunity_score >= 50
                            ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                            : "bg-zinc-800 border-zinc-700 text-zinc-400"
                        }`}
                      >
                        <Compass className="w-4 h-4" />
                        <span>Score: {Math.round(opp.opportunity_score)}/100</span>
                      </div>

                      {/* Trend score pill */}
                      <span className="text-xs px-2.5 py-0.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold flex items-center gap-1">
                        <Flame className="w-3 h-3" />
                        Trend: {Math.round(opp.trend_score)}
                      </span>

                      {/* Status */}
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                          isApproved
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : isWatching
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                            : isRejected
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                            : "bg-indigo-500/10 text-indigo-400 border border-indigo-500/30"
                        }`}
                      >
                        {opp.status.replace("_", " ")}
                      </span>

                      {/* Content Family Badge */}
                      <span className="text-xs px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 font-medium border border-zinc-700">
                        {opp.suggested_content_family}
                      </span>

                      {/* Pillar */}
                      {opp.pillar && (
                        <span className="text-xs px-2.5 py-0.5 rounded-md bg-zinc-800/60 text-zinc-400 border border-zinc-800">
                          {opp.pillar}
                        </span>
                      )}
                    </div>

                    <h2 className="text-lg font-bold text-white tracking-tight leading-snug">
                      {opp.topic}
                    </h2>
                  </div>

                  {/* Explainability & Actions */}
                  <div className="flex items-center gap-2 self-start flex-wrap">
                    <button
                      onClick={() => setExplainingOpp(opp)}
                      className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold rounded-lg border border-zinc-700 flex items-center gap-1.5 transition"
                    >
                      <Info className="w-3.5 h-3.5 text-indigo-400" />
                      10 Dimensions
                    </button>

                    <button
                      onClick={() => handleApprove(opp)}
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1 shadow-sm"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Research
                    </button>

                    <button
                      onClick={() => handleWatch(opp)}
                      className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold rounded-lg border border-zinc-700 transition flex items-center gap-1"
                    >
                      <Eye className="w-3.5 h-3.5 text-amber-400" />
                      Watch
                    </button>

                    <button
                      onClick={() => handleReject(opp)}
                      className="p-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-rose-400 rounded-lg border border-zinc-700 transition"
                      title="Reject"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Original Test Angle Callout (Mandatory Spec Item) */}
                <div className="p-3.5 rounded-xl bg-zinc-950/70 border border-zinc-800 space-y-1.5">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400 font-mono flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5" />
                    Suggested Original Angle / Test Idea:
                  </span>
                  <p className="text-xs text-zinc-200 leading-relaxed font-mono">
                    {opp.suggested_original_angle}
                  </p>
                </div>

                {/* Why & Risks row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-zinc-300">
                  <div className="space-y-1">
                    <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                      Why this matters for our channel:
                    </span>
                    <p className="text-zinc-300 leading-relaxed">{opp.why}</p>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                      Risks & Verification Notes:
                    </span>
                    <ul className="list-disc list-inside space-y-1 text-zinc-400">
                      {opp.risks.map((r, idx) => (
                        <li key={idx} className="leading-relaxed">
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Production Effort & Estimates bar */}
                <div className="pt-3 border-t border-zinc-800/60 flex items-center justify-between text-xs text-zinc-400 flex-wrap gap-2">
                  <div className="flex items-center gap-4">
                    <span>
                      Effort: <strong className="text-zinc-200 capitalize">{opp.production_effort}</strong>
                    </span>
                    <span>
                      Est. Cost: <strong className="text-emerald-400">${opp.estimated_cost.toFixed(2)}</strong>
                    </span>
                    <span>
                      Est. Production: <strong className="text-zinc-200">{opp.estimated_time_minutes} mins</strong>
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-zinc-500 font-mono">
                      Recommended: <strong className="text-indigo-400">{opp.recommended_action}</strong>
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 10-Dimensions Explainability Modal */}
      {explainingOpp && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                  <Info className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">10 Scoring Dimensions</h3>
                  <p className="text-xs text-zinc-400">{explainingOpp.topic}</p>
                </div>
              </div>
              <button
                onClick={() => setExplainingOpp(null)}
                className="text-zinc-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Total summary */}
            <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold uppercase text-zinc-400">
                  Composite Opportunity Score
                </span>
                <div className="text-2xl font-bold text-emerald-400 mt-1">
                  {Math.round(explainingOpp.opportunity_score)} / 100
                </div>
              </div>
              <div className="text-right text-xs text-zinc-400 font-mono space-y-1">
                <div>Raw Positive: {explainingOpp.score_breakdown.raw_score.toFixed(1)} / 100</div>
                {explainingOpp.score_breakdown.saturation_penalty > 0 && (
                  <div className="text-rose-400 font-bold">
                    Saturation Penalty: -{explainingOpp.score_breakdown.saturation_penalty.toFixed(1)}
                  </div>
                )}
              </div>
            </div>

            {/* 10 Dimensions Breakdown */}
            <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Editable Dimensions Decomposition
              </h4>

              <div className="space-y-2.5 text-xs">
                {/* 1. Niche Fit */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>1. Niche Fit (Weight: 18)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.niche_fit.toFixed(1)} / 18</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-indigo-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.niche_fit / 18) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 2. Original Test Potential */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>2. Original Test / Value Potential (Weight: 20)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.original_value.toFixed(1)} / 20</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-emerald-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.original_value / 20) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 3. Audience Usefulness */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>3. Audience Problem Usefulness (Weight: 15)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.audience_usefulness.toFixed(1)} / 15</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-sky-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.audience_usefulness / 15) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 4. Search / Evergreen Value */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>4. Search / Evergreen Value (Weight: 12)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.evergreen_value.toFixed(1)} / 12</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-amber-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.evergreen_value / 12) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 5. Trend Momentum */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>5. Trend Momentum (Weight: 10)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.trend_momentum.toFixed(1)} / 10</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-rose-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.trend_momentum / 10) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 6. Commercial Fit */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>6. Commercial / Affiliate Fit (Weight: 10)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.commercial_fit.toFixed(1)} / 10</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-teal-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.commercial_fit / 10) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 7. Content-Family Potential */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>7. Content-Family Multi-Format Potential (Weight: 5)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.content_family_potential.toFixed(1)} / 5</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-purple-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.content_family_potential / 5) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 8. Sponsor Relevance */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>8. Sponsor Relevance (Weight: 3)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.sponsor_relevance.toFixed(1)} / 3</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-yellow-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.sponsor_relevance / 3) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 9. Production Effort Economy */}
                <div>
                  <div className="flex justify-between text-zinc-300 mb-1">
                    <span>9. Production Effort Economy (Weight: 4)</span>
                    <span className="font-mono">{explainingOpp.score_breakdown.production_effort_score.toFixed(1)} / 4</span>
                  </div>
                  <div className="w-full bg-zinc-800 rounded-full h-1.5">
                    <div
                      className="bg-blue-500 h-1.5 rounded-full"
                      style={{ width: `${(explainingOpp.score_breakdown.production_effort_score / 4) * 100}%` }}
                    />
                  </div>
                </div>

                {/* 10. Channel Saturation Penalty */}
                {explainingOpp.score_breakdown.saturation_penalty > 0 && (
                  <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-300">
                    <div className="flex justify-between font-semibold">
                      <span>10. Recent Channel Saturation Penalty</span>
                      <span className="font-mono">-{explainingOpp.score_breakdown.saturation_penalty.toFixed(1)}</span>
                    </div>
                    <p className="text-[11px] text-rose-400/80 mt-1">
                      Deduction applied because closely matching topic was covered in channel memory within past 30 days.
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-zinc-800">
              <button
                onClick={() => setExplainingOpp(null)}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm font-medium transition"
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
