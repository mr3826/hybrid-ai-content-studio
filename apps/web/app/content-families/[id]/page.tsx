"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Boxes,
  ArrowLeft,
  Sparkles,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  DollarSign,
  Cpu,
  Video,
  FileText,
  Share2,
  Mail,
  Trash2,
  Edit2,
  Link2,
  BookOpen,
  FlaskConical,
  ShieldCheck,
  ExternalLink,
  ChevronRight,
  Archive,
} from "lucide-react";
import {
  ContentFamilyDetail,
  ContentChildItem,
  ChildSuggestionProposal,
  getContentFamily,
  approveContentFamily,
  archiveContentFamily,
  suggestContentFamilyItems,
  createFamilyItem,
  updateContentItem,
  deleteContentItem,
  linkChildEvidence,
  unlinkChildEvidence,
  listClaims,
  Claim,
} from "@/lib/api";

const FORMAT_ICONS: Record<string, any> = {
  short_vertical: Video,
  youtube_long: Video,
  social_post: Share2,
  newsletter: Mail,
  article: FileText,
};

const HOOK_TYPES = [
  "bold_claim",
  "curiosity_gap",
  "problem_agitation",
  "surprising_stat",
  "story_open",
  "direct_value",
];

const PLATFORMS = ["youtube", "facebook", "instagram", "tiktok", "cross_platform", "none"];

