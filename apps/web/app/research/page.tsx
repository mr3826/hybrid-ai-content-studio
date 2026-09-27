"use client";

import { useEffect, useState, useTransition, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  History,
  RotateCcw,
  Sparkles,
  Plus,
  Search,
  Filter,
  Layers,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Clock,
  HelpCircle,
  Hash,
  Calendar,
  Tag,
  Edit3,
  X,
  RefreshCw,
} from "lucide-react";
import {
  ResearchPacket,
  ResearchRevision,
  listResearchPackets,
  getResearchPacket,
  createResearchPacket,
  updateResearchPacket,
  verifyResearchPacket,
  getResearchRevisions,
  revertResearchRevision,
} from "@/lib/api";

function ResearchContent() {
  const searchParams = useSearchParams();
  const paramOppId = searchParams.get("opportunity_id");
  const paramPacketId = searchParams.get("packet_id");

  const [packets, setPackets] = useState<ResearchPacket[]>([]);
  const [selectedPacket, setSelectedPacket] = useState<ResearchPacket | null>(null);
  const [revisions, setRevisions] = useState<ResearchRevision[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [isPending, startTransition] = useTransition();

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [verifiedFilter, setVerifiedFilter] = useState<string>("all");

  // Modals & Forms
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showRevisionsModal, setShowRevisionsModal] = useState(false);
  const [showAddClaimModal, setShowAddClaimModal] = useState(false);
  const [isEditingSummary, setIsEditingSummary] = useState(false);
  const [editedSummary, setEditedSummary] = useState("");

  // New Packet Form State
  const [newTopic, setNewTopic] = useState("");
  const [newSourcesText, setNewSourcesText] = useState("");
  const [newRawText, setNewRawText] = useState("");

  // New Manual Claim Form State
  const [newClaimText, setNewClaimText] = useState("");
  const [newClaimStatus, setNewClaimStatus] = useState<"manually_entered" | "source-backed" | "explicitly_uncertain">("manually_entered");
  const [newClaimSourceUrl, setNewClaimSourceUrl] = useState("");
  const [newClaimEvidence, setNewClaimEvidence] = useState("");
  const [newClaimReason, setNewClaimReason] = useState("");

  // Toast / Status Feedback
  const [feedback, setFeedback] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  const fetchPackets = async () => {
    try {
      setLoading(true);
      const data = await listResearchPackets({
        is_verified: verifiedFilter === "all" ? undefined : verifiedFilter === "verified",
        search: searchQuery || undefined,
        limit: 50,
      });
      setPackets(data);

      // Handle selecting packet from URL params or default to first
      if (paramPacketId) {
        const found = data.find((p) => p.id === paramPacketId);
        if (found) {
          setSelectedPacket(found);
          loadRevisions(found.id);
        }
      } else if (paramOppId) {
        const linked = data.find((p) => p.opportunity_id === paramOppId);
        if (linked) {
          setSelectedPacket(linked);
          loadRevisions(linked.id);
        } else {
          // If not found, automatically attempt generation for this opportunity
          handleAutoGenerateForOpp(paramOppId);
        }
      } else if (data.length > 0 && !selectedPacket) {
        setSelectedPacket(data[0]);
        loadRevisions(data[0].id);
      }
    } catch (err: any) {
      console.error("Failed to load research packets:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoGenerateForOpp = async (oppId: string) => {
    try {
      setActionLoading(true);
      setFeedback({ type: "info", text: "Synthesizing traceable Research Packet for opportunity..." });
      const created = await createResearchPacket({ opportunity_id: oppId });
      setPackets((prev) => [created, ...prev]);
      setSelectedPacket(created);
      loadRevisions(created.id);
      setFeedback({ type: "success", text: `Research Packet generated for "${created.topic}"!` });
    } catch (err: any) {
      setFeedback({ type: "error", text: `Generation failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  const loadRevisions = async (packetId: string) => {
    try {
      const revs = await getResearchRevisions(packetId);
      setRevisions(revs);
    } catch (err) {
      console.error("Failed to load revisions:", err);
    }
  };

  useEffect(() => {
    fetchPackets();
  }, [verifiedFilter, searchQuery]);

  const handleSelectPacket = (packet: ResearchPacket) => {
    setSelectedPacket(packet);
    setIsEditingSummary(false);
    setEditedSummary(packet.summary);
    loadRevisions(packet.id);
  };

  const handleVerify = async () => {
    if (!selectedPacket) return;
    try {
      setActionLoading(true);
      const verified = await verifyResearchPacket(selectedPacket.id);
      setSelectedPacket(verified);
      setPackets((prev) => prev.map((p) => (p.id === verified.id ? verified : p)));
      setFeedback({
        type: "success",
        text: `Research Packet verified! Human Quality Gate cleared for script synthesis.`,
      });
      loadRevisions(verified.id);
    } catch (err: any) {
      setFeedback({ type: "error", text: `Verification failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveSummary = async () => {
    if (!selectedPacket) return;
    try {
      setActionLoading(true);
      const updated = await updateResearchPacket(selectedPacket.id, {
        summary: editedSummary,
        change_summary: "Updated executive research summary",
        changed_by: "creator",
      });
      setSelectedPacket(updated);
      setPackets((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setIsEditingSummary(false);
      setFeedback({ type: "success", text: "Summary updated and new revision archived." });
      loadRevisions(updated.id);
    } catch (err: any) {
      setFeedback({ type: "error", text: `Update failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddManualClaim = async () => {
    if (!selectedPacket || !newClaimText.trim()) return;
    try {
      setActionLoading(true);
      const newClaim = {
        id: `c-${Date.now()}`,
        claim_text: newClaimText.trim(),
        verification_status: newClaimStatus,
        evidence_quote: newClaimEvidence || undefined,
        source_url: newClaimSourceUrl || undefined,
        uncertainty_reason: newClaimReason || undefined,
        confidence: newClaimStatus === "source-backed" ? 0.95 : 0.7,
      };

      const updatedClaims = [...selectedPacket.claims, newClaim];
      const updated = await updateResearchPacket(selectedPacket.id, {
        claims: updatedClaims as any,
        change_summary: `Added ${newClaimStatus} claim by creator`,
        changed_by: "creator",
      });

      setSelectedPacket(updated);
      setPackets((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setShowAddClaimModal(false);
      setNewClaimText("");
      setNewClaimEvidence("");
      setNewClaimSourceUrl("");
      setNewClaimReason("");
      setFeedback({ type: "success", text: "Claim added with verified attribution." });
      loadRevisions(updated.id);
    } catch (err: any) {
      setFeedback({ type: "error", text: `Failed to add claim: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevert = async (revNumber: number) => {
    if (!selectedPacket) return;
    try {
      setActionLoading(true);
      const reverted = await revertResearchRevision(selectedPacket.id, revNumber);
      setSelectedPacket(reverted);
      setPackets((prev) => prev.map((p) => (p.id === reverted.id ? reverted : p)));
      setShowRevisionsModal(false);
      setFeedback({ type: "success", text: `Successfully reverted to revision #${revNumber}.` });
      loadRevisions(reverted.id);
    } catch (err: any) {
      setFeedback({ type: "error", text: `Revert failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreatePacket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopic.trim()) return;

    try {
      setActionLoading(true);
      // Parse sources URLs or lines
      const sourcesList = newSourcesText
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean)
        .map((url, idx) => ({
          url,
          title: `Source Reference ${idx + 1}`,
          excerpt: "",
          trust_weight: 1.0,
        }));

      const created = await createResearchPacket({
        topic: newTopic.trim(),
        sources: sourcesList,
        raw_text: newRawText.trim() || undefined,
      });

      setPackets((prev) => [created, ...prev]);
      setSelectedPacket(created);
      setShowCreateModal(false);
      setNewTopic("");
      setNewSourcesText("");
      setNewRawText("");
      setFeedback({ type: "success", text: `Traceable packet created for "${created.topic}"!` });
      loadRevisions(created.id);
    } catch (err: any) {
      setFeedback({ type: "error", text: `Creation failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast Feedback */}
      {feedback && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between shadow-lg transition-all ${
            feedback.type === "success"
              ? "bg-emerald-950/70 border-emerald-700/50 text-emerald-200"
              : feedback.type === "info"
              ? "bg-blue-950/70 border-blue-700/50 text-blue-200"
              : "bg-rose-950/70 border-rose-700/50 text-rose-200"
          }`}
        >
          <div className="flex items-center gap-3">
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : feedback.type === "info" ? (
              <Sparkles className="w-5 h-5 text-blue-400" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-400" />
            )}
            <span className="text-sm font-medium">{feedback.text}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-xs opacity-75 hover:opacity-100 px-2 py-1 rounded bg-black/20"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-indigo-400" />
              Evidence-Based Research Engine
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Ground Truth
            </span>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Traceable facts, verifiable metrics, source-backed claims, and unverified hype isolation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-md transition flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            New Research Packet
          </button>
        </div>
      </div>

      {/* Main Layout: Left Packet List, Right Packet Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Packet Backlog / Browser (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-zinc-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search research topics..."
                className="w-full bg-zinc-950/80 border border-zinc-800 rounded-lg pl-9 pr-3 py-2 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span>Status:</span>
              <div className="flex items-center gap-1">
                {(["all", "verified", "unverified"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setVerifiedFilter(mode)}
                    className={`px-2 py-1 rounded capitalize text-[11px] font-medium transition ${
                      verifiedFilter === mode
                        ? "bg-indigo-600 text-white"
                        : "bg-zinc-800/80 text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
            {loading && packets.length === 0 ? (
              <div className="p-8 text-center text-xs text-zinc-500">Loading research packets...</div>
            ) : packets.length === 0 ? (
              <div className="p-8 text-center rounded-xl bg-zinc-900/40 border border-zinc-800/80 text-zinc-400 text-xs">
                No research packets found. Generate one from Opportunities or click "+ New Research Packet".
              </div>
            ) : (
              packets.map((pkt) => {
                const isSelected = selectedPacket?.id === pkt.id;
                const sourceBackedCount = pkt.claims.filter((c) => c.verification_status === "source-backed").length;
                return (
                  <div
                    key={pkt.id}
                    onClick={() => handleSelectPacket(pkt)}
                    className={`p-3.5 rounded-xl border transition cursor-pointer ${
                      isSelected
                        ? "bg-indigo-950/30 border-indigo-500/50 shadow-md ring-1 ring-indigo-500/20"
                        : "bg-zinc-900/60 border-zinc-800/80 hover:bg-zinc-900 hover:border-zinc-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <h3 className="text-xs font-semibold text-zinc-100 line-clamp-2 leading-tight">
                        {pkt.topic}
                      </h3>
                      {pkt.is_verified ? (
                        <span className="shrink-0 flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          Verified
                        </span>
                      ) : (
                        <span className="shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          Pending
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-zinc-400 mb-2">
                      <span className="font-mono text-zinc-500">v{pkt.version}</span>
                      <span>•</span>
                      <span>{pkt.primary_sources.length + pkt.supporting_sources.length} sources</span>
                      <span>•</span>
                      <span className="text-emerald-400/90">{sourceBackedCount} backed</span>
                      {pkt.things_not_to_claim.length > 0 && (
                        <>
                          <span>•</span>
                          <span className="text-rose-400/90">{pkt.things_not_to_claim.length} hype</span>
                        </>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-zinc-500">
                      <span>{new Date(pkt.updated_at || pkt.created_at).toLocaleDateString()}</span>
                      {pkt.opportunity_id && (
                        <span className="text-indigo-400 flex items-center gap-0.5">
                          Opp Linked <ArrowRight className="w-2.5 h-2.5" />
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Detailed Traceable Packet Viewer (8 cols) */}
        <div className="lg:col-span-8">
          {selectedPacket ? (
            <div className="space-y-6">
              {/* Packet Top Banner & Quality Gate Control */}
              <div className="p-5 rounded-2xl bg-zinc-900/80 border border-zinc-800 shadow-xl space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-zinc-800 text-zinc-300 border border-zinc-700">
                        Revision v{selectedPacket.version}
                      </span>
                      {selectedPacket.is_verified ? (
                        <span className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                          Verified Ground Truth
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                          Verification Gate Required
                        </span>
                      )}
                    </div>
                    <h2 className="text-lg font-bold text-white mt-1.5 leading-snug">
                      {selectedPacket.topic}
                    </h2>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowRevisionsModal(true)}
                      className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium rounded-lg border border-zinc-700 transition flex items-center gap-1.5"
                      title="Revision Audit History"
                    >
                      <History className="w-3.5 h-3.5 text-indigo-400" />
                      History ({revisions.length || selectedPacket.version})
                    </button>

                    {!selectedPacket.is_verified ? (
                      <button
                        onClick={handleVerify}
                        disabled={actionLoading}
                        className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg shadow-md transition flex items-center gap-1.5 disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        Verify Packet
                      </button>
                    ) : (
                      <div className="text-right">
                        <span className="text-[11px] text-emerald-400 font-medium block">
                          Verified by {selectedPacket.verified_by || "creator"}
                        </span>
                        <span className="text-[10px] text-zinc-500">
                          {selectedPacket.verified_at ? new Date(selectedPacket.verified_at).toLocaleTimeString() : ""}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Grounded Summary Card */}
                <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      Synthesized Ground Truth Summary
                    </h4>
                    {!isEditingSummary ? (
                      <button
                        onClick={() => {
                          setEditedSummary(selectedPacket.summary);
                          setIsEditingSummary(true);
                        }}
                        className="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
                      >
                        <Edit3 className="w-3 h-3" /> Edit
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={handleSaveSummary}
                          disabled={actionLoading}
                          className="px-2 py-0.5 bg-indigo-600 text-white text-[11px] font-semibold rounded hover:bg-indigo-500"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setIsEditingSummary(false)}
                          className="text-[11px] text-zinc-400 hover:text-zinc-200"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>

                  {isEditingSummary ? (
                    <textarea
                      value={editedSummary}
                      onChange={(e) => setEditedSummary(e.target.value)}
                      rows={3}
                      className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                    />
                  ) : (
                    <p className="text-xs text-zinc-300 leading-relaxed">
                      {selectedPacket.summary || "No summary synthesized yet."}
                    </p>
                  )}
                </div>
              </div>

              {/* Contradictions Alert Callout (If any) */}
              {selectedPacket.contradictions && selectedPacket.contradictions.length > 0 && (
                <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/40 text-amber-200 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-xs text-amber-300">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    Detected Cross-Source Contradictions ({selectedPacket.contradictions.length})
                  </div>
                  <div className="space-y-2 text-xs">
                    {selectedPacket.contradictions.map((c, idx) => (
                      <div key={idx} className="p-2.5 rounded bg-zinc-950/60 border border-amber-500/20 space-y-1">
                        <p className="font-medium text-amber-100">{c.conflict_summary}</p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-zinc-400">
                          <div>
                            <span className="text-zinc-500">Source A:</span> {c.claim_a}
                          </div>
                          <div>
                            <span className="text-zinc-500">Source B:</span> {c.claim_b}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Things NOT to Claim Alert (Unverified Vendor Marketing Claims) */}
              {selectedPacket.things_not_to_claim && selectedPacket.things_not_to_claim.length > 0 && (
                <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-600/30 text-rose-200 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-xs text-rose-300">
                    <ShieldAlert className="w-4 h-4 text-rose-400" />
                    Things NOT to Claim (Unverified Vendor Hype & Superlatives)
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                    {selectedPacket.things_not_to_claim.map((item, idx) => (
                      <div key={idx} className="p-2.5 rounded bg-zinc-950/60 border border-rose-500/20 space-y-1">
                        <span className="font-semibold text-rose-300 block">{item.claim_text}</span>
                        <p className="text-[11px] text-zinc-400">{item.reason_to_avoid}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Numbers & Benchmarks Grid */}
              {selectedPacket.numbers && selectedPacket.numbers.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Hash className="w-3.5 h-3.5 text-indigo-400" />
                    Verified Quantitative Metrics & Benchmarks ({selectedPacket.numbers.length})
                  </h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                    {selectedPacket.numbers.map((num, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1 hover:border-zinc-700 transition"
                      >
                        <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider block">
                          {num.metric}
                        </span>
                        <div className="text-base font-extrabold text-white font-mono">
                          {num.value}
                        </div>
                        <p className="text-[10px] text-zinc-400 line-clamp-2" title={num.context}>
                          {num.context}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Claims & Verification Taxonomy */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                    Claims & Verification Taxonomy ({selectedPacket.claims.length})
                  </h3>
                  <button
                    onClick={() => setShowAddClaimModal(true)}
                    className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg border border-zinc-700 transition flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" /> Add Claim
                  </button>
                </div>

                <div className="space-y-2">
                  {selectedPacket.claims.map((claim, idx) => {
                    const isSourceBacked = claim.verification_status === "source-backed";
                    const isUncertain = claim.verification_status === "explicitly_uncertain";
                    const isManual = claim.verification_status === "manually_entered";

                    return (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-xl border transition ${
                          isSourceBacked
                            ? "bg-zinc-900/50 border-emerald-500/30 hover:border-emerald-500/50"
                            : isUncertain
                            ? "bg-zinc-900/50 border-amber-500/30 hover:border-amber-500/50"
                            : "bg-zinc-900/50 border-blue-500/30 hover:border-blue-500/50"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <p className="text-xs text-zinc-200 leading-relaxed font-medium">
                            {claim.claim_text}
                          </p>

                          <div className="shrink-0">
                            {isSourceBacked && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                                source-backed
                              </span>
                            )}
                            {isUncertain && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                                explicitly_uncertain
                              </span>
                            )}
                            {isManual && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/40">
                                manually_entered
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Attribution evidence or uncertainty note */}
                        {isSourceBacked && claim.evidence_quote && (
                          <div className="mt-2 text-[11px] text-zinc-400 bg-zinc-950/60 p-2 rounded border border-zinc-800/80 flex items-center justify-between">
                            <span className="italic truncate pr-2">"{claim.evidence_quote}"</span>
                            {claim.source_url && (
                              <a
                                href={claim.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-emerald-400 hover:text-emerald-300 shrink-0 flex items-center gap-0.5"
                              >
                                View Citation <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>
                        )}

                        {isUncertain && claim.uncertainty_reason && (
                          <div className="mt-2 text-[11px] text-amber-300/90 bg-amber-950/20 p-2 rounded border border-amber-800/40 flex items-center gap-1.5">
                            <HelpCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                            <span>{claim.uncertainty_reason}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Primary & Supporting Sources */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                  <ExternalLink className="w-3.5 h-3.5 text-indigo-400" />
                  Cited Source Provenance (
                  {selectedPacket.primary_sources.length + selectedPacket.supporting_sources.length}
                  )
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Primary Sources */}
                  {selectedPacket.primary_sources.map((src, idx) => (
                    <div
                      key={`pri-${idx}`}
                      className="p-3.5 rounded-xl bg-zinc-900/60 border border-indigo-500/30 space-y-2"
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold">
                          Primary Source
                        </span>
                        <span className="text-zinc-500 font-mono text-[10px]">{src.domain}</span>
                      </div>
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-bold text-zinc-100 hover:text-indigo-400 transition line-clamp-1 flex items-center gap-1"
                      >
                        {src.title}
                        <ExternalLink className="w-3 h-3 text-zinc-500" />
                      </a>
                      {src.excerpt && (
                        <p className="text-[11px] text-zinc-400 line-clamp-2 italic">
                          "{src.excerpt}"
                        </p>
                      )}
                    </div>
                  ))}

                  {/* Supporting Sources */}
                  {selectedPacket.supporting_sources.map((src, idx) => (
                    <div
                      key={`sup-${idx}`}
                      className="p-3.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-2"
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 font-medium">
                          Supporting
                        </span>
                        <span className="text-zinc-500 font-mono text-[10px]">{src.domain}</span>
                      </div>
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-semibold text-zinc-200 hover:text-indigo-400 transition line-clamp-1 flex items-center gap-1"
                      >
                        {src.title}
                        <ExternalLink className="w-3 h-3 text-zinc-500" />
                      </a>
                      {src.excerpt && (
                        <p className="text-[11px] text-zinc-400 line-clamp-2 italic">
                          "{src.excerpt}"
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Dates & Entities Footer */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Key Dates */}
                <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-2">
                  <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                    Key Milestones & Dates
                  </h4>
                  <div className="space-y-1.5">
                    {selectedPacket.dates.length === 0 ? (
                      <span className="text-[11px] text-zinc-500">No dates extracted</span>
                    ) : (
                      selectedPacket.dates.map((d, idx) => (
                        <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-zinc-800/60">
                          <span className="font-mono text-indigo-300 font-semibold">{d.date_str}</span>
                          <span className="text-zinc-400 text-[11px] truncate max-w-[200px]">{d.event}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Identified Entities */}
                <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-2">
                  <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5 text-indigo-400" />
                    Identified Tech Entities
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedPacket.entities.length === 0 ? (
                      <span className="text-[11px] text-zinc-500">No entities extracted</span>
                    ) : (
                      selectedPacket.entities.map((e, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded text-[11px] bg-zinc-800 text-zinc-300 border border-zinc-700 font-medium"
                        >
                          {e.name} <span className="text-[9px] text-zinc-500">({e.type})</span>
                        </span>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-2xl bg-zinc-900/40 border border-zinc-800 space-y-3">
              <BookOpen className="w-10 h-10 text-zinc-600 mx-auto" />
              <h3 className="text-sm font-semibold text-zinc-300">No Research Packet Selected</h3>
              <p className="text-xs text-zinc-500 max-w-sm mx-auto">
                Select a research packet from the left backlog or generate a new one from an approved opportunity.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Revisions Audit History Modal */}
      {showRevisionsModal && selectedPacket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-zinc-900 border border-zinc-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <History className="w-4 h-4 text-indigo-400" />
                Revision History & Audit Snapshots
              </h3>
              <button
                onClick={() => setShowRevisionsModal(false)}
                className="text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-zinc-400">
              Every creator correction and automated extraction is version-preserved. Reverting restores the complete state snapshot.
            </p>

            <div className="space-y-2 overflow-y-auto flex-1 pr-1">
              {revisions.map((rev) => (
                <div
                  key={rev.id}
                  className="p-3.5 rounded-xl bg-zinc-950/70 border border-zinc-800 flex items-center justify-between gap-3"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-indigo-300">
                        v{rev.revision_number}
                      </span>
                      <span className="text-[11px] text-zinc-500">
                        {new Date(rev.created_at).toLocaleString()}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
                        by {rev.changed_by}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-300">{rev.change_summary || "Automated snapshot"}</p>
                  </div>

                  {rev.revision_number !== selectedPacket.version && (
                    <button
                      onClick={() => handleRevert(rev.revision_number)}
                      disabled={actionLoading}
                      className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold text-zinc-200 rounded border border-zinc-700 flex items-center gap-1 transition"
                    >
                      <RotateCcw className="w-3 h-3" /> Revert
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Add Manual Claim Modal */}
      {showAddClaimModal && selectedPacket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-zinc-900 border border-zinc-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Plus className="w-4 h-4 text-indigo-400" />
                Add Factual Claim
              </h3>
              <button
                onClick={() => setShowAddClaimModal(false)}
                className="text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Claim Statement</label>
                <textarea
                  value={newClaimText}
                  onChange={(e) => setNewClaimText(e.target.value)}
                  placeholder="e.g. Measured 142 tokens/s generation speed under local test bench."
                  rows={2}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs text-zinc-400 block mb-1">Verification Classification</label>
                <select
                  value={newClaimStatus}
                  onChange={(e: any) => setNewClaimStatus(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="manually_entered">manually_entered (Creator lab test/observation)</option>
                  <option value="source-backed">source-backed (Direct citation with quote)</option>
                  <option value="explicitly_uncertain">explicitly_uncertain (Pending benchmark/unconfirmed)</option>
                </select>
              </div>

              {newClaimStatus === "source-backed" && (
                <>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Source URL</label>
                    <input
                      type="url"
                      value={newClaimSourceUrl}
                      onChange={(e) => setNewClaimSourceUrl(e.target.value)}
                      placeholder="https://..."
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-400 block mb-1">Direct Quote / Evidence</label>
                    <input
                      type="text"
                      value={newClaimEvidence}
                      onChange={(e) => setNewClaimEvidence(e.target.value)}
                      placeholder="Exact quote from source"
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </>
              )}

              {newClaimStatus === "explicitly_uncertain" && (
                <div>
                  <label className="text-xs text-zinc-400 block mb-1">Reason for Uncertainty</label>
                  <input
                    type="text"
                    value={newClaimReason}
                    onChange={(e) => setNewClaimReason(e.target.value)}
                    placeholder="e.g. Unconfirmed benchmark claim lacking test methodology."
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowAddClaimModal(false)}
                  className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddManualClaim}
                  disabled={!newClaimText.trim() || actionLoading}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  Add Claim
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create New Packet Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <form
            onSubmit={handleCreatePacket}
            className="bg-zinc-900 border border-zinc-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-400" />
                Create New Research Packet
              </h3>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-zinc-400 block mb-1">Research Topic / Headline</label>
                <input
                  type="text"
                  required
                  value={newTopic}
                  onChange={(e) => setNewTopic(e.target.value)}
                  placeholder="e.g. Local DeepSeek 67B Quantization on Apple Silicon M4 Max"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs text-zinc-400 block mb-1">
                  Source URLs (One per line)
                </label>
                <textarea
                  value={newSourcesText}
                  onChange={(e) => setNewSourcesText(e.target.value)}
                  placeholder="https://github.com/...\nhttps://arxiv.org/..."
                  rows={3}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs text-zinc-400 block mb-1">
                  Raw Document / Release Notes / Benchmark Text (Optional)
                </label>
                <textarea
                  value={newRawText}
                  onChange={(e) => setNewRawText(e.target.value)}
                  placeholder="Paste article text or benchmark tables here for deterministic extraction..."
                  rows={4}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500 font-mono text-[11px]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newTopic.trim() || actionLoading}
                  className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow disabled:opacity-50"
                >
                  Synthesize Packet
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default function ResearchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-zinc-500">Loading research engine...</div>}>
      <ResearchContent />
    </Suspense>
  );
}
