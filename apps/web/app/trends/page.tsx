"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp,
  Sparkles,
  Play,
  RefreshCw,
  Plus,
  Search,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Clock,
  Flame,
  Zap,
  CheckCircle2,
  VolumeX,
  Volume2,
  Info,
  Layers,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";
import {
  TrendTopic,
  listTrends,
  runTrends,
  dryRunTrends,
  boostTrend,
  suppressTrend,
  createManualSignal,
} from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

export default function TrendsPage() {
  const { t, isBangla } = useLanguage();
  const [trends, setTrends] = useState<TrendTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [expandedTopicId, setExpandedTopicId] = useState<string | null>(null);
  const [explainingTopic, setExplainingTopic] = useState<TrendTopic | null>(null);

  // Filters & Sorting
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [pillarFilter, setPillarFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"trend_score" | "velocity" | "recency" | "mentions">("trend_score");
  const [searchQuery, setSearchQuery] = useState("");

  // Manual Signal Modal
  const [showSignalModal, setShowSignalModal] = useState(false);
  const [signalTitle, setSignalTitle] = useState("");
  const [signalSource, setSignalSource] = useState("Manual Trend Observer");
  const [signalSummary, setSignalSummary] = useState("");
  const [signalUrl, setSignalUrl] = useState("");
  const [signalPillar, setSignalPillar] = useState("");
  const [signalTrust, setSignalTrust] = useState(0.9);

  // Toast / notification
  const [actionMessage, setActionMessage] = useState<{
    type: "success" | "error" | "info";
    text: string;
  } | null>(null);

  const fetchTrendsData = async () => {
    try {
      setLoading(true);
      const data = await listTrends({
        sort_by: sortBy,
        status: statusFilter === "all" ? undefined : statusFilter,
        pillar: pillarFilter === "all" ? undefined : pillarFilter,
        limit: 100,
      });
      setTrends(data);
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: `Failed to load trends: ${err.message || "Unknown error"}`,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrendsData();
  }, [sortBy, statusFilter, pillarFilter]);

  const handleRunAnalysis = async (dryRun: boolean = false) => {
    try {
      setRunningAnalysis(true);
      setActionMessage({
        type: "info",
        text: dryRun
          ? "Simulating Trends momentum analysis (dry-run)..."
          : "Analyzing niche signals, velocities, and multi-source momentum...",
      });

      const res = dryRun ? await dryRunTrends() : await runTrends();
      setActionMessage({
        type: "success",
        text: res.summary || (dryRun ? "Dry run completed successfully." : "Trends analysis complete!"),
      });
      await fetchTrendsData();
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: `Trends run failed: ${err.message || "Unknown error"}`,
      });
    } finally {
      setRunningAnalysis(false);
    }
  };

  const handleBoost = async (topic: TrendTopic, factor: number) => {
    try {
      const updated = await boostTrend(topic.id, factor);
      setTrends((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setActionMessage({
        type: "success",
        text: `Applied ${factor}x manual boost to "${topic.title}".`,
      });
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: `Failed to boost trend: ${err.message}`,
      });
    }
  };

  const handleToggleSuppress = async (topic: TrendTopic) => {
    try {
      const nextSuppress = !topic.is_suppressed;
      const updated = await suppressTrend(topic.id, nextSuppress);
      setTrends((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setActionMessage({
        type: "info",
        text: nextSuppress
          ? `Suppressed topic "${topic.title}". Trend score clamped to 0.`
          : `Restored topic "${topic.title}" to active status.`,
      });
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: `Failed to toggle suppression: ${err.message}`,
      });
    }
  };

  const handleCreateManualSignal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await createManualSignal({
        title: signalTitle,
        source_name: signalSource,
        summary: signalSummary,
        url: signalUrl || undefined,
        pillar: signalPillar || undefined,
        trust_weight: signalTrust,
      });

      setShowSignalModal(false);
      setSignalTitle("");
      setSignalSummary("");
      setSignalUrl("");
      setSignalPillar("");

      setActionMessage({
        type: "success",
        text: `Injected signal and established topic cluster: "${created.title}".`,
      });
      await fetchTrendsData();
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: `Failed to add manual signal: ${err.message}`,
      });
    }
  };

  // Filter trends by search query
  const filteredTrends = trends.filter((t) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      t.title.toLowerCase().includes(q) ||
      t.summary.toLowerCase().includes(q) ||
      t.keywords.some((k) => k.toLowerCase().includes(q)) ||
      (t.pillar && t.pillar.toLowerCase().includes(q))
    );
  });

  // Unique pillars for filter dropdown
  const availablePillars = Array.from(
    new Set(trends.map((t) => t.pillar).filter(Boolean) as string[])
  );

  // Metrics summary
  const activeTrendsCount = trends.filter((t) => !t.is_suppressed).length;
  const emergingCount = trends.filter((t) => t.status === "emerging" && !t.is_suppressed).length;
  const highestVelocityTopic = trends
    .filter((t) => !t.is_suppressed)
    .sort((a, b) => b.velocity_ratio - a.velocity_ratio)[0];
  const avgDiversity =
    trends.length > 0
      ? (
          trends.reduce((acc, t) => acc + (t.distinct_sources_count || 1), 0) /
          trends.length
        ).toFixed(1)
      : "1.0";

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                {t("trends.title", "Trends Engine")}
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  Zero Paid APIs
                </span>
              </h1>
              <p className="text-sm text-zinc-400">
                {t("trends.subtitle", "What is gaining momentum inside our niche? Velocity, cross-source grouping & explainable scoring.")}
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
            {isBangla ? "টেস্ট রান" : "Dry Run"}
          </button>

          <button
            onClick={() => handleRunAnalysis(false)}
            disabled={runningAnalysis}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-rose-600/20 flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${runningAnalysis ? "animate-spin" : ""}`} />
            {runningAnalysis
              ? (isBangla ? "এনালাইসিস চলছে..." : "Running...")
              : (isBangla ? "ট্রেন্ড এনালাইসিস চালান" : "Run Trends")}
          </button>

          <button
            onClick={() => setShowSignalModal(true)}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm font-medium border border-zinc-700 transition flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {isBangla ? "নতুন সিগন্যাল যোগ" : "Add Signal"}
          </button>
        </div>
      </div>

      {/* Action Feedback Banner */}
      {actionMessage && (
        <div
          className={`p-4 rounded-xl text-sm flex items-start justify-between border ${
            actionMessage.type === "success"
              ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
              : actionMessage.type === "error"
              ? "bg-rose-950/40 border-rose-500/30 text-rose-300"
              : "bg-blue-950/40 border-blue-500/30 text-blue-300"
          }`}
        >
          <div className="flex items-center gap-2">
            <Info className="w-5 h-5 flex-shrink-0" />
            <span>{actionMessage.text}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-xs hover:underline opacity-80"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Active Trends
            </span>
            <Sparkles className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">{activeTrendsCount}</span>
            <span className="text-xs text-zinc-500">clusters tracked</span>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Emerging Momentum
            </span>
            <Flame className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-amber-400">{emergingCount}</span>
            <span className="text-xs text-zinc-500">accelerating</span>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Peak Velocity
            </span>
            <Zap className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-emerald-400">
              {highestVelocityTopic
                ? `+${Math.round(highestVelocityTopic.velocity_ratio * 100)}%`
                : "0%"}
            </span>
            <span className="text-xs text-zinc-500">vs baseline</span>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Avg Source Diversity
            </span>
            <Layers className="w-4 h-4 text-sky-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-sky-400">{avgDiversity}</span>
            <span className="text-xs text-zinc-500">sources/topic</span>
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-zinc-900/40 border border-zinc-800">
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search trend topics, entities, keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-rose-500 transition"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto flex-wrap">
          {/* Pillar Filter */}
          <select
            value={pillarFilter}
            onChange={(e) => setPillarFilter(e.target.value)}
            className="px-3 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs font-medium text-zinc-300 focus:outline-none focus:border-rose-500"
          >
            <option value="all">All Content Pillars</option>
            {availablePillars.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs font-medium text-zinc-300 focus:outline-none focus:border-rose-500"
          >
            <option value="all">All Statuses</option>
            <option value="emerging">Emerging</option>
            <option value="active">Active</option>
            <option value="cooling">Cooling</option>
            <option value="archived">Archived / Suppressed</option>
          </select>

          {/* Sort By */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-2 bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs font-medium text-zinc-300 focus:outline-none focus:border-rose-500"
          >
            <option value="trend_score">Sort by: Trend Score</option>
            <option value="velocity">Sort by: Velocity & Momentum</option>
            <option value="recency">Sort by: First Seen Recency</option>
            <option value="mentions">Sort by: Mention Count</option>
          </select>
        </div>
      </div>

      {/* Trends Feed */}
      {loading ? (
        <div className="text-center py-20 text-zinc-500 text-sm flex items-center justify-center gap-2">
          <RefreshCw className="w-5 h-5 animate-spin text-rose-500" />
          Loading trend momentum signals...
        </div>
      ) : filteredTrends.length === 0 ? (
        <div className="text-center py-20 rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/20">
          <TrendingUp className="w-12 h-12 text-zinc-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">No trend topics detected</h3>
          <p className="text-sm text-zinc-400 mt-1 max-w-md mx-auto">
            Run Trends analysis across discovered RSS signals or add a manual trend signal to establish topic momentum.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              onClick={() => handleRunAnalysis(false)}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm font-medium transition"
            >
              Analyze Discovered Signals
            </button>
            <button
              onClick={() => setShowSignalModal(true)}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium transition border border-zinc-700"
            >
              Add Manual Signal
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredTrends.map((topic) => {
            const isExpanded = expandedTopicId === topic.id;
            const explanationSummary = topic.explanation?.summary || "";
            const isEmerging = topic.status === "emerging";
            const isSuppressed = topic.is_suppressed;

            return (
              <div
                key={topic.id}
                className={`rounded-2xl border transition ${
                  isSuppressed
                    ? "bg-zinc-900/30 border-zinc-800/40 opacity-60"
                    : isEmerging
                    ? "bg-gradient-to-r from-zinc-900/90 via-zinc-900/60 to-rose-950/20 border-rose-500/30 hover:border-rose-500/50"
                    : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-700"
                } p-6 space-y-4`}
              >
                {/* Header row */}
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      {/* Trend Score Ring / Badge */}
                      <div
                        className={`px-3 py-1 rounded-xl font-bold text-sm flex items-center gap-1.5 border ${
                          topic.trend_score >= 80
                            ? "bg-rose-500/10 border-rose-500/30 text-rose-400"
                            : topic.trend_score >= 50
                            ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                            : "bg-zinc-800 border-zinc-700 text-zinc-400"
                        }`}
                      >
                        <Flame className="w-3.5 h-3.5" />
                        <span>{Math.round(topic.trend_score)} / 100</span>
                      </div>

                      {/* Status badge */}
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                          topic.status === "emerging"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : topic.status === "active"
                            ? "bg-sky-500/10 text-sky-400 border border-sky-500/30"
                            : topic.status === "cooling"
                            ? "bg-zinc-800 text-zinc-400 border border-zinc-700"
                            : "bg-zinc-800 text-zinc-500"
                        }`}
                      >
                        {topic.status}
                      </span>

                      {/* Content Pillar */}
                      {topic.pillar && (
                        <span className="text-xs px-2.5 py-0.5 rounded-md bg-zinc-800/80 text-zinc-300 border border-zinc-700/60 font-medium">
                          {topic.pillar}
                        </span>
                      )}

                      {/* Manual Boost indicator */}
                      {topic.manual_boost > 1.0 && (
                        <span className="text-xs px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30 font-semibold">
                          +{Math.round((topic.manual_boost - 1) * 100)}% Boosted
                        </span>
                      )}

                      {/* Suppressed indicator */}
                      {topic.is_suppressed && (
                        <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-700 font-semibold flex items-center gap-1">
                          <VolumeX className="w-3 h-3" /> Suppressed
                        </span>
                      )}
                    </div>

                    <h2 className="text-lg font-bold text-white tracking-tight leading-snug">
                      {topic.title}
                    </h2>

                    <p className="text-sm text-zinc-300 leading-relaxed line-clamp-2">
                      {topic.summary}
                    </p>
                  </div>

                  {/* Actions & Explainability button */}
                  <div className="flex items-center gap-2 self-start flex-wrap">
                    <button
                      onClick={() => setExplainingTopic(topic)}
                      className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold rounded-lg border border-zinc-700 flex items-center gap-1.5 transition"
                      title="Inspect score breakdown and mathematical explainability"
                    >
                      <Info className="w-3.5 h-3.5 text-rose-400" />
                      Explain Score
                    </button>

                    <button
                      onClick={() => handleBoost(topic, topic.manual_boost > 1.0 ? 1.0 : 1.25)}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition flex items-center gap-1 ${
                        topic.manual_boost > 1.0
                          ? "bg-purple-950/40 border-purple-500/40 text-purple-300 hover:bg-purple-900/60"
                          : "bg-zinc-800 hover:bg-zinc-700 border-zinc-700 text-zinc-300"
                      }`}
                      title={topic.manual_boost > 1.0 ? "Reset Boost" : "Boost +25%"}
                    >
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                      {topic.manual_boost > 1.0 ? "Reset Boost" : "Boost (+25%)"}
                    </button>

                    <button
                      onClick={() => handleToggleSuppress(topic)}
                      className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-400 hover:text-white transition"
                      title={topic.is_suppressed ? "Unsuppress topic" : "Suppress topic"}
                    >
                      {topic.is_suppressed ? (
                        <Volume2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <VolumeX className="w-4 h-4" />
                      )}
                    </button>

                    <a
                      href={`/opportunities?seed_topic=${encodeURIComponent(topic.title)}`}
                      className="px-3 py-1.5 bg-rose-600/90 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1 shadow-sm"
                    >
                      Promote
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>

                {/* Explainability Banner (Mandatory Spec Item) */}
                <div className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/80 flex items-center justify-between text-xs text-zinc-300">
                  <div className="flex items-center gap-2 font-mono flex-wrap">
                    <span className="text-rose-400 font-semibold">SIGNAL VERDICT:</span>
                    <span>{explanationSummary || "Awaiting multi-signal convergence."}</span>
                  </div>
                  <div className="flex items-center gap-4 text-zinc-500 text-xs">
                    <span>{topic.velocity.toFixed(1)}/hr</span>
                    <span>{topic.distinct_sources_count} sources</span>
                  </div>
                </div>

                {/* Keywords & Sources row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1 border-t border-zinc-800/50">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {topic.keywords.map((kw) => (
                      <span
                        key={kw}
                        className="text-xs px-2 py-0.5 rounded-md bg-zinc-800/60 text-zinc-400 border border-zinc-800"
                      >
                        #{kw}
                      </span>
                    ))}
                  </div>

                  <button
                    onClick={() => setExpandedTopicId(isExpanded ? null : topic.id)}
                    className="text-xs text-zinc-400 hover:text-white flex items-center gap-1 self-end sm:self-auto transition"
                  >
                    <span>
                      {topic.source_breakdown?.length || topic.mention_count} sources linked
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>

                {/* Expandable Sources Breakdown */}
                {isExpanded && (
                  <div className="mt-3 p-4 rounded-xl bg-zinc-950/80 border border-zinc-800/80 space-y-2">
                    <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                      Cross-Source Reporting Breakdown
                    </h4>
                    {topic.source_breakdown && topic.source_breakdown.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {topic.source_breakdown.map((s, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs"
                          >
                            <span className="font-medium text-zinc-200">{s.source_name}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-zinc-500 font-mono">
                                Trust: {(s.trust_weight * 100).toFixed(0)}%
                              </span>
                              {s.url && (
                                <a
                                  href={s.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-rose-400 hover:text-rose-300"
                                >
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-zinc-500">
                        Signal aggregated from primary discovered candidate feed.
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Explainability Breakdown Modal */}
      {explainingTopic && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
                  <Info className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Transparent Explainability</h3>
                  <p className="text-xs text-zinc-400">{explainingTopic.title}</p>
                </div>
              </div>
              <button
                onClick={() => setExplainingTopic(null)}
                className="text-zinc-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Main formula summary */}
            <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 text-sm space-y-2">
              <span className="text-xs uppercase tracking-wider font-semibold text-rose-400 font-mono">
                Formula Verdict
              </span>
              <p className="text-zinc-200 font-medium font-mono text-sm leading-relaxed">
                "{explainingTopic.explanation?.summary}"
              </p>
            </div>

            {/* Score Factors Breakdown */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Scoring Dimensions (0 - 100)
              </h4>

              {explainingTopic.explanation?.breakdown && (
                <div className="space-y-3">
                  {/* Mentions */}
                  <div>
                    <div className="flex justify-between text-xs text-zinc-300 mb-1">
                      <span>Cross-Source Mentions (Weight: 25%)</span>
                      <span className="font-mono">
                        {explainingTopic.explanation.breakdown.base_mentions_score.toFixed(1)} / 100
                      </span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2">
                      <div
                        className="bg-rose-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            explainingTopic.explanation.breakdown.base_mentions_score
                          )}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Velocity */}
                  <div>
                    <div className="flex justify-between text-xs text-zinc-300 mb-1">
                      <span>Mention Velocity & Acceleration (Weight: 30%)</span>
                      <span className="font-mono">
                        {explainingTopic.explanation.breakdown.velocity_score.toFixed(1)} / 100
                      </span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2">
                      <div
                        className="bg-emerald-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            explainingTopic.explanation.breakdown.velocity_score
                          )}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Recency */}
                  <div>
                    <div className="flex justify-between text-xs text-zinc-300 mb-1">
                      <span>First-Seen Recency Decay (Weight: 20%)</span>
                      <span className="font-mono">
                        {explainingTopic.explanation.breakdown.recency_score.toFixed(1)} / 100
                      </span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2">
                      <div
                        className="bg-amber-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            explainingTopic.explanation.breakdown.recency_score
                          )}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Authority */}
                  <div>
                    <div className="flex justify-between text-xs text-zinc-300 mb-1">
                      <span>Source Trust & Authority (Weight: 15%)</span>
                      <span className="font-mono">
                        {explainingTopic.explanation.breakdown.source_authority_score.toFixed(1)} / 100
                      </span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2">
                      <div
                        className="bg-sky-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            explainingTopic.explanation.breakdown.source_authority_score
                          )}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Diversity */}
                  <div>
                    <div className="flex justify-between text-xs text-zinc-300 mb-1">
                      <span>Source Diversity & Entropy (Weight: 10%)</span>
                      <span className="font-mono">
                        {explainingTopic.explanation.breakdown.source_diversity_score.toFixed(1)} / 100
                      </span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-2">
                      <div
                        className="bg-purple-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            explainingTopic.explanation.breakdown.source_diversity_score
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-4 border-t border-zinc-800">
              <button
                onClick={() => setExplainingTopic(null)}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm font-medium transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Signal Modal */}
      {showSignalModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateManualSignal}
            className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-rose-500" />
                Add Manual Trend Signal
              </h3>
              <button
                type="button"
                onClick={() => setShowSignalModal(false)}
                className="text-zinc-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1">
                  Topic Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. OpenAI Operator Autonomous Browser Agent"
                  value={signalTitle}
                  onChange={(e) => setSignalTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:border-rose-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1">
                  Source Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Hacker News Frontpage"
                  value={signalSource}
                  onChange={(e) => setSignalSource(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:border-rose-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1">
                  Summary / Key Takeaway
                </label>
                <textarea
                  rows={3}
                  placeholder="Describe the momentum observation or emerging development..."
                  value={signalSummary}
                  onChange={(e) => setSignalSummary(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:border-rose-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1">
                    Content Pillar (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Agentic Workflows"
                    value={signalPillar}
                    onChange={(e) => setSignalPillar(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:border-rose-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-1">
                    Trust Weight: {signalTrust}
                  </label>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    value={signalTrust}
                    onChange={(e) => setSignalTrust(parseFloat(e.target.value))}
                    className="w-full accent-rose-500 mt-2"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-300 mb-1">
                  Reference URL (Optional)
                </label>
                <input
                  type="url"
                  placeholder="https://news.ycombinator.com/item?id=..."
                  value={signalUrl}
                  onChange={(e) => setSignalUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:border-rose-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-zinc-800">
              <button
                type="button"
                onClick={() => setShowSignalModal(false)}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm font-medium transition shadow-md shadow-rose-600/20"
              >
                Inject Signal
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
