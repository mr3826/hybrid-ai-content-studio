"use client";

import { useEffect, useState } from "react";
import {
  Rss,
  Plus,
  RefreshCw,
  Play,
  ShieldCheck,
  ShieldAlert,
  ExternalLink,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Layers,
  Search,
  ChevronDown,
  ChevronUp,
  Clock,
  Info,
  Sparkles,
} from "lucide-react";
import {
  RssFeed,
  DiscoveredCandidate,
  listRssFeeds,
  createRssFeed,
  updateRssFeed,
  deleteRssFeed,
  runRssDiscovery,
  dryRunRssDiscovery,
  listDiscoveredCandidates,
} from "@/lib/api";

export default function SourcesPage() {
  const [feeds, setFeeds] = useState<RssFeed[]>([]);
  const [candidates, setCandidates] = useState<DiscoveredCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningDiscovery, setRunningDiscovery] = useState(false);
  const [activeTab, setActiveTab] = useState<"candidates" | "sources">("candidates");

  // Filter state for candidates
  const [statusFilter, setStatusFilter] = useState<string>("candidate");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null);

  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newFeedName, setNewFeedName] = useState("");
  const [newFeedUrl, setNewFeedUrl] = useState("");
  const [newFeedCategory, setNewFeedCategory] = useState("General");
  const [newFeedTrust, setNewFeedTrust] = useState(0.8);
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [feedsData, candidatesData] = await Promise.all([
        listRssFeeds(),
        listDiscoveredCandidates({ limit: 100 }),
      ]);
      setFeeds(feedsData);
      setCandidates(candidatesData);
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to load RSS sources" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddFeed = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFeedName || !newFeedUrl) return;
    try {
      await createRssFeed({
        name: newFeedName,
        url: newFeedUrl,
        category: newFeedCategory,
        trust_weight: newFeedTrust,
        enabled: true,
      });
      setShowAddModal(false);
      setNewFeedName("");
      setNewFeedUrl("");
      setActionMessage({ type: "success", text: `Feed "${newFeedName}" added successfully.` });
      await fetchData();
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to add feed" });
    }
  };

  const handleToggleFeed = async (feed: RssFeed) => {
    try {
      await updateRssFeed(feed.id, { enabled: !feed.enabled });
      setFeeds(feeds.map((f) => (f.id === feed.id ? { ...f, enabled: !f.enabled } : f)));
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to update feed" });
    }
  };

  const handleDeleteFeed = async (feedId: string, feedName: string) => {
    if (!confirm(`Delete feed "${feedName}"?`)) return;
    try {
      await deleteRssFeed(feedId);
      setFeeds(feeds.filter((f) => f.id !== feedId));
      setActionMessage({ type: "info", text: `Feed "${feedName}" removed.` });
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Failed to delete feed" });
    }
  };

  const handleRunDiscovery = async (isDryRun: boolean = false) => {
    try {
      setRunningDiscovery(true);
      setActionMessage({ type: "info", text: isDryRun ? "Running dry-run preview..." : "Polling feeds and running Niche Guard..." });
      
      const response = isDryRun
        ? await dryRunRssDiscovery()
        : await runRssDiscovery();

      const out = response.engine_result;
      setActionMessage({
        type: "success",
        text: out.summary || `Discovered ${out.output_count} candidate(s).`,
      });
      await fetchData();
    } catch (err: any) {
      setActionMessage({ type: "error", text: err.message || "Discovery run failed" });
    } finally {
      setRunningDiscovery(false);
    }
  };

  const filteredCandidates = candidates.filter((cand) => {
    if (statusFilter !== "all" && cand.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        cand.title.toLowerCase().includes(q) ||
        cand.summary.toLowerCase().includes(q) ||
        (cand.pillar && cand.pillar.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-orange-500/10 text-orange-400 flex items-center justify-center font-bold">
              <Rss className="w-4 h-4" />
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">RSS Source Discovery</h1>
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
              Phase 4 Active
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Resilient local source discovery with exact and near-title deduplication, cross-source grouping,
            freshness filtering, and deterministic Niche Guard validation with zero AI calls.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => handleRunDiscovery(true)}
            disabled={runningDiscovery}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 text-amber-400" />
            <span>Dry Run</span>
          </button>

          <button
            onClick={() => handleRunDiscovery(false)}
            disabled={runningDiscovery}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${runningDiscovery ? "animate-spin" : ""}`} />
            <span>{runningDiscovery ? "Polling..." : "Run Discovery"}</span>
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
          >
            <Plus className="w-3.5 h-3.5 text-emerald-400" />
            <span>Add Source</span>
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div
          className={`p-3.5 rounded-xl border flex items-center justify-between text-xs ${
            actionMessage.type === "success"
              ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
              : actionMessage.type === "error"
              ? "bg-rose-950/40 border-rose-800 text-rose-300"
              : "bg-indigo-950/40 border-indigo-800 text-indigo-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {actionMessage.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : actionMessage.type === "error" ? (
              <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
            ) : (
              <Info className="w-4 h-4 text-indigo-400 shrink-0" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-slate-400 hover:text-white text-xs px-2 py-0.5"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab("candidates")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "candidates"
              ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Discovered Candidates ({candidates.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("sources")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-colors ${
            activeTab === "sources"
              ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
          }`}
        >
          <Rss className="w-3.5 h-3.5" />
          <span>Configured Feeds ({feeds.length})</span>
        </button>
      </div>

      {/* TAB 1: DISCOVERED CANDIDATES */}
      {activeTab === "candidates" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search headlines, pillars..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="candidate">In-Niche Approved</option>
                <option value="rejected">Rejected Off-Niche</option>
                <option value="all">All Discovered Items</option>
              </select>
            </div>

            <div className="text-[11px] text-slate-400">
              Showing {filteredCandidates.length} of {candidates.length} candidates
            </div>
          </div>

          {/* Candidate Cards List */}
          {loading ? (
            <div className="p-12 text-center text-slate-500 text-xs">Loading discovered items...</div>
          ) : filteredCandidates.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-slate-800 space-y-3">
              <Rss className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-sm font-semibold text-slate-300">No candidates match your current filter</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Trigger a Discovery Run above or add new RSS feeds to ingest fresh signals into your studio.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredCandidates.map((cand) => {
                const isExpanded = expandedCandidateId === cand.id;
                const isApproved = cand.is_in_niche && cand.status === "candidate";

                return (
                  <div
                    key={cand.id}
                    className={`rounded-xl border transition-all ${
                      isApproved
                        ? "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                        : "bg-slate-950/40 border-slate-900/80 opacity-75"
                    }`}
                  >
                    <div className="p-4 space-y-2.5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            {/* In-Niche / Rejected Status Badge */}
                            {isApproved ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                <ShieldCheck className="w-3 h-3" />
                                <span>In Niche ({Math.round(cand.niche_score)}%)</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                                <ShieldAlert className="w-3 h-3" />
                                <span>Rejected</span>
                              </span>
                            )}

                            {/* Content Pillar Badge */}
                            {cand.pillar && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                                {cand.pillar}
                              </span>
                            )}

                            {/* Cross-source grouped badge */}
                            {cand.source_count > 1 ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                                <Sparkles className="w-3 h-3 text-amber-400" />
                                <span>{cand.source_count} Sources Grouped</span>
                              </span>
                            ) : (
                              <span className="text-[10px] text-slate-400">
                                Source: <strong>{cand.primary_source}</strong>
                              </span>
                            )}

                            {/* Authority Score Mix */}
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
                              Auth: {cand.authority_score.toFixed(2)}
                            </span>
                          </div>

                          <h3 className="text-sm font-semibold text-white leading-snug hover:text-indigo-300 transition-colors">
                            <a
                              href={cand.canonical_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1"
                            >
                              <span>{cand.title}</span>
                              <ExternalLink className="w-3 h-3 text-slate-500 shrink-0" />
                            </a>
                          </h3>
                        </div>

                        <button
                          onClick={() => setExpandedCandidateId(isExpanded ? null : cand.id)}
                          className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>

                      {cand.summary && (
                        <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                          {cand.summary}
                        </p>
                      )}

                      <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1 border-t border-slate-800/60">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(cand.published_at).toLocaleDateString()}</span>
                        </span>
                        <span>Fingerprint: <code className="text-slate-400">{cand.content_fingerprint.slice(0, 8)}</code></span>
                      </div>
                    </div>

                    {/* Expandable Explanation & Source Breakdown */}
                    {isExpanded && (
                      <div className="px-4 pb-4 pt-2 border-t border-slate-800/60 bg-slate-950/60 space-y-3 rounded-b-xl text-xs">
                        {/* Cross-source reporting sources list */}
                        {cand.sources && cand.sources.length > 0 && (
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                              Reporting Sources ({cand.sources.length})
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                              {cand.sources.map((s, idx) => (
                                <div
                                  key={idx}
                                  className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-[11px]"
                                >
                                  <div>
                                    <div className="font-semibold text-slate-200">{s.feed_name}</div>
                                    <a
                                      href={s.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-slate-400 hover:underline text-[10px] truncate block max-w-[200px]"
                                    >
                                      {s.url}
                                    </a>
                                  </div>
                                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">
                                    Trust: {s.trust_weight}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Niche Guard Verdict Breakdown */}
                        {cand.niche_verdict && (
                          <div>
                            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                              Niche Guard Verdict & Factors
                            </span>
                            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
                              <p className="text-slate-300 font-medium">
                                {cand.niche_verdict.reason || "Evaluated by deterministic taxonomy."}
                              </p>

                              {cand.niche_verdict.factors && (
                                <div className="space-y-1 pt-1">
                                  {cand.niche_verdict.factors.map((f: any, fIdx: number) => (
                                    <div key={fIdx} className="flex items-center justify-between text-[11px]">
                                      <span className="text-slate-400">{f.detail}</span>
                                      <span
                                        className={`font-mono font-bold ${
                                          f.points > 0 ? "text-emerald-400" : f.points < 0 ? "text-rose-400" : "text-slate-500"
                                        }`}
                                      >
                                        {f.points > 0 ? `+${f.points}` : f.points}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: CONFIGURED FEEDS */}
      {activeTab === "sources" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Active Feed Sources</h2>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Feed Source</span>
            </button>
          </div>

          <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/40">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 font-medium">
                <tr>
                  <th className="p-3">Source Name</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Trust Weight</th>
                  <th className="p-3">Status / Health</th>
                  <th className="p-3">Enabled</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {feeds.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      No feed sources configured. Click "Add Feed Source" to add an RSS or Atom feed.
                    </td>
                  </tr>
                ) : (
                  feeds.map((feed) => {
                    const isFailing = feed.failure_count > 0;
                    return (
                      <tr key={feed.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="p-3">
                          <div className="font-semibold text-white">{feed.name}</div>
                          <a
                            href={feed.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-slate-500 hover:text-indigo-400 text-[11px] truncate block max-w-sm"
                          >
                            {feed.url}
                          </a>
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                            {feed.category}
                          </span>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-slate-200">{feed.trust_weight}</span>
                            <div className="w-16 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                              <div
                                className="bg-indigo-500 h-full rounded-full"
                                style={{ width: `${feed.trust_weight * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        <td className="p-3">
                          {isFailing ? (
                            <span
                              title={feed.last_error || "Feed failure"}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            >
                              <AlertTriangle className="w-3 h-3" />
                              <span>Failing ({feed.failure_count})</span>
                            </span>
                          ) : feed.last_success_at ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <CheckCircle2 className="w-3 h-3" />
                              <span>Healthy</span>
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400">
                              Untested
                            </span>
                          )}
                        </td>
                        <td className="p-3">
                          <button
                            onClick={() => handleToggleFeed(feed)}
                            className={`w-9 h-5 rounded-full p-0.5 transition-colors ${
                              feed.enabled ? "bg-indigo-600" : "bg-slate-700"
                            }`}
                          >
                            <div
                              className={`w-4 h-4 rounded-full bg-white transition-transform ${
                                feed.enabled ? "translate-x-4" : "translate-x-0"
                              }`}
                            />
                          </button>
                        </td>
                        <td className="p-3 text-right">
                          <button
                            onClick={() => handleDeleteFeed(feed.id, feed.name)}
                            className="p-1.5 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                            title="Delete Source"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Feed Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Rss className="w-4 h-4 text-orange-400" />
                <h3 className="text-sm font-bold text-white">Add RSS/Atom Discovery Source</h3>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddFeed} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Feed Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. OpenAI Research Blog"
                  value={newFeedName}
                  onChange={(e) => setNewFeedName(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Feed URL (RSS or Atom)
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://example.com/feed.xml"
                  value={newFeedUrl}
                  onChange={(e) => setNewFeedUrl(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Category
                  </label>
                  <input
                    type="text"
                    value={newFeedCategory}
                    onChange={(e) => setNewFeedCategory(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Trust Weight ({newFeedTrust})
                  </label>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    value={newFeedTrust}
                    onChange={(e) => setNewFeedTrust(parseFloat(e.target.value))}
                    className="w-full accent-indigo-500 mt-2"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 text-xs rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
                >
                  Save Feed
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