export default function ContentFamilyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const familyId = params?.id as string;

  const [family, setFamily] = useState<ContentFamilyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Available claims for linking
  const [availableClaims, setAvailableClaims] = useState<Claim[]>([]);

  // Suggest modal state
  const [showSuggestModal, setShowSuggestModal] = useState(false);
  const [proposals, setProposals] = useState<ChildSuggestionProposal[]>([]);
  const [suggesting, setSuggesting] = useState(false);

  // Add / Edit Child Modal
  const [showChildModal, setShowChildModal] = useState(false);
  const [editingItem, setEditingItem] = useState<ContentChildItem | null>(null);
  const [itemFormat, setItemFormat] = useState("short_vertical");
  const [itemPlatform, setItemPlatform] = useState("youtube");
  const [itemTitle, setItemTitle] = useState("");
  const [itemAngle, setItemAngle] = useState("");
  const [itemHook, setItemHook] = useState("bold_claim");
  const [itemConnection, setItemConnection] = useState("");
  const [itemViewerValue, setItemViewerValue] = useState("");
  const [itemCost, setItemCost] = useState<number>(0);
  const [itemTime, setItemTime] = useState<number>(0);
  const [savingChild, setSavingChild] = useState(false);

  // Link Evidence Modal
  const [showLinkEvidenceModal, setShowLinkEvidenceModal] = useState(false);
  const [targetChildId, setTargetChildId] = useState<string>("");
  const [selectedClaimId, setSelectedClaimId] = useState<string>("");
  const [relevanceNote, setRelevanceNote] = useState("");
  const [isPrimaryClaim, setIsPrimaryClaim] = useState(false);
  const [linkingEvidence, setLinkingEvidence] = useState(false);

  useEffect(() => {
    if (familyId) {
      loadFamily();
    }
  }, [familyId]);

  async function loadFamily() {
    setLoading(true);
    setErrorBanner(null);
    try {
      const data = await getContentFamily(familyId);
      setFamily(data);

      // Load claims for linking
      const claimsData = await listClaims({ limit: 50 });
      setAvailableClaims(claimsData);
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to load Content Family.");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    try {
      await approveContentFamily(familyId);
      await loadFamily();
    } catch (err: any) {
      setErrorBanner(err?.message || "Approval failed.");
    }
  }

  async function handleArchive() {
    if (!confirm("Are you sure you want to archive this Content Family?")) return;
    try {
      await archiveContentFamily(familyId);
      router.push("/content-families");
    } catch (err: any) {
      setErrorBanner(err?.message || "Archival failed.");
    }
  }

  async function handleOpenSuggest() {
    setShowSuggestModal(true);
    setSuggesting(true);
    try {
      const res = await suggestContentFamilyItems(familyId);
      setProposals(res.proposals);
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to suggest items.");
    } finally {
      setSuggesting(false);
    }
  }

  async function handleApplyProposal(proposal: ChildSuggestionProposal) {
    try {
      await createFamilyItem(familyId, {
        format: proposal.format,
        platform_target: proposal.platform_target,
        working_title: proposal.working_title,
        angle: proposal.angle,
        hook_type: proposal.hook_type,
        original_value_connection: proposal.original_value_connection,
        viewer_value: proposal.viewer_value,
        status: "PLANNED",
      });
      // Remove from proposals list
      setProposals((prev) => prev.filter((p) => p.working_title !== proposal.working_title));
      await loadFamily();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to add child item.");
    }
  }

  function openAddModal() {
    setEditingItem(null);
    setItemFormat("short_vertical");
    setItemPlatform("youtube");
    setItemTitle("");
    setItemAngle("");
    setItemHook("bold_claim");
    setItemConnection(family?.title ? `Derived from ${family.title} empirical findings.` : "");
    setItemViewerValue("");
    setItemCost(0);
    setItemTime(0);
    setShowChildModal(true);
  }

  function openEditModal(item: ContentChildItem) {
    setEditingItem(item);
    setItemFormat(item.format);
    setItemPlatform(item.platform_target);
    setItemTitle(item.working_title);
    setItemAngle(item.angle);
    setItemHook(item.hook_type);
    setItemConnection(item.original_value_connection);
    setItemViewerValue(item.viewer_value);
    setItemCost(item.incremental_cost);
    setItemTime(item.manual_time_minutes);
    setShowChildModal(true);
  }

  async function handleSaveChild(e: React.FormEvent) {
    e.preventDefault();
    setSavingChild(true);
    setErrorBanner(null);
    try {
      if (editingItem) {
        await updateContentItem(editingItem.id, {
          format: itemFormat,
          platform_target: itemPlatform,
          working_title: itemTitle,
          angle: itemAngle,
          hook_type: itemHook,
          original_value_connection: itemConnection,
          viewer_value: itemViewerValue,
          incremental_cost: itemCost,
          manual_time_minutes: itemTime,
        });
      } else {
        await createFamilyItem(familyId, {
          format: itemFormat,
          platform_target: itemPlatform,
          working_title: itemTitle,
          angle: itemAngle,
          hook_type: itemHook,
          original_value_connection: itemConnection,
          viewer_value: itemViewerValue,
          incremental_cost: itemCost,
          manual_time_minutes: itemTime,
        });
      }
      setShowChildModal(false);
      await loadFamily();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to save child item.");
    } finally {
      setSavingChild(false);
    }
  }

  async function handleDeleteChild(itemId: string) {
    if (!confirm("Are you sure you want to remove this child item?")) return;
    try {
      await deleteContentItem(itemId);
      await loadFamily();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to delete child item.");
    }
  }

  async function handleLinkEvidenceSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!targetChildId || !selectedClaimId) return;
    setLinkingEvidence(true);
    try {
      await linkChildEvidence(targetChildId, {
        claim_id: selectedClaimId,
        relevance_note: relevanceNote || undefined,
        is_primary: isPrimaryClaim,
      });
      setShowLinkEvidenceModal(false);
      setSelectedClaimId("");
      setRelevanceNote("");
      setIsPrimaryClaim(false);
      await loadFamily();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to link evidence claim.");
    } finally {
      setLinkingEvidence(false);
    }
  }

  async function handleUnlinkEvidence(itemId: string, claimId: string) {
    try {
      await unlinkChildEvidence(itemId, claimId);
      await loadFamily();
    } catch (err: any) {
      setErrorBanner(err?.message || "Failed to unlink evidence.");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (!family) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-slate-400">Content Family not found.</p>
        <Link href="/content-families" className="text-indigo-400 hover:text-indigo-300 text-sm font-semibold">
          &larr; Back to Content Families
        </Link>
      </div>
    );
  }

  const econ = family.economics;

  return (
    <div className="space-y-6">
      {/* Back button and Header */}
      <div>
        <Link
          href="/content-families"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Content Families
        </Link>

        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {family.content_pillar}
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 uppercase font-mono">
                {family.original_value_type}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                  family.status === "READY_FOR_CONTENT"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : family.status === "ARCHIVED"
                    ? "bg-slate-800 text-slate-400 border border-slate-700"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}
              >
                {family.status}
              </span>
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Boxes className="w-6 h-6 text-indigo-400" />
              {family.title}
            </h1>
            <p className="text-xs text-slate-500 font-mono">slug: {family.slug}</p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleOpenSuggest}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Suggest Content Items
            </button>
            <button
              onClick={openAddModal}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Child Item
            </button>
            {family.status !== "READY_FOR_CONTENT" && family.status !== "ARCHIVED" && (
              <button
                onClick={handleApprove}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 shadow-sm"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Approve Family Plan
              </button>
            )}
            {family.status !== "ARCHIVED" && (
              <button
                onClick={handleArchive}
                className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                title="Archive Family"
              >
                <Archive className="w-4 h-4" />
              </button>
            )}
          </div>
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

      {/* Summary & Dependency Provenance Links */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-1">
            Empirical Core Finding & "What are WE adding?"
          </p>
          <p className="text-sm text-slate-200 leading-relaxed font-medium">
            {family.summary || "No empirical summary declared."}
          </p>
        </div>

        <div className="flex items-center gap-4 pt-3 border-t border-slate-800 text-xs text-slate-400 flex-wrap">
          <span className="font-semibold text-slate-300">Shared Foundation:</span>
          {family.research_packet_id ? (
            <Link
              href={`/research?packet_id=${family.research_packet_id}`}
              className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-medium"
            >
              <BookOpen className="w-3.5 h-3.5" />
              Research Packet &rarr;
            </Link>
          ) : (
            <span className="text-slate-500">No Research Packet</span>
          )}

          {family.originality_plan_id ? (
            <Link
              href="/originality"
              className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium"
            >
              <FlaskConical className="w-3.5 h-3.5" />
              Originality Plan &rarr;
            </Link>
          ) : (
            <span className="text-slate-500">No Originality Plan</span>
          )}

          {family.primary_experiment_id ? (
            <Link
              href="/originality"
              className="flex items-center gap-1 text-amber-400 hover:text-amber-300 font-medium"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Benchmark Experiment &rarr;
            </Link>
          ) : null}
        </div>
      </div>

      {/* Family Economics Summary Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-[11px] text-slate-400 font-medium">Shared Family Cost</p>
          <p className="text-lg font-bold text-white mt-0.5">${econ.shared_family_cost.toFixed(2)}</p>
          <p className="text-[10px] text-slate-500">Research + Experiment + AI</p>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-[11px] text-indigo-400 font-medium">Incremental Child Cost</p>
          <p className="text-lg font-bold text-indigo-300 mt-0.5">${econ.total_incremental_cost.toFixed(2)}</p>
          <p className="text-[10px] text-slate-500">Sum of {family.items.length} child assets</p>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-[11px] text-emerald-400 font-medium">Total Investment</p>
          <p className="text-lg font-bold text-emerald-300 mt-0.5">${econ.total_family_cost.toFixed(2)}</p>
          <p className="text-[10px] text-slate-500">Total production cost</p>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-[11px] text-amber-400 font-medium">Cost per Child Item</p>
          <p className="text-lg font-bold text-amber-300 mt-0.5">${econ.cost_per_child.toFixed(2)}</p>
          <p className="text-[10px] text-slate-500">Amortized efficiency</p>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
          <p className="text-[11px] text-slate-400 font-medium">Total Time & Compute</p>
          <p className="text-sm font-bold text-white mt-1">
            {econ.total_time_minutes}m <span className="text-slate-500 text-xs font-normal">/ {econ.total_compute_seconds}s</span>
          </p>
          <p className="text-[10px] text-slate-500">Manual editing + compute</p>
        </div>
      </div>

      {/* Child Content Items Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Video className="w-5 h-5 text-indigo-400" />
            Child Content Items ({family.items.length})
          </h2>
          <button
            onClick={openAddModal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Child Item
          </button>
        </div>

        {family.items.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl bg-slate-900/20 space-y-3">
            <Video className="w-10 h-10 text-slate-600 mx-auto" />
            <p className="text-slate-400 font-medium">No child items planned yet.</p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Use the "Suggest Content Items" tool to propose tailored Long-form video, Vertical Shorts, Social Cheat-Sheets, and Newsletters.
            </p>
            <button
              onClick={handleOpenSuggest}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600 hover:text-white transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Suggest Content Items
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {family.items.map((item) => {
              const Icon = FORMAT_ICONS[item.format] || Video;
              return (
                <div
                  key={item.id}
                  className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all space-y-3"
                >
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center gap-1">
                          <Icon className="w-3 h-3" />
                          {item.format.replace(/_/g, " ")}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                          {item.platform_target}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 font-mono">
                          {item.hook_type}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                          {item.status}
                        </span>
                      </div>

                      <h3 className="text-base font-bold text-white">{item.working_title}</h3>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <Link
                        href={`/script-studio/${item.id}`}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-purple-600/20 text-purple-300 hover:bg-purple-600/30 border border-purple-500/30 transition-colors"
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        Script Studio
                      </Link>
                      <button
                        onClick={() => {
                          setTargetChildId(item.id);
                          setShowLinkEvidenceModal(true);
                        }}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/30"
                      >
                        <Link2 className="w-3.5 h-3.5" />
                        Link Evidence
                      </button>
                      <button
                        onClick={() => openEditModal(item)}
                        className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
                        title="Edit Child"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDeleteChild(item.id)}
                        className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                        title="Delete Child"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Angle & Viewer Value */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded bg-slate-950/60 border border-slate-800/80">
                      <p className="font-semibold text-slate-300 mb-0.5">Child-Specific Angle</p>
                      <p className="text-slate-400 leading-relaxed">{item.angle}</p>
                    </div>
                    <div className="p-3 rounded bg-slate-950/60 border border-slate-800/80">
                      <p className="font-semibold text-slate-300 mb-0.5">Viewer Value & Takeaway</p>
                      <p className="text-slate-400 leading-relaxed">
                        {item.viewer_value || "Clear empirical learning or decision criterion."}
                      </p>
                    </div>
                  </div>

                  {/* Original Value Connection */}
                  {item.original_value_connection && (
                    <div className="text-xs p-2.5 rounded bg-indigo-950/20 border border-indigo-500/20 text-indigo-200">
                      <span className="font-semibold text-indigo-300">Original Value Connection: </span>
                      {item.original_value_connection}
                    </div>
                  )}

                  {/* Selected Evidence Claims */}
                  {item.evidence_selections && item.evidence_selections.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80">
                      <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        Selected Evidence Claims ({item.evidence_selections.length})
                      </p>
                      <div className="space-y-1.5">
                        {item.evidence_selections.map((sel) => (
                          <div
                            key={sel.id}
                            className="flex items-center justify-between gap-2 p-2 rounded bg-slate-950 border border-slate-800 text-xs text-slate-300"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                                {sel.claim_type || "claim"}
                              </span>
                              <span className="font-medium text-slate-200">{sel.claim_text}</span>
                              {sel.relevance_note && (
                                <span className="text-[11px] text-slate-500 italic">
                                  ({sel.relevance_note})
                                </span>
                              )}
                            </div>
                            <button
                              onClick={() => handleUnlinkEvidence(item.id, sel.claim_id)}
                              className="text-slate-500 hover:text-rose-400 text-xs font-bold"
                              title="Unlink"
                            >
                              &times;
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Economics Footer */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-[11px] text-slate-500">
                    <span>
                      Incremental Cost: <span className="text-slate-300 font-semibold">${item.incremental_cost.toFixed(2)}</span>
                    </span>
                    <span>
                      Manual Time: <span className="text-slate-300 font-semibold">{item.manual_time_minutes}m</span>
                    </span>
                    <span>
                      Local Compute: <span className="text-slate-300 font-semibold">{item.local_compute_seconds.toFixed(0)}s</span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* MODAL: SUGGEST CHILD ITEMS */}
      {showSuggestModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                Proposed Child Content Items
              </h2>
              <button
                onClick={() => setShowSuggestModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            {suggesting ? (
              <div className="py-12 text-center space-y-2">
                <RefreshCw className="w-6 h-6 text-indigo-500 animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Synthesizing distinct format & platform proposals...</p>
              </div>
            ) : proposals.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">All proposals have been added to the family!</p>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-slate-400">
                  Review and selectively add proposed assets to your Content Family. Each item is independently editable.
                </p>
                {proposals.map((prop, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2 hover:border-slate-700 transition-all"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                          {prop.format.replace(/_/g, " ")}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                          {prop.platform_target}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono text-amber-400 bg-amber-500/10">
                          {prop.hook_type}
                        </span>
                      </div>
                      <button
                        onClick={() => handleApplyProposal(prop)}
                        className="px-3 py-1 text-xs font-semibold rounded bg-indigo-600 text-white hover:bg-indigo-500 transition-colors shadow-sm"
                      >
                        + Add to Family
                      </button>
                    </div>

                    <h4 className="text-sm font-semibold text-white">{prop.working_title}</h4>
                    <p className="text-xs text-slate-300">{prop.angle}</p>
                    <p className="text-[11px] text-slate-400">
                      <span className="font-semibold text-indigo-400">Originality: </span>
                      {prop.original_value_connection}
                    </p>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowSuggestModal(false)}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: ADD / EDIT CHILD ITEM */}
      {showChildModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-4 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Video className="w-5 h-5 text-indigo-400" />
                {editingItem ? "Edit Child Item" : "Add Child Item to Family"}
              </h2>
              <button
                onClick={() => setShowChildModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveChild} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Asset Format *
                  </label>
                  <select
                    value={itemFormat}
                    onChange={(e) => setItemFormat(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  >
                    <option value="short_vertical">Short Vertical Video (15-60s)</option>
                    <option value="youtube_long">YouTube Long-form (6-30m)</option>
                    <option value="social_post">Social Post / Companion</option>
                    <option value="newsletter">Email Newsletter</option>
                    <option value="article">Technical Article</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Platform Target *
                  </label>
                  <select
                    value={itemPlatform}
                    onChange={(e) => setItemPlatform(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  >
                    {PLATFORMS.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Working Title *
                </label>
                <input
                  type="text"
                  required
                  value={itemTitle}
                  onChange={(e) => setItemTitle(e.target.value)}
                  placeholder="e.g. M4 Max Speed Benchmark Winner"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Hook Type *
                  </label>
                  <select
                    value={itemHook}
                    onChange={(e) => setItemHook(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  >
                    {HOOK_TYPES.map((h) => (
                      <option key={h} value={h}>
                        {h.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Incremental Cost ($)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={itemCost}
                    onChange={(e) => setItemCost(parseFloat(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Child-Specific Angle * (Min 15 chars)
                </label>
                <textarea
                  required
                  rows={2}
                  value={itemAngle}
                  onChange={(e) => setItemAngle(e.target.value)}
                  placeholder="Specific narrative angle distinct from other family children"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Original Value Connection *
                </label>
                <input
                  type="text"
                  required
                  value={itemConnection}
                  onChange={(e) => setItemConnection(e.target.value)}
                  placeholder="How this child reflects the family's 'What are WE adding?' contribution"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Viewer Value / Takeaway
                </label>
                <input
                  type="text"
                  value={itemViewerValue}
                  onChange={(e) => setItemViewerValue(e.target.value)}
                  placeholder="What actionable insight the viewer takes away"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowChildModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingChild}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
                >
                  {savingChild ? "Saving..." : editingItem ? "Update Item" : "Add Item"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: LINK EVIDENCE CLAIM */}
      {showLinkEvidenceModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Link2 className="w-5 h-5 text-indigo-400" />
                Select Evidence Claim from Foundation
              </h2>
              <button
                onClick={() => setShowLinkEvidenceModal(false)}
                className="text-slate-400 hover:text-white text-xs font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleLinkEvidenceSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Claim *
                </label>
                <select
                  required
                  value={selectedClaimId}
                  onChange={(e) => setSelectedClaimId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">-- Choose Claim --</option>
                  {availableClaims.map((c) => (
                    <option key={c.id} value={c.id}>
                      [{c.claim_type}] {c.text.slice(0, 75)}...
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Relevance Note (Optional)
                </label>
                <input
                  type="text"
                  value={relevanceNote}
                  onChange={(e) => setRelevanceNote(e.target.value)}
                  placeholder="e.g. Highlighted in opening hook and summary table"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-white"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="primaryCheck"
                  checked={isPrimaryClaim}
                  onChange={(e) => setIsPrimaryClaim(e.target.checked)}
                  className="rounded border-slate-800 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="primaryCheck" className="text-xs text-slate-300">
                  Primary focal claim for this child asset
                </label>
              </div>

              <p className="text-[11px] text-slate-500 bg-slate-950 p-2.5 rounded border border-slate-800">
                Child items reference claims without duplicating records. This maintains end-to-end factual provenance back to primary sources.
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
                  disabled={linkingEvidence || !selectedClaimId}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
                >
                  {linkingEvidence ? "Linking..." : "Link Evidence"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
