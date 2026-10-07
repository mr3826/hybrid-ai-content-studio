"use client";

import { useEffect, useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Layers,
  FlaskConical,
  Link2,
  FileText,
  Plus,
  RefreshCw,
  GitBranch,
  Quote,
  Activity,
  Tag,
  AlertCircle,
  HelpCircle,
  Clock,
  Sparkles,
} from "lucide-react";
import {
  Claim,
  CoverageReport,
  Experiment,
  ProvenanceTrace,
  listClaims,
  getEvidenceCoverage,
  getClaimProvenance,
  linkSourceEvidence,
  labelClaimOpinion,
  listExperiments,
  createClaim,
  createExperiment,
  addExperimentRun,
  addConclusion,
} from "@/lib/api";

export default function EvidencePage() {
  const [coverage, setCoverage] = useState<CoverageReport | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"claims" | "provenance" | "experiments">("claims");
  const [filterType, setFilterType] = useState<string>("all");

  // Selected claim for provenance inspection
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [provenanceTrace, setProvenanceTrace] = useState<ProvenanceTrace | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);

  // Modals state
  const [linkSourceModalClaim, setLinkSourceModalClaim] = useState<Claim | null>(null);
  const [sourceUrl, setSourceUrl] = useState("");
  const [sourceTitle, setSourceTitle] = useState("");
  const [sourceQuote, setSourceQuote] = useState("");
  const [sourceType, setSourceType] = useState("primary");
  const [sourceTrust, setSourceTrust] = useState(1.0);
  const [submittingAction, setSubmittingAction] = useState(false);

  // New claim modal
  const [showNewClaimModal, setShowNewClaimModal] = useState(false);
  const [newClaimText, setNewClaimText] = useState("");
  const [newClaimType, setNewClaimType] = useState<any>("external_fact");

  // New experiment modal
  const [showNewExpModal, setShowNewExpModal] = useState(false);
  const [expTitle, setExpTitle] = useState("");
  const [expHypothesis, setExpHypothesis] = useState("");
  const [expMethod, setExpMethod] = useState("");
  const [expTools, setExpTools] = useState("");

  async function loadData() {
    setLoading(true);
    try {
      const [covData, claimsData, expData] = await Promise.all([
        getEvidenceCoverage(),
        listClaims({ limit: 100 }),
        listExperiments(),
      ]);
      setCoverage(covData);
      setClaims(claimsData);
      setExperiments(expData);

      if (claimsData.length > 0 && !selectedClaimId) {
        setSelectedClaimId(claimsData[0].id);
        loadTrace(claimsData[0].id);
      }
    } catch (err) {
      console.error("Failed to load evidence data:", err);
    } finally {
      setLoading(false);
    }
  }

  async function loadTrace(claimId: string) {
    setTraceLoading(true);
    try {
      const trace = await getClaimProvenance(claimId);
      setProvenanceTrace(trace);
    } catch (err) {
      console.error("Failed to load provenance trace:", err);
    } finally {
      setTraceLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleSelectClaim(claimId: string) {
    setSelectedClaimId(claimId);
    loadTrace(claimId);
  }

  async function handleLinkSource(e: React.FormEvent) {
    e.preventDefault();
    if (!linkSourceModalClaim) return;
    setSubmittingAction(true);
    try {
      await linkSourceEvidence(linkSourceModalClaim.id, {
        source_url: sourceUrl,
        source_title: sourceTitle || sourceUrl,
        quote: sourceQuote,
        source_type: sourceType,
        trust_weight: sourceTrust,
      });
      setLinkSourceModalClaim(null);
      setSourceUrl("");
      setSourceTitle("");
      setSourceQuote("");
      await loadData();
      if (selectedClaimId === linkSourceModalClaim.id) {
        loadTrace(linkSourceModalClaim.id);
      }
    } catch (err) {
      alert("Failed to link source citation.");
    } finally {
      setSubmittingAction(false);
    }
  }

  async function handleLabelOpinion(claimId: string) {
    if (!confirm("Label this claim as subjective creator opinion / speculation?")) return;
    try {
      await labelClaimOpinion(claimId, "opinion");
      await loadData();
      if (selectedClaimId === claimId) {
        loadTrace(claimId);
      }
    } catch (err) {
      alert("Failed to label claim.");
    }
  }

  async function handleCreateClaim(e: React.FormEvent) {
    e.preventDefault();
    if (!newClaimText.trim()) return;
    setSubmittingAction(true);
    try {
      const created = await createClaim({
        text: newClaimText.trim(),
        claim_type: newClaimType,
      });
      setShowNewClaimModal(false);
      setNewClaimText("");
      await loadData();
      setSelectedClaimId(created.id);
      loadTrace(created.id);
    } catch (err) {
      alert("Failed to create claim.");
    } finally {
      setSubmittingAction(false);
    }
  }

  async function handleCreateExperiment(e: React.FormEvent) {
    e.preventDefault();
    if (!expTitle.trim() || !expHypothesis.trim()) return;
    setSubmittingAction(true);
    try {
      const toolsList = expTools.split(",").map((s) => s.trim()).filter(Boolean);
      await createExperiment({
        title: expTitle.trim(),
        hypothesis: expHypothesis.trim(),
        method: expMethod.trim() || "Empirical benchmark execution in local studio lab.",
        tools_models: toolsList,
      });
      setShowNewExpModal(false);
      setExpTitle("");
      setExpHypothesis("");
      setExpMethod("");
      setExpTools("");
      await loadData();
    } catch (err) {
      alert("Failed to record experiment.");
    } finally {
      setSubmittingAction(false);
    }
  }

  const filteredClaims = claims.filter((c) => {
    if (filterType === "all") return true;
    if (filterType === "unsupported") return !c.is_verified && c.claim_type !== "opinion" && c.claim_type !== "prediction_speculation";
    if (filterType === "verified") return c.is_verified;
    if (filterType === "opinion") return c.claim_type === "opinion" || c.claim_type === "prediction_speculation";
    return c.claim_type === filterType;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shadow-sm shadow-emerald-500/10">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Evidence & Provenance Engine
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Source-backed traceability from primary citations and empirical experiments through to final script sections.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors border border-slate-700"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowNewClaimModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium shadow-lg shadow-emerald-600/20 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Claim
          </button>
        </div>
      </div>

      {/* Evidence Coverage & Quality Gate Banner */}
      {coverage && (
        <div className="rounded-xl border border-slate-800 bg-gradient-to-br from-slate-900/90 to-slate-950/80 p-6 shadow-xl relative overflow-hidden backdrop-blur-sm">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border ${
                    coverage.gate_passed
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-sm shadow-emerald-500/10"
                      : "bg-rose-500/10 text-rose-400 border-rose-500/30 shadow-sm shadow-rose-500/10"
                  }`}
                >
                  {coverage.gate_passed ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Quality Gate: Passed
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Quality Gate: Blocked
                    </>
                  )}
                </span>
                <span className="text-xs text-slate-400">
                  Threshold: 85.0% Min Evidence Coverage &bull; 0 Unsupported Claims
                </span>
              </div>

              <div>
                <div className="flex items-baseline gap-3">
                  <span className="text-4xl font-extrabold tracking-tight text-white font-mono">
                    {coverage.coverage_percent.toFixed(1)}%
                  </span>
                  <span className="text-sm font-medium text-slate-400">
                    Evidence Coverage Score
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {coverage.gate_passed
                    ? "All script assertions are verified by primary citations, empirical benchmarks, or explicit creator overrides."
                    : `${coverage.unsupported} factual claim(s) require evidence citations or opinion labeling before script approval.`}
                </p>
              </div>

              {/* Progress Bar */}
              <div className="w-full max-w-xl bg-slate-800 h-2.5 rounded-full overflow-hidden border border-slate-700/60">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${
                    coverage.coverage_percent >= 85
                      ? "bg-gradient-to-r from-emerald-500 to-teal-400"
                      : "bg-gradient-to-r from-amber-500 to-rose-500"
                  }`}
                  style={{ width: `${Math.min(100, coverage.coverage_percent)}%` }}
                />
              </div>
            </div>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="text-xl font-bold text-white font-mono">{coverage.total_claims}</div>
                <div className="text-[11px] text-slate-400 uppercase font-semibold mt-0.5">Total Claims</div>
              </div>
              <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="text-xl font-bold text-emerald-400 font-mono">
                  {coverage.primary_source_backed + coverage.supporting_source_backed}
                </div>
                <div className="text-[11px] text-slate-400 uppercase font-semibold mt-0.5">Source-Backed</div>
              </div>
              <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                <div className="text-xl font-bold text-cyan-400 font-mono">{coverage.original_test_backed}</div>
                <div className="text-[11px] text-slate-400 uppercase font-semibold mt-0.5">Original Tests</div>
              </div>
              <div className={`p-3 rounded-lg border ${coverage.unsupported > 0 ? "bg-rose-950/20 border-rose-800/60" : "bg-slate-950/60 border-slate-800/80"}`}>
                <div className={`text-xl font-bold font-mono ${coverage.unsupported > 0 ? "text-rose-400" : "text-slate-400"}`}>
                  {coverage.unsupported}
                </div>
                <div className="text-[11px] text-slate-400 uppercase font-semibold mt-0.5">Unsupported</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Studio Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto no-scrollbar whitespace-nowrap">
        <button
          onClick={() => setActiveTab("claims")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === "claims"
              ? "bg-slate-800 text-white border border-slate-700"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Quote className="w-4 h-4 text-emerald-400" />
          Claims & Citations ({claims.length})
        </button>

        <button
          onClick={() => setActiveTab("provenance")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === "provenance"
              ? "bg-slate-800 text-white border border-slate-700"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <GitBranch className="w-4 h-4 text-cyan-400" />
          Provenance Graph
        </button>

        <button
          onClick={() => setActiveTab("experiments")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === "experiments"
              ? "bg-slate-800 text-white border border-slate-700"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <FlaskConical className="w-4 h-4 text-amber-400" />
          Studio Experiments ({experiments.length})
        </button>
      </div>

      {/* TAB 1: CLAIMS & CITATIONS */}
      {activeTab === "claims" && (
        <div className="space-y-6">
          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: "all", label: "All Claims" },
              { id: "unsupported", label: "Unsupported Only" },
              { id: "verified", label: "Verified Only" },
              { id: "external_fact", label: "External Facts" },
              { id: "original_measurement", label: "Original Measurements" },
              { id: "opinion", label: "Opinions" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterType(f.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                  filterType === f.id
                    ? "bg-indigo-600/20 text-indigo-300 border-indigo-500/40"
                    : "bg-slate-900/60 text-slate-400 border-slate-800 hover:bg-slate-800"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Claims List */}
          <div className="grid gap-4">
            {filteredClaims.length === 0 ? (
              <div className="p-12 text-center border border-slate-800 rounded-xl bg-slate-900/30">
                <CheckCircle2 className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-slate-300">No claims match filter</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Adjust filters or add a new claim to begin tracking provenance.
                </p>
              </div>
            ) : (
              filteredClaims.map((claim) => (
                <div
                  key={claim.id}
                  className={`p-5 rounded-xl border transition-all ${
                    selectedClaimId === claim.id
                      ? "bg-slate-900/90 border-indigo-500/50 shadow-md shadow-indigo-500/10"
                      : "bg-slate-900/40 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                            claim.is_verified
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                              : claim.claim_type === "opinion" || claim.claim_type === "prediction_speculation"
                              ? "bg-purple-500/10 text-purple-400 border-purple-500/30"
                              : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                          }`}
                        >
                          {claim.is_verified
                            ? "Verified"
                            : claim.claim_type === "opinion"
                            ? "Labeled Opinion"
                            : "Unsupported"}
                        </span>

                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {claim.claim_type}
                        </span>

                        <span className="text-xs text-slate-500">
                          Confidence: {(claim.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      <p className="text-sm font-medium text-slate-200 leading-relaxed">
                        {claim.text}
                      </p>
                    </div>

                    {/* Action Controls */}
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleSelectClaim(claim.id)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
                      >
                        Inspect Trace
                      </button>

                      {!claim.is_verified && claim.claim_type !== "opinion" && (
                        <>
                          <button
                            onClick={() => setLinkSourceModalClaim(claim)}
                            className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors flex items-center gap-1.5 shadow-sm shadow-emerald-600/20"
                          >
                            <Link2 className="w-3.5 h-3.5" />
                            Link Source
                          </button>

                          <button
                            onClick={() => handleLabelOpinion(claim.id)}
                            className="px-3 py-1.5 rounded-lg bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 text-xs font-medium border border-purple-500/30 transition-colors"
                          >
                            Label Opinion
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 2: PROVENANCE GRAPH INSPECTOR */}
      {activeTab === "provenance" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Claim Selector List */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Select Claim to Trace
            </h3>
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {claims.map((c) => (
                <div
                  key={c.id}
                  onClick={() => handleSelectClaim(c.id)}
                  className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                    selectedClaimId === c.id
                      ? "bg-indigo-600/10 border-indigo-500/50 text-indigo-200"
                      : "bg-slate-900/50 border-slate-800 text-slate-400 hover:bg-slate-800/60"
                  }`}
                >
                  <div className="text-xs font-medium line-clamp-2">{c.text}</div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                      {c.claim_type}
                    </span>
                    <span className={`text-[10px] ${c.is_verified ? "text-emerald-400" : "text-rose-400"}`}>
                      {c.is_verified ? "Verified" : "Unsupported"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Graph Visualization Card */}
          <div className="lg:col-span-2 space-y-6">
            {traceLoading ? (
              <div className="p-16 text-center border border-slate-800 rounded-xl bg-slate-900/30">
                <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-2" />
                <p className="text-xs text-slate-400">Traversing provenance graph...</p>
              </div>
            ) : provenanceTrace ? (
              <div className="space-y-6">
                {/* 1. Root Citation Sources */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 uppercase tracking-wider">
                    <ExternalLink className="w-4 h-4" />
                    <span>Level 1: Citation Sources ({provenanceTrace.sources.length})</span>
                  </div>

                  {provenanceTrace.sources.length === 0 ? (
                    <div className="text-xs text-slate-500 italic p-3 bg-slate-950/40 rounded border border-slate-800/60">
                      No external citation sources attached to this claim.
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      {provenanceTrace.sources.map((src, i) => (
                        <div key={i} className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <a
                              href={src.url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs font-semibold text-cyan-300 hover:underline flex items-center gap-1"
                            >
                              {src.title || src.domain}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-800/50">
                              Trust: {src.trust_weight}x
                            </span>
                          </div>
                          {src.quote && (
                            <p className="text-xs text-slate-400 italic bg-slate-900/40 p-2 rounded border border-slate-800/50">
                              "{src.quote}"
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 2. Claim Node */}
                <div className="rounded-xl border border-indigo-500/40 bg-indigo-950/20 p-5 space-y-2 relative">
                  <div className="flex items-center justify-between text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                    <span className="flex items-center gap-2">
                      <Quote className="w-4 h-4" />
                      Level 2: Asserted Empirical Claim
                    </span>
                    <span className="font-mono text-[11px]">{provenanceTrace.claim_type}</span>
                  </div>
                  <p className="text-sm font-medium text-slate-100 leading-relaxed">
                    {provenanceTrace.claim_text}
                  </p>
                </div>

                {/* 3. Experiments & Empirical Measurements */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-amber-400 uppercase tracking-wider">
                    <FlaskConical className="w-4 h-4" />
                    <span>Level 3: Studio Benchmarks & Experiments ({provenanceTrace.experiments.length})</span>
                  </div>

                  {provenanceTrace.experiments.length === 0 ? (
                    <div className="text-xs text-slate-500 italic p-3 bg-slate-950/40 rounded border border-slate-800/60">
                      No studio lab experiments or benchmarks linked to this claim.
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      {provenanceTrace.experiments.map((exp, i) => (
                        <div key={i} className="p-4 bg-slate-950/60 rounded-lg border border-slate-800/80 space-y-3">
                          <div>
                            <h4 className="text-xs font-semibold text-amber-300">{exp.title}</h4>
                            <p className="text-xs text-slate-400 mt-0.5">{exp.hypothesis}</p>
                          </div>

                          {exp.runs.map((run, ri) => (
                            <div key={ri} className="p-2.5 bg-slate-900/60 rounded border border-slate-800 space-y-1.5">
                              <div className="flex items-center justify-between text-[11px] text-slate-400">
                                <span>Run #{run.run_number}</span>
                                <span>{run.execution_time_ms}ms</span>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {run.measurements.map((m, mi) => (
                                  <span
                                    key={mi}
                                    className="text-xs font-mono px-2 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/40"
                                  >
                                    {m.metric}: {m.value} {m.unit || ""}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ))}

                          {exp.conclusion_summary && (
                            <div className="text-xs text-emerald-400 bg-emerald-950/20 p-2 rounded border border-emerald-800/40">
                              <strong>Conclusion:</strong> {exp.conclusion_summary}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 4. Script Usages */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-purple-400 uppercase tracking-wider">
                    <FileText className="w-4 h-4" />
                    <span>Level 4: Script & Scene Usages ({provenanceTrace.content_usages.length})</span>
                  </div>

                  {provenanceTrace.content_usages.length === 0 ? (
                    <div className="text-xs text-slate-500 italic p-3 bg-slate-950/40 rounded border border-slate-800/60">
                      Not currently mapped to an active script draft.
                    </div>
                  ) : (
                    <div className="grid gap-2">
                      {provenanceTrace.content_usages.map((u, i) => (
                        <div key={i} className="p-3 bg-slate-950/60 rounded border border-slate-800/80 flex items-center justify-between">
                          <div>
                            <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                              Section: {u.section_id}
                            </span>
                            <p className="text-xs text-slate-300 mt-1">"{u.quote_in_script}"</p>
                          </div>
                          <span className="text-xs text-emerald-400 font-medium">
                            {u.verification_status}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* TAB 3: STUDIO EXPERIMENTS & BENCHMARKS */}
      {activeTab === "experiments" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Original Studio Benchmarks</h2>
            <button
              onClick={() => setShowNewExpModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium shadow-sm shadow-amber-600/20 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              New Experiment
            </button>
          </div>

          <div className="grid gap-4">
            {experiments.length === 0 ? (
              <div className="p-12 text-center border border-slate-800 rounded-xl bg-slate-900/30">
                <FlaskConical className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-slate-300">No experiments recorded</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Empirical benchmarks give your studio original evidence that sets you apart from generic summaries.
                </p>
              </div>
            ) : (
              experiments.map((exp) => (
                <div key={exp.id} className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-4">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                    <div>
                      <h3 className="text-base font-semibold text-white">{exp.title}</h3>
                      <p className="text-xs text-slate-400 mt-1"><strong>Hypothesis:</strong> {exp.hypothesis}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {exp.run_count || 0} Runs
                      </span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {exp.conclusions_count || 0} Conclusions
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-slate-400 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <strong>Methodology:</strong> {exp.method}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* MODAL: Link Source Citation */}
      {linkSourceModalClaim && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Link2 className="w-5 h-5 text-emerald-400" />
                Link Citation Source
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Provide a verifiable external URL and excerpt to back this claim.
              </p>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 text-xs text-slate-300">
              "{linkSourceModalClaim.text}"
            </div>

            <form onSubmit={handleLinkSource} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Source Canonical URL *
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://example.com/article"
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Document / Article Headline
                </label>
                <input
                  type="text"
                  placeholder="Benchmarking LLMs on M4 Max"
                  value={sourceTitle}
                  onChange={(e) => setSourceTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Direct Verbatim Quote *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Paste direct sentence or paragraph from source..."
                  value={sourceQuote}
                  onChange={(e) => setSourceQuote(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Source Type
                  </label>
                  <select
                    value={sourceType}
                    onChange={(e) => setSourceType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200"
                  >
                    <option value="primary">Primary Source</option>
                    <option value="supporting">Supporting Source</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Trust Weight
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="1.5"
                    value={sourceTrust}
                    onChange={(e) => setSourceTrust(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setLinkSourceModalClaim(null)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium shadow-md shadow-emerald-600/20"
                >
                  {submittingAction ? "Verifying..." : "Verify & Attach Citation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: New Claim */}
      {showNewClaimModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Quote className="w-5 h-5 text-indigo-400" />
                Add Empirical Claim
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Enter an assertion to track through the evidence graph.
              </p>
            </div>

            <form onSubmit={handleCreateClaim} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Claim Text *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="e.g. M4 Max achieves 138 tokens/s on 4-bit DeepSeek 67B."
                  value={newClaimText}
                  onChange={(e) => setNewClaimText(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Claim Type
                </label>
                <select
                  value={newClaimType}
                  onChange={(e) => setNewClaimType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200"
                >
                  <option value="external_fact">External Fact (requires citation)</option>
                  <option value="original_measurement">Original Measurement (from studio benchmark)</option>
                  <option value="derived_conclusion">Derived Conclusion (synthesized from data)</option>
                  <option value="opinion">Subjective Creator Opinion</option>
                  <option value="prediction_speculation">Future Prediction / Speculation</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowNewClaimModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-md shadow-indigo-600/20"
                >
                  {submittingAction ? "Adding..." : "Add to Graph"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: New Experiment */}
      {showNewExpModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FlaskConical className="w-5 h-5 text-amber-400" />
                Record Studio Benchmark Experiment
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Define the hypothesis and methodology for an empirical lab test.
              </p>
            </div>

            <form onSubmit={handleCreateExperiment} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Experiment Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Local Ollama vs vLLM Latency Test"
                  value={expTitle}
                  onChange={(e) => setExpTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Hypothesis *
                </label>
                <textarea
                  required
                  rows={2}
                  placeholder="e.g. vLLM will achieve 25% lower TTFT due to paged attention."
                  value={expHypothesis}
                  onChange={(e) => setExpHypothesis(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Tools & Models (comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="vLLM, Ollama, DeepSeek-67B"
                  value={expTools}
                  onChange={(e) => setExpTools(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-slate-200"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowNewExpModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium shadow-md shadow-amber-600/20"
                >
                  {submittingAction ? "Recording..." : "Record Experiment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
