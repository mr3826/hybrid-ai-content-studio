"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Boxes,
  Plus,
  RefreshCw,
  Clock,
  DollarSign,
  CheckCircle2,
  Archive,
  ArrowRight,
  Sparkles,
  Layers,
  BookOpen,
  FlaskConical,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import {
  ContentFamilyItem,
  listContentFamilies,
  createContentFamily,
  approveContentFamily,
  archiveContentFamily,
  getContentFamilyHealth,
} from "@/lib/api";

const PILLARS = ["Core", "Local Hardware", "Local AI Models", "Hardware Benchmarks", "Tutorials", "Cost Optimization"];

const ORIGINALITY_TYPES = [
  "benchmark",
  "tool_test",
  "cost_comparison",
  "workflow_demonstration",
  "before_after",
  "implementation_attempt",
  "multi_source_synthesis",
  "original_framework",
  "original_chart_data_analysis",
  "practical_tutorial",
  "failure_analysis",
  "clearly_labeled_opinion",
];

function ContentFamiliesContent() {
  const searchParams = useSearchParams();
  const [families, setFamilies] = useState<ContentFamilyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [engineHealth, setEngineHealth] = useState("checking");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterPillar, setFilterPillar] = useState("all");

  // Create Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [title, setTitle] = useState("");
  const [topicId, setTopicId] = useState("");
  const [researchPacketId, setResearchPacketId] = useState("");
  const [originalityPlanId, setOriginalityPlanId] = useState("");
  const [contentPillar, setContentPillar] = useState("Core");
  const [originalValueType, setOriginalValueType] = useState("benchmark");
  const [summary, setSummary] = useState("");
  const [researchCost, setResearchCost] = useState<number>(0.0);
  const [aiCost, setAiCost] = useState<number>(0.0);
  const [manualTime, setManualTime] = useState<number>(0);
  const [submitting, setSubmitting] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  useEffect(() => {
    const pNew = searchParams.get("new");
    const pTitle = searchParams.get("title");
    const pTopicId = searchParams.get("topic_id");
    const pPillar = searchParams.get("pillar");
    const pPacketId = searchParams.get("packet_id");
    const pPlanId = searchParams.get("plan_id");

    if (pNew === "1" || pNew === "true" || pTitle) {
      if (pTitle) setTitle(pTitle);
      if (pTopicId) setTopicId(pTopicId);
      if (pPillar && PILLARS.includes(pPillar)) setContentPillar(pPillar);
      if (pPacketId) setResearchPacketId(pPacketId);
      if (pPlanId) setOriginalityPlanId(pPlanId);
      setShowCreateModal(true);
    }
  }, [searchParams]);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setErrorBanner(null);
    try {
      const [hRes, listRes] = await Promise.all([
        getContentFamilyHealth().catch(() => ({ status: "offline", engine_id: "content_family" })),
        listContentFamilies(),
      ]);
      setEngineHealth(hRes.status);
      setFamilies(listRes);
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to load Content Families.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    setErrorBanner(null);
    try {
      await createContentFamily({
        title,
        content_pillar: contentPillar,
        original_value_type: originalValueType,
        summary,
        topic_id: topicId || undefined,
        research_packet_id: researchPacketId || undefined,
        originality_plan_id: originalityPlanId || undefined,
        research_cost: researchCost,
        ai_cost: aiCost,
        manual_time_minutes: manualTime,
      });
      setShowCreateModal(false);
      setTitle("");
      setTopicId("");
      setResearchPacketId("");
      setOriginalityPlanId("");
      setSummary("");
      setResearchCost(0);
      setAiCost(0);
      setManualTime(0);
      await loadData();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to create Content Family.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleApprove(familyId: string) {
    try {
      await approveContentFamily(familyId);
      await loadData();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to approve family.");
    }
  }

  async function handleArchive(familyId: string) {
    if (!confirm("Are you sure you want to archive this Content Family?")) return;
    try {
      await archiveContentFamily(familyId);
      await loadData();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to archive family.");
    }
  }

  const activeCount = families.filter((f) => f.status === "ACTIVE" || f.status === "READY_FOR_CONTENT").length;
  const totalItemsCount = families.reduce((acc, f) => acc + (f.item_count || 0), 0);
  const totalInvestment = families.reduce((acc, f) => acc + (f.shared_cost || 0), 0);

  const filteredFamilies = families.filter((f) => {
    if (filterStatus !== "all" && f.status !== filterStatus) return false;
    if (filterPillar !== "all" && f.content_pillar !== filterPillar) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Boxes className="w-6 h-6 text-indigo-400" />
              Content Families
            </h1>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                engineHealth === "healthy"
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
              }`}
            >
              Engine: {engineHealth}
            </span>
          </div>
          <p className="text-sm text-slate-400">
            One Research & Empirical Investment &rarr; Multiple Platform-Tailored Child Items.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors shadow-sm shadow-indigo-500/20"
          >
            <Plus className="w-3.5 h-3.5" />
            New Content Family
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {errorBanner && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-sm flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorBanner}</span>
          </div>
          <button onClick={() => setErrorBanner(null)} className="text-xs font-bold text-rose-400">
            Dismiss
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-slate-400 font-medium">Total Content Families</p>
          <p className="text-2xl font-bold text-white mt-1">{families.length}</p>
          <p className="text-[11px] text-slate-500 mt-1">Research investments</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-emerald-400 font-medium">Active / Ready for Content</p>
          <p className="text-2xl font-bold text-emerald-300 mt-1">{activeCount}</p>
          <p className="text-[11px] text-slate-500 mt-1">Approved family plans</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-indigo-400 font-medium">Planned Content Items</p>
          <p className="text-2xl font-bold text-indigo-300 mt-1">{totalItemsCount}</p>
          <p className="text-[11px] text-slate-500 mt-1">Shorts, Longs & Newsletters</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-amber-400 font-medium">Total Shared Investment</p>
          <p className="text-2xl font-bold text-amber-300 mt-1">${totalInvestment.toFixed(2)}</p>
          <p className="text-[11px] text-slate-500 mt-1">Amortized across all children</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-lg border border-slate-800">
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-medium">Status:</span>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-800 text-xs text-slate-200 rounded px-2.5 py-1 border border-slate-700 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Statuses</option>
            <option value="DRAFT">DRAFT</option>
            <option value="READY_FOR_CONTENT">READY_FOR_CONTENT</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="ARCHIVED">ARCHIVED</option>
          </select>

          <span className="text-xs text-slate-400 font-medium ml-2">Pillar:</span>
          <select
            value={filterPillar}
            onChange={(e) => setFilterPillar(e.target.value)}
            className="bg-slate-800 text-xs text-slate-200 rounded px-2.5 py-1 border border-slate-700 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Content Pillars</option>
            {PILLARS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <p className="text-xs text-slate-500">
          Showing {filteredFamilies.length} of {families.length} families
        </p>
      </div>

      {/* Family Cards Grid */}
      {filteredFamilies.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl bg-slate-900/20">
          <Boxes className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400 font-medium">No Content Families found.</p>
          <p className="text-xs text-slate-500 mt-1">
            Create a family to link research, evidence, and experiments to multiple child assets.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredFamilies.map((fam) => (
            <div
              key={fam.id}
              className={`p-5 rounded-xl border transition-all ${
                fam.status === "READY_FOR_CONTENT"
                  ? "bg-slate-900/80 border-emerald-500/30"
                  : fam.status === "ARCHIVED"
                  ? "bg-slate-950/40 border-slate-800/50 opacity-75"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      {fam.content_pillar}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 uppercase font-mono">
                      {fam.original_value_type}
                    </span>

                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        fam.status === "READY_FOR_CONTENT"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : fam.status === "ARCHIVED"
                          ? "bg-slate-800 text-slate-400 border border-slate-700"
                          : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      }`}
                    >
                      {fam.status}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-white leading-tight">{fam.title}</h3>
                  {fam.summary && <p className="text-xs text-slate-300 leading-relaxed">{fam.summary}</p>}

                  {/* Factual Dependencies Pills */}
                  <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-400 flex-wrap">
                    {fam.research_packet_id ? (
                      <span className="flex items-center gap-1 text-emerald-400">
                        <BookOpen className="w-3 h-3" />
                        Research Linked
                      </span>
                    ) : (
                      <span className="text-slate-500">No Research Packet</span>
                    )}

                    {fam.originality_plan_id ? (
                      <span className="flex items-center gap-1 text-indigo-400">
                        <FlaskConical className="w-3 h-3" />
                        Originality Plan Linked
                      </span>
                    ) : (
                      <span className="text-slate-500">No Originality Plan</span>
                    )}

                    {fam.primary_experiment_id ? (
                      <span className="flex items-center gap-1 text-amber-400">
                        <ShieldCheck className="w-3 h-3" />
                        Experiment Linked
                      </span>
                    ) : null}
                  </div>
                </div>

                {/* Economics and Actions */}
                <div className="flex flex-col md:items-end justify-between gap-3 shrink-0">
                  <div className="text-right">
                    <p className="text-xs text-slate-400 font-medium">
                      {fam.item_count} Child Items Planned
                    </p>
                    <p className="text-sm font-bold text-white mt-0.5">
                      ${fam.shared_cost.toFixed(2)}{" "}
                      <span className="text-[11px] font-normal text-slate-500">shared investment</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {fam.status !== "READY_FOR_CONTENT" && fam.status !== "ARCHIVED" && (
                      <button
                        onClick={() => handleApprove(fam.id)}
                        className="px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/30 transition-colors flex items-center gap-1"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Approve Plan
                      </button>
                    )}

                    {fam.status !== "ARCHIVED" && (
                      <button
                        onClick={() => handleArchive(fam.id)}
                        className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
                        title="Archive Family"
                      >
                        <Archive className="w-4 h-4" />
                      </button>
                    )}

                    <Link
                      href={`/content-families/${fam.id}`}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors shadow-sm"
                    >
                      Open Workspace
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CREATE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Boxes className="w-5 h-5 text-indigo-400" />
                Create New Content Family
              </h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Family Title *
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Gemini 2.0 vs Qwen 2.5 Coding Benchmark"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Content Pillar
                  </label>
                  <select
                    value={contentPillar}
                    onChange={(e) => setContentPillar(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  >
                    {PILLARS.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Originality Value Type
                  </label>
                  <select
                    value={originalValueType}
                    onChange={(e) => setOriginalValueType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  >
                    {ORIGINALITY_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Empirical Summary & Key Finding
                </label>
                <textarea
                  rows={3}
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  placeholder="Core research conclusion and 'What are WE adding?' that all child items will share."
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Research Cost ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={researchCost}
                    onChange={(e) => setResearchCost(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    AI Cost ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={aiCost}
                    onChange={(e) => setAiCost(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Manual Time (mins)
                  </label>
                  <input
                    type="number"
                    value={manualTime}
                    onChange={(e) => setManualTime(parseInt(e.target.value, 10) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
                >
                  {submitting ? "Creating..." : "Create Family"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ContentFamiliesPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500">Loading Content Families...</div>}>
      <ContentFamiliesContent />
    </Suspense>
  );
}
