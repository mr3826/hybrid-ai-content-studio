"use client";

import { useEffect, useState } from "react";
import {
  FlaskConical,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Plus,
  RefreshCw,
  FileCode,
  Image as ImageIcon,
  FileText,
  Clock,
  DollarSign,
  ShieldCheck,
  ChevronRight,
  Terminal,
  Layers,
  HelpCircle,
  ExternalLink,
  UploadCloud,
} from "lucide-react";
import {
  OriginalityFormat,
  OriginalityAngle,
  OriginalityPlan,
  ExperimentItem,
  getOriginalityFormats,
  getOriginalityHealth,
  listOriginalityPlans,
  createOriginalityPlan,
  approveOriginalityPlan,
  rejectOriginalityPlan,
  proposeOriginalAngles,
  listWorkspaceExperiments,
  createWorkspaceExperiment,
  addExperimentAttachment,
  linkExperimentEvidence,
} from "@/lib/api";

export default function OriginalityPage() {
  const [activeTab, setActiveTab] = useState<"plans" | "experiments" | "formats">("plans");
  const [loading, setLoading] = useState(true);
  const [engineHealth, setEngineHealth] = useState<string>("checking");
  const [plans, setPlans] = useState<OriginalityPlan[]>([]);
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [formats, setFormats] = useState<OriginalityFormat[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterFormat, setFilterFormat] = useState<string>("all");

  // Modals & Forms
  const [showNewPlanModal, setShowNewPlanModal] = useState(false);
  const [planTopic, setPlanTopic] = useState("");
  const [planType, setPlanType] = useState("tool_test");
  const [planAdding, setPlanAdding] = useState("");
  const [planMatters, setPlanMatters] = useState("");

  const [showProposeModal, setShowProposeModal] = useState(false);
  const [proposeTopic, setProposeTopic] = useState("");
  const [proposeSummary, setProposeSummary] = useState("");
  const [proposedAngles, setProposedAngles] = useState<OriginalityAngle[]>([]);
  const [proposing, setProposing] = useState(false);

  const [showNewExpModal, setShowNewExpModal] = useState(false);
  const [expPlanId, setExpPlanId] = useState("");
  const [expTitle, setExpTitle] = useState("");
  const [expQuestion, setExpQuestion] = useState("");
  const [expHypothesis, setExpHypothesis] = useState("");
  const [expMethod, setExpMethod] = useState("");
  const [expDataset, setExpDataset] = useState("");
  const [expTools, setExpTools] = useState("");
  const [expResults, setExpResults] = useState("");
  const [expFailures, setExpFailures] = useState("");
  const [expLatency, setExpLatency] = useState<number>(0);
  const [expCost, setExpCost] = useState<number>(0);
  const [expConclusion, setExpConclusion] = useState("");

  const [showAttachModal, setShowAttachModal] = useState(false);
  const [selectedExpId, setSelectedExpId] = useState<string>("");
  const [attachType, setAttachType] = useState("json");
  const [attachFilename, setAttachFilename] = useState("");
  const [attachFilePath, setAttachFilePath] = useState("");
  const [attachSnippet, setAttachSnippet] = useState("");
  const [attachCaption, setAttachCaption] = useState("");

  const [showLinkEvidenceModal, setShowLinkEvidenceModal] = useState(false);
  const [linkExpId, setLinkExpId] = useState("");
  const [evidenceConclusionText, setEvidenceConclusionText] = useState("");
  const [evidenceConfidence, setEvidenceConfidence] = useState(0.95);

  const [actionLoading, setActionLoading] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    setErrorBanner(null);
    try {
      const [hRes, fRes, pRes, eRes] = await Promise.all([
        getOriginalityHealth().catch(() => ({ status: "offline", engine_id: "originality" })),
        getOriginalityFormats().catch(() => ({ formats: [], count: 0 })),
        listOriginalityPlans(),
        listWorkspaceExperiments(),
      ]);
      setEngineHealth(hRes.status);
      setFormats(fRes.formats);
      setPlans(pRes);
      setExperiments(eRes);
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to load originality data.");
    } finally {
      setLoading(false);
    }
  }

  // Handle Plan Creation
  async function handleCreatePlan(e: React.FormEvent) {
    e.preventDefault();
    setActionLoading(true);
    setErrorBanner(null);
    try {
      const created = await createOriginalityPlan({
        topic: planTopic,
        originality_type: planType,
        what_are_we_adding: planAdding,
        why_it_matters: planMatters,
      });
      setShowNewPlanModal(false);
      setPlanTopic("");
      setPlanAdding("");
      setPlanMatters("");
      await loadAll();
      if (created.is_generic_summary) {
        setErrorBanner(
          `Notice: Plan created but flagged as 'Generic Summary' (Status: NOT READY). It cannot be approved until hands-on empirical value is defined.`
        );
      }
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to create originality plan.");
    } finally {
      setActionLoading(false);
    }
  }

  // Handle Plan Approval
  async function handleApprove(planId: string) {
    setActionLoading(true);
    setErrorBanner(null);
    try {
      await approveOriginalityPlan(planId, {
        reviewer: "creator",
        notes: "Approved human contribution gate for production studio.",
      });
      await loadAll();
    } catch (err: any) {
      setErrorBanner(err?.message || "Approval failed.");
    } finally {
      setActionLoading(false);
    }
  }

  // Handle Plan Rejection
  async function handleReject(planId: string) {
    const reason = prompt("Enter rejection reason (e.g. lacks empirical test or original benchmark):");
    if (!reason) return;
    setActionLoading(true);
    setErrorBanner(null);
    try {
      await rejectOriginalityPlan(planId, reason);
      await loadAll();
    } catch (err: any) {
      setErrorBanner(err?.message || "Rejection failed.");
    } finally {
      setActionLoading(false);
    }
  }

  // Handle Propose Angles
  async function handleProposeAngles(e: React.FormEvent) {
    e.preventDefault();
    if (!proposeTopic.trim()) return;
    setProposing(true);
    setErrorBanner(null);
    try {
      const res = await proposeOriginalAngles(proposeTopic, proposeSummary);
      setProposedAngles(res.angles);
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to propose originality angles.");
    } finally {
      setProposing(false);
    }
  }

  function applyProposedAngle(angle: OriginalityAngle) {
    setPlanTopic(proposeTopic);
    setPlanType(angle.originality_type);
    setPlanAdding(angle.what_are_we_adding);
    setPlanMatters(angle.why_it_matters);
    setShowProposeModal(false);
    setShowNewPlanModal(true);
  }

  // Handle Experiment Creation
  async function handleCreateExperiment(e: React.FormEvent) {
    e.preventDefault();
    setActionLoading(true);
    setErrorBanner(null);
    try {
      let parsedResults = {};
      if (expResults.trim()) {
        try {
          parsedResults = JSON.parse(expResults);
        } catch {
          parsedResults = { raw_output: expResults };
        }
      }

      const toolsList = expTools
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      const failuresList = expFailures
        .split("\n")
        .map((f) => f.trim())
        .filter(Boolean);

      await createWorkspaceExperiment({
        title: expTitle,
        question: expQuestion || expTitle,
        hypothesis: expHypothesis,
        method: expMethod,
        dataset_sample: expDataset,
        tools_models: toolsList,
        results: parsedResults,
        failures: failuresList,
        latency_ms: expLatency,
        cost_usd: expCost,
        conclusion: expConclusion,
        status: "completed",
        originality_plan_id: expPlanId || undefined,
      });

      setShowNewExpModal(false);
      setExpTitle("");
      setExpQuestion("");
      setExpHypothesis("");
      setExpMethod("");
      setExpDataset("");
      setExpTools("");
      setExpResults("");
      setExpFailures("");
      setExpConclusion("");
      setExpPlanId("");
      await loadAll();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to create experiment.");
    } finally {
      setActionLoading(false);
    }
  }

  // Handle Attachment
  async function handleAddAttachment(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedExpId) return;
    setActionLoading(true);
    setErrorBanner(null);
    try {
      await addExperimentAttachment(selectedExpId, {
        attachment_type: attachType,
        filename: attachFilename,
        file_path: attachFilePath || `/data/experiments/${attachFilename}`,
        content_snippet: attachSnippet || undefined,
        caption: attachCaption || undefined,
      });
      setShowAttachModal(false);
      setAttachFilename("");
      setAttachFilePath("");
      setAttachSnippet("");
      setAttachCaption("");
      await loadAll();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to attach file.");
    } finally {
      setActionLoading(false);
    }
  }

  // Handle Link Evidence
  async function handleLinkEvidence(e: React.FormEvent) {
    e.preventDefault();
    if (!linkExpId || !evidenceConclusionText.trim()) return;
    setActionLoading(true);
    setErrorBanner(null);
    try {
      await linkExperimentEvidence(linkExpId, {
        conclusion_text: evidenceConclusionText,
        confidence: evidenceConfidence,
      });
      setShowLinkEvidenceModal(false);
      setEvidenceConclusionText("");
      await loadAll();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to link evidence.");
    } finally {
      setActionLoading(false);
    }
  }

  // Stats
  const approvedPlansCount = plans.filter((p) => p.status === "approved").length;
  const quarantinedPlansCount = plans.filter((p) => p.is_generic_summary || p.status === "not_ready").length;
  const filteredPlans = plans.filter((p) => {
    if (filterStatus !== "all") {
      if (filterStatus === "quarantined") {
        if (!p.is_generic_summary && p.status !== "not_ready") return false;
      } else if (p.status !== filterStatus) {
        return false;
      }
    }
    if (filterFormat !== "all" && p.originality_type !== filterFormat) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <FlaskConical className="w-6 h-6 text-indigo-400" />
              Originality & Experiment Workspace
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
            Mandatory Channel Contribution Gate: Every video must explicitly answer{" "}
            <span className="font-semibold text-indigo-300">"What are WE adding?"</span> Generic news summaries are blocked.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowProposeModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Propose 3 Angles
          </button>
          <button
            onClick={() => setShowNewPlanModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors shadow-sm shadow-indigo-500/20"
          >
            <Plus className="w-3.5 h-3.5" />
            New Originality Plan
          </button>
          <button
            onClick={() => setShowNewExpModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors border border-slate-700"
          >
            <FlaskConical className="w-3.5 h-3.5" />
            New Experiment
          </button>
          <button
            onClick={loadAll}
            disabled={loading}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Error / Alert Banner */}
      {errorBanner && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-sm flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-amber-400 hover:text-amber-200 text-xs font-bold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-slate-400 font-medium">Total Originality Plans</p>
          <p className="text-2xl font-bold text-white mt-1">{plans.length}</p>
          <p className="text-[11px] text-slate-500 mt-1">Structured contribution definitions</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-emerald-400 font-medium">Approved Plans</p>
          <p className="text-2xl font-bold text-emerald-300 mt-1">{approvedPlansCount}</p>
          <p className="text-[11px] text-slate-500 mt-1">Human quality gate approved</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-rose-400 font-medium">Generic Summary Quarantine</p>
          <p className="text-2xl font-bold text-rose-300 mt-1">{quarantinedPlansCount}</p>
          <p className="text-[11px] text-slate-500 mt-1">Status: NOT READY (Blocked)</p>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-xs text-indigo-400 font-medium">Experiment Workspace</p>
          <p className="text-2xl font-bold text-indigo-300 mt-1">{experiments.length}</p>
          <p className="text-[11px] text-slate-500 mt-1">Empirical runs & benchmarks</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 overflow-x-auto no-scrollbar whitespace-nowrap">
        <button
          onClick={() => setActiveTab("plans")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "plans"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-4 h-4" />
          "What are WE adding?" Plans ({plans.length})
        </button>
        <button
          onClick={() => setActiveTab("experiments")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "experiments"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FlaskConical className="w-4 h-4" />
          Experiment Workspace ({experiments.length})
        </button>
        <button
          onClick={() => setActiveTab("formats")}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "formats"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <HelpCircle className="w-4 h-4" />
          12 Originality Formats ({formats.length})
        </button>
      </div>

      {/* TAB 1: PLANS */}
      {activeTab === "plans" && (
        <div className="space-y-4">
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
                <option value="approved">Approved</option>
                <option value="needs_review">Needs Review</option>
                <option value="quarantined">Quarantined (Generic Summary)</option>
                <option value="rejected">Rejected</option>
              </select>

              <span className="text-xs text-slate-400 font-medium ml-2">Format:</span>
              <select
                value={filterFormat}
                onChange={(e) => setFilterFormat(e.target.value)}
                className="bg-slate-800 text-xs text-slate-200 rounded px-2.5 py-1 border border-slate-700 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All 12 Formats</option>
                {formats.map((f) => (
                  <option key={f.type} value={f.type}>
                    {f.title}
                  </option>
                ))}
              </select>
            </div>

            <p className="text-xs text-slate-500">
              Showing {filteredPlans.length} of {plans.length} plans
            </p>
          </div>

          {/* Plans Grid */}
          {filteredPlans.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl bg-slate-900/20">
              <FlaskConical className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 font-medium">No originality plans match the current filters.</p>
              <p className="text-xs text-slate-500 mt-1">
                Create a plan or propose 3 original angles from any trending topic.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {filteredPlans.map((plan) => {
                const isQuarantined = plan.is_generic_summary || plan.status === "not_ready";
                return (
                  <div
                    key={plan.id}
                    className={`p-5 rounded-xl border transition-all ${
                      isQuarantined
                        ? "bg-rose-950/10 border-rose-800/40"
                        : plan.status === "approved"
                        ? "bg-slate-900/70 border-emerald-500/30"
                        : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-3 mb-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-wide">
                            {plan.originality_type.replace(/_/g, " ")}
                          </span>

                          {isQuarantined ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" />
                              NOT READY (Generic Summary Quarantined)
                            </span>
                          ) : plan.status === "approved" ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              Approved by {plan.reviewed_by || "creator"}
                            </span>
                          ) : plan.status === "rejected" ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-red-500/10 text-red-400 border border-red-500/20 flex items-center gap-1">
                              <XCircle className="w-3 h-3" />
                              Rejected
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              Needs Review
                            </span>
                          )}

                          <span className="text-[11px] text-slate-500">
                            Confidence: {Math.round(plan.confidence_score)}%
                          </span>
                        </div>

                        <h3 className="text-base font-semibold text-white">{plan.topic}</h3>
                        <p className="text-xs text-slate-500 font-mono mt-0.5">slug: {plan.slug}</p>
                      </div>

                      {/* Human Gate Action Buttons */}
                      <div className="flex items-center gap-2 shrink-0">
                        {plan.status !== "approved" && (
                          <button
                            onClick={() => handleApprove(plan.id)}
                            disabled={isQuarantined || actionLoading}
                            title={
                              isQuarantined
                                ? "Generic summaries cannot be approved under studio invariants"
                                : "Approve originality contribution"
                            }
                            className={`flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                              isQuarantined
                                ? "bg-slate-800/60 text-slate-500 cursor-not-allowed border border-slate-700/50"
                                : "bg-emerald-600 text-white hover:bg-emerald-500 shadow-sm shadow-emerald-600/20"
                            }`}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Approve
                          </button>
                        )}

                        {plan.status !== "rejected" && (
                          <button
                            onClick={() => handleReject(plan.id)}
                            disabled={actionLoading}
                            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 text-rose-300 hover:bg-slate-700 border border-slate-700"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            Reject
                          </button>
                        )}

                        <button
                          onClick={() => {
                            setExpPlanId(plan.id);
                            setExpTitle(`Experiment: ${plan.topic}`);
                            setExpQuestion(`Testing original contribution for: ${plan.topic}`);
                            setExpHypothesis(plan.what_are_we_adding);
                            setShowNewExpModal(true);
                          }}
                          className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/30"
                        >
                          <FlaskConical className="w-3.5 h-3.5" />
                          Run Experiment
                        </button>
                      </div>
                    </div>

                    {/* What are WE adding? Card Highlight */}
                    <div className="mt-3 p-3.5 rounded-lg bg-slate-950/60 border border-slate-800">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-400 mb-1 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                        What are WE adding?
                      </p>
                      <p className="text-sm text-slate-200 leading-relaxed font-medium">
                        {plan.what_are_we_adding}
                      </p>

                      {plan.why_it_matters && (
                        <div className="mt-2 pt-2 border-t border-slate-800/80">
                          <p className="text-[11px] text-slate-400">
                            <span className="font-semibold text-slate-300">Why it matters: </span>
                            {plan.why_it_matters}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Quarantine Warning */}
                    {isQuarantined && (
                      <div className="mt-3 p-2.5 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                        <span>
                          Studio Policy: Generic summaries lack empirical channel contribution and cannot proceed into script generation.
                          Add specific hardware tests, benchmarks, failure analysis, or code tutorials to pass quality gates.
                        </span>
                      </div>
                    )}

                    {/* Review Notes */}
                    {plan.review_notes && (
                      <div className="mt-3 text-xs text-slate-400 bg-slate-950/40 p-2.5 rounded border border-slate-800/60">
                        <span className="font-semibold text-slate-300">Review Notes: </span>
                        {plan.review_notes}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: EXPERIMENT WORKSPACE */}
      {activeTab === "experiments" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900/40 p-3 rounded-lg border border-slate-800">
            <div>
              <p className="text-xs text-slate-400 font-medium">
                Structured reproducible test harness runs, benchmarks, latency measurements, and evidence attachments.
              </p>
            </div>
            <button
              onClick={() => setShowNewExpModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              New Experiment
            </button>
          </div>

          {experiments.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl bg-slate-900/20">
              <FlaskConical className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 font-medium">No experiments recorded in workspace.</p>
              <p className="text-xs text-slate-500 mt-1">
                Log a benchmark, model latency test, or tool run with attachments.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {experiments.map((exp) => (
                <div
                  key={exp.id}
                  className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all"
                >
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-3 mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase">
                          {exp.status}
                        </span>
                        {exp.latency_ms ? (
                          <span className="text-[11px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded flex items-center gap-1 border border-indigo-500/20">
                            <Clock className="w-3 h-3" />
                            {exp.latency_ms.toFixed(1)} ms
                          </span>
                        ) : null}
                        {exp.cost_usd !== undefined && exp.cost_usd > 0 ? (
                          <span className="text-[11px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded flex items-center gap-1 border border-amber-500/20">
                            <DollarSign className="w-3 h-3" />${exp.cost_usd.toFixed(4)}
                          </span>
                        ) : (
                          <span className="text-[11px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                            $0.00 (Local Hardware)
                          </span>
                        )}
                      </div>

                      <h3 className="text-base font-semibold text-white">{exp.title}</h3>
                      {exp.question && (
                        <p className="text-xs text-slate-400 mt-1">
                          <span className="font-semibold text-slate-300">Question: </span>
                          {exp.question}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => {
                          setSelectedExpId(exp.id);
                          setShowAttachModal(true);
                        }}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700"
                      >
                        <UploadCloud className="w-3.5 h-3.5" />
                        Add Attachment
                      </button>
                      <button
                        onClick={() => {
                          setLinkExpId(exp.id);
                          setEvidenceConclusionText(
                            exp.conclusion || `${exp.title}: Confirmed hypothesis empirically.`
                          );
                          setShowLinkEvidenceModal(true);
                        }}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/30"
                      >
                        <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                        Link to Evidence
                      </button>
                    </div>
                  </div>

                  {/* Core Experiment Methodology Details */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 text-xs">
                    <div className="p-3 rounded bg-slate-950/60 border border-slate-800/80">
                      <p className="font-semibold text-slate-300 mb-1">Hypothesis</p>
                      <p className="text-slate-400">{exp.hypothesis}</p>
                    </div>
                    <div className="p-3 rounded bg-slate-950/60 border border-slate-800/80">
                      <p className="font-semibold text-slate-300 mb-1">Method</p>
                      <p className="text-slate-400">{exp.method}</p>
                    </div>
                  </div>

                  {/* Tools / Models Chips */}
                  {exp.tools_models && exp.tools_models.length > 0 && (
                    <div className="mt-3 flex items-center gap-1.5 flex-wrap">
                      <span className="text-[11px] text-slate-500 font-medium">Tools/Models:</span>
                      {exp.tools_models.map((tool, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-300 border border-slate-700 font-mono"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Observed Results & Failures */}
                  {exp.results && Object.keys(exp.results).length > 0 && (
                    <div className="mt-3 p-3 rounded bg-slate-950/80 border border-slate-800 font-mono text-xs">
                      <p className="font-sans font-semibold text-emerald-400 mb-1 flex items-center gap-1">
                        <Terminal className="w-3.5 h-3.5" />
                        Results & Empirical Metrics
                      </p>
                      <pre className="text-slate-300 overflow-x-auto text-[11px]">
                        {JSON.stringify(exp.results, null, 2)}
                      </pre>
                    </div>
                  )}

                  {exp.failures && exp.failures.length > 0 && (
                    <div className="mt-3 p-3 rounded bg-rose-950/20 border border-rose-800/40 text-xs">
                      <p className="font-semibold text-rose-400 mb-1 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                        Documented Failures & Limitations
                      </p>
                      <ul className="list-disc list-inside space-y-0.5 text-rose-200 text-[11px]">
                        {exp.failures.map((f, i) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Conclusion */}
                  {exp.conclusion && (
                    <div className="mt-3 p-2.5 rounded bg-indigo-950/20 border border-indigo-500/20 text-xs text-indigo-200">
                      <span className="font-semibold text-indigo-300">Empirical Conclusion: </span>
                      {exp.conclusion}
                    </div>
                  )}

                  {/* Attachments Section */}
                  {exp.attachments && exp.attachments.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-800">
                      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Attachments ({exp.attachments.length})
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {exp.attachments.map((att) => (
                          <div
                            key={att.id}
                            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300"
                          >
                            {att.attachment_type === "csv" || att.attachment_type === "json" ? (
                              <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                            ) : att.attachment_type === "screenshot" || att.attachment_type === "image" ? (
                              <ImageIcon className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <FileText className="w-3.5 h-3.5 text-amber-400" />
                            )}
                            <span className="font-mono text-[11px]">{att.filename}</span>
                            {att.caption && <span className="text-slate-500 text-[10px]">({att.caption})</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Linked Evidence Conclusions */}
                  {exp.conclusions && exp.conclusions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-800">
                      <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        Evidence Engine Linked Claims ({exp.conclusions.length})
                      </p>
                      <div className="space-y-1.5">
                        {exp.conclusions.map((c) => (
                          <div
                            key={c.id}
                            className="p-2 rounded bg-emerald-950/20 border border-emerald-500/20 text-xs text-emerald-200 flex items-center justify-between"
                          >
                            <span>{c.summary}</span>
                            <span className="text-[10px] text-emerald-400 font-mono">
                              {(c.confidence * 100).toFixed(0)}% confidence
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: 12 ORIGINALITY FORMATS */}
      {activeTab === "formats" && (
        <div className="space-y-4">
          <div className="bg-slate-900/40 p-4 rounded-lg border border-slate-800">
            <h2 className="text-sm font-semibold text-white mb-1">
              The 12 Recognized Studio Originality Formats
            </h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              To guarantee that every video script provides net-new empirical value to our audience, topics must adopt at least one of these 12 recognized originality formats. Generic article aggregations or news summaries default to <span className="text-rose-400 font-semibold">NOT READY</span>.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {formats.map((fmt) => (
              <div
                key={fmt.type}
                className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col justify-between hover:border-indigo-500/40 transition-all"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <h3 className="text-sm font-bold text-white">{fmt.title}</h3>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      {fmt.type}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">{fmt.description}</p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    Channel Original
                  </span>
                  <button
                    onClick={() => {
                      setPlanType(fmt.type);
                      setShowNewPlanModal(true);
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    Draft with this format &rarr;
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL: NEW ORIGINALITY PLAN */}
      {showNewPlanModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <FlaskConical className="w-5 h-5 text-indigo-400" />
                Define Channel Contribution Plan
              </h2>
              <button
                onClick={() => setShowNewPlanModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreatePlan} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Topic / Title *
                </label>
                <input
                  type="text"
                  required
                  value={planTopic}
                  onChange={(e) => setPlanTopic(e.target.value)}
                  placeholder="e.g. DeepSeek-R1-Distill-14B on 16GB M4 Mac"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Originality Format *
                </label>
                <select
                  value={planType}
                  onChange={(e) => setPlanType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  {formats.map((fmt) => (
                    <option key={fmt.type} value={fmt.type}>
                      {fmt.title} ({fmt.type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-bold text-indigo-300 uppercase tracking-wide">
                    What are WE adding? *
                  </label>
                  <span className="text-[10px] text-slate-500">Minimum 15 characters, no generic summaries</span>
                </div>
                <textarea
                  required
                  rows={3}
                  value={planAdding}
                  onChange={(e) => setPlanAdding(e.target.value)}
                  placeholder="e.g. Hands-on token speed benchmarks, VRAM saturation curves at 32k context, and failure recovery scripts."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Rule: Do not summarize existing news. State the exact empirical test, code asset, or benchmark data our studio contributes.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Why it matters to viewers (Optional)
                </label>
                <input
                  type="text"
                  value={planMatters}
                  onChange={(e) => setPlanMatters(e.target.value)}
                  placeholder="e.g. Viewers avoid buying incompatible RAM configurations."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowNewPlanModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
                >
                  {actionLoading ? "Submitting..." : "Save Originality Plan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: PROPOSE 3 ANGLES */}
      {showProposeModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                Propose 3 Original Contribution Angles
              </h2>
              <button
                onClick={() => setShowProposeModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleProposeAngles} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Topic or Headline *
                </label>
                <input
                  type="text"
                  required
                  value={proposeTopic}
                  onChange={(e) => setProposeTopic(e.target.value)}
                  placeholder="e.g. Llama 3 8B Local Fine-tuning"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Context / Summary (Optional)
                </label>
                <input
                  type="text"
                  value={proposeSummary}
                  onChange={(e) => setProposeSummary(e.target.value)}
                  placeholder="Background notes from research packet or RSS feed"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={proposing}
                className="w-full py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm flex items-center justify-center gap-2"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {proposing ? "Generating Empirical Angles..." : "Generate 3 Angles"}
              </button>
            </form>

            {/* Proposed Angles Results */}
            {proposedAngles.length > 0 && (
              <div className="space-y-3 pt-3 border-t border-slate-800">
                <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Generated Angles ({proposedAngles.length})
                </p>
                <div className="space-y-2.5">
                  {proposedAngles.map((angle, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-indigo-500/40 transition-all flex flex-col justify-between gap-2"
                    >
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            {angle.originality_type.replace(/_/g, " ")}
                          </span>
                        </div>
                        <p className="text-xs font-medium text-slate-200">
                          <span className="text-indigo-400 font-semibold">Adding: </span>
                          {angle.what_are_we_adding}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-1">
                          <span className="text-slate-300 font-semibold">Why it matters: </span>
                          {angle.why_it_matters}
                        </p>
                      </div>

                      <div className="flex justify-end">
                        <button
                          onClick={() => applyProposedAngle(angle)}
                          className="px-3 py-1 text-xs font-semibold rounded bg-indigo-600/30 text-indigo-300 hover:bg-indigo-600 hover:text-white transition-colors"
                        >
                          Use this Angle &rarr;
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL: NEW EXPERIMENT */}
      {showNewExpModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <FlaskConical className="w-5 h-5 text-indigo-400" />
                Record Empirical Experiment Run
              </h2>
              <button
                onClick={() => setShowNewExpModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateExperiment} className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Experiment Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={expTitle}
                    onChange={(e) => setExpTitle(e.target.value)}
                    placeholder="e.g. Throughput Benchmark Ollama vs vLLM"
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Inquiry Question *
                  </label>
                  <input
                    type="text"
                    value={expQuestion}
                    onChange={(e) => setExpQuestion(e.target.value)}
                    placeholder="e.g. Does vLLM outperform Ollama on local unified memory?"
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Hypothesis *
                </label>
                <input
                  type="text"
                  required
                  value={expHypothesis}
                  onChange={(e) => setExpHypothesis(e.target.value)}
                  placeholder="e.g. Ollama has higher single-user throughput on Apple Silicon Metal."
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Reproduction Method *
                </label>
                <textarea
                  required
                  rows={2}
                  value={expMethod}
                  onChange={(e) => setExpMethod(e.target.value)}
                  placeholder="e.g. Ran 5 concurrent requests with 2048 prompt tokens across 3 iterations."
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Tools / Models Tested (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={expTools}
                    onChange={(e) => setExpTools(e.target.value)}
                    placeholder="e.g. Ollama v0.5.4, llama.cpp, DeepSeek-14B"
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Dataset / Input Sample
                  </label>
                  <input
                    type="text"
                    value={expDataset}
                    onChange={(e) => setExpDataset(e.target.value)}
                    placeholder="e.g. 50 GSM8k reasoning prompts"
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Measured Latency (ms)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={expLatency}
                    onChange={(e) => setExpLatency(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Cost ($ USD)
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    value={expCost}
                    onChange={(e) => setExpCost(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Empirical Results (JSON or key/values)
                </label>
                <textarea
                  rows={2}
                  value={expResults}
                  onChange={(e) => setExpResults(e.target.value)}
                  placeholder='{"ollama_tps": 42.1, "llamacpp_tps": 48.6}'
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Failures & Roadblocks (1 per line)
                </label>
                <textarea
                  rows={2}
                  value={expFailures}
                  onChange={(e) => setExpFailures(e.target.value)}
                  placeholder="e.g. Context window spilled to swap memory at 32k"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Conclusion
                </label>
                <input
                  type="text"
                  value={expConclusion}
                  onChange={(e) => setExpConclusion(e.target.value)}
                  placeholder="e.g. llama.cpp is 15% faster for batch tasks, while Ollama has lower memory footprint."
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowNewExpModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
                >
                  {actionLoading ? "Saving..." : "Record Experiment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD ATTACHMENT */}
      {showAttachModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-indigo-400" />
                Attach File to Experiment
              </h2>
              <button
                onClick={() => setShowAttachModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleAddAttachment} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Attachment Type *
                </label>
                <select
                  value={attachType}
                  onChange={(e) => setAttachType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                >
                  <option value="json">JSON Metrics Data</option>
                  <option value="csv">CSV Benchmark Logs</option>
                  <option value="screenshot">Screenshot / Image</option>
                  <option value="terminal_output">Terminal Output / Log</option>
                  <option value="code_snippet">Code Snippet / Config</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Filename *
                </label>
                <input
                  type="text"
                  required
                  value={attachFilename}
                  onChange={(e) => setAttachFilename(e.target.value)}
                  placeholder="e.g. latency_benchmark.csv"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Local File Path
                </label>
                <input
                  type="text"
                  value={attachFilePath}
                  onChange={(e) => setAttachFilePath(e.target.value)}
                  placeholder="/data/experiments/latency_benchmark.csv"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Content Preview / Snippet
                </label>
                <textarea
                  rows={2}
                  value={attachSnippet}
                  onChange={(e) => setAttachSnippet(e.target.value)}
                  placeholder="First few lines of the CSV or terminal output"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Caption / Notes
                </label>
                <input
                  type="text"
                  value={attachCaption}
                  onChange={(e) => setAttachCaption(e.target.value)}
                  placeholder="e.g. Log of 5 iterations with context size 4096"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAttachModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
                >
                  {actionLoading ? "Saving..." : "Save Attachment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: LINK TO EVIDENCE ENGINE */}
      {showLinkEvidenceModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-indigo-400" />
                Link Experiment to Evidence Engine
              </h2>
              <button
                onClick={() => setShowLinkEvidenceModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleLinkEvidence} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Empirical Conclusion Statement *
                </label>
                <textarea
                  required
                  rows={3}
                  value={evidenceConclusionText}
                  onChange={(e) => setEvidenceConclusionText(e.target.value)}
                  placeholder="e.g. Tests verify that local llama.cpp achieves 48 tokens/s on M4 Max with 0 dropped frames."
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Confidence Score (0.0 to 1.0)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.1"
                  max="1.0"
                  value={evidenceConfidence}
                  onChange={(e) => setEvidenceConfidence(parseFloat(e.target.value) || 0.95)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <p className="text-[11px] text-slate-400 leading-relaxed bg-slate-950 p-2.5 rounded border border-slate-800">
                This conclusion will be written into the Evidence Engine graph. Video scripts can directly reference this empirical experiment as primary provenance for factual claims.
              </p>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowLinkEvidenceModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
                >
                  {actionLoading ? "Linking..." : "Link Evidence"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
