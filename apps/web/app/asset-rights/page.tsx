"use client";

import { useEffect, useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Ban,
  Plus,
  RefreshCw,
  Search,
  Copy,
  Check,
  Trash2,
  FileCheck,
  Sparkles,
  Info,
  Scale,
} from "lucide-react";
import {
  listAssetRights,
  getAssetRightsSummary,
  registerAssetRights,
  deleteAssetRights,
  seedStarterAssetRights,
  evaluateAssetRights,
  AssetRightsRecord,
  AssetRightsSummaryStats,
  AssetRightsVerdict,
} from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

export default function AssetRightsPage() {
  const { t } = useLanguage();
  const [assets, setAssets] = useState<AssetRightsRecord[]>([]);
  const [summary, setSummary] = useState<AssetRightsSummaryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Registration modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newType, setNewType] = useState("image");
  const [newSource, setNewSource] = useState("");
  const [newCreator, setNewCreator] = useState("");
  const [newLicense, setNewLicense] = useState("Self-Created");
  const [newAttribution, setNewAttribution] = useState("");
  const [newProof, setNewProof] = useState("");
  const [newNotes, setNewNotes] = useState("");

  // Live evaluator modal state
  const [isEvalOpen, setIsEvalOpen] = useState(false);
  const [evalTitle, setEvalTitle] = useState("");
  const [evalType, setEvalType] = useState("image");
  const [evalLicense, setEvalLicense] = useState("CC-BY-4.0");
  const [evalAttribution, setEvalAttribution] = useState("");
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<AssetRightsVerdict | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [records, stats] = await Promise.all([
        listAssetRights({ status: selectedStatus !== "all" ? selectedStatus : undefined }),
        getAssetRightsSummary(),
      ]);
      setAssets(records);
      setSummary(stats);
    } catch (err: any) {
      setError(err?.message || "Failed to load asset rights records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedStatus]);

  const handleSeedDefaults = async () => {
    try {
      setLoading(true);
      await seedStarterAssetRights();
      await loadData();
    } catch (err: any) {
      setError(err?.message || "Failed to seed defaults");
      setLoading(false);
    }
  };

  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newSource.trim()) return;

    setSubmitting(true);
    try {
      await registerAssetRights({
        title: newTitle.trim(),
        asset_type: newType,
        source: newSource.trim(),
        creator_provider: newCreator.trim() || undefined,
        license_type: newLicense.trim(),
        attribution_text: newAttribution.trim() || undefined,
        license_proof: newProof.trim() || undefined,
        notes: newNotes.trim() || undefined,
      });
      setIsModalOpen(false);
      // Reset form
      setNewTitle("");
      setNewSource("");
      setNewCreator("");
      setNewLicense("Self-Created");
      setNewAttribution("");
      setNewProof("");
      setNewNotes("");
      await loadData();
    } catch (err: any) {
      alert(err?.message || "Failed to create asset rights record.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to remove this asset rights record?")) return;
    try {
      await deleteAssetRights(id);
      await loadData();
    } catch (err: any) {
      alert(err?.message || "Failed to delete record.");
    }
  };

  const handleLiveEvaluate = async (e: React.FormEvent) => {
    e.preventDefault();
    setEvaluating(true);
    try {
      const verdict = await evaluateAssetRights({
        title: evalTitle || "Untitled Sample Asset",
        asset_type: evalType,
        source: "Live Evaluation Sandbox",
        license_type: evalLicense,
        attribution_text: evalAttribution || undefined,
      });
      setEvalResult(verdict);
    } catch (err: any) {
      alert(err?.message || "Evaluation failed.");
    } finally {
      setEvaluating(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredAssets = assets.filter((a) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.title.toLowerCase().includes(q) ||
      a.source.toLowerCase().includes(q) ||
      (a.creator_provider && a.creator_provider.toLowerCase().includes(q)) ||
      a.license_type.toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "VERIFIED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-3.5 h-3.5" />
            VERIFIED
          </span>
        );
      case "REQUIRES_ATTRIBUTION":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            ATTRIBUTION REQ.
          </span>
        );
      case "UNKNOWN":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
            <Info className="w-3.5 h-3.5" />
            UNKNOWN
          </span>
        );
      case "DO_NOT_USE":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Ban className="w-3.5 h-3.5" />
            DO NOT USE
          </span>
        );
      default:
        return <span className="text-xs text-slate-400">{status}</span>;
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Scale className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">
                {t("assetRightsPage.title", "Asset Rights & Provenance Registry")}
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                {t(
                  "assetRightsPage.subtitle",
                  "Track copyright documentation, commercial use status, and attribution requirements across visual, audio, code, and font assets."
                )}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setIsEvalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition"
          >
            <Sparkles className="w-4 h-4 text-amber-400" />
            {t("assetRightsPage.evalLive", "Live Rights Evaluator")}
          </button>
          <button
            onClick={handleSeedDefaults}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            {t("assetRightsPage.seedDefaults", "Load Starter Assets")}
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-md shadow-indigo-600/20 transition"
          >
            <Plus className="w-4 h-4" />
            {t("assetRightsPage.newAsset", "Register Asset")}
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
            <span className="text-xs font-medium text-slate-400">
              {t("assetRightsPage.statTotal", "Total Tracked")}
            </span>
            <p className="text-2xl font-bold text-white mt-1">{summary.total_assets}</p>
          </div>

          <div className="bg-emerald-950/20 border border-emerald-900/30 p-4 rounded-xl">
            <span className="text-xs font-medium text-emerald-400">
              {t("assetRightsPage.statVerified", "Verified Safe")}
            </span>
            <p className="text-2xl font-bold text-emerald-300 mt-1">{summary.verified}</p>
          </div>

          <div className="bg-amber-950/20 border border-amber-900/30 p-4 rounded-xl">
            <span className="text-xs font-medium text-amber-400">
              {t("assetRightsPage.statRequiresAttribution", "Attribution Req.")}
            </span>
            <p className="text-2xl font-bold text-amber-300 mt-1">{summary.requires_attribution}</p>
          </div>

          <div className="bg-yellow-950/20 border border-yellow-900/30 p-4 rounded-xl">
            <span className="text-xs font-medium text-yellow-400">
              {t("assetRightsPage.statUnknown", "Unknown License")}
            </span>
            <p className="text-2xl font-bold text-yellow-300 mt-1">{summary.unknown}</p>
          </div>

          <div className="bg-rose-950/20 border border-rose-900/30 p-4 rounded-xl">
            <span className="text-xs font-medium text-rose-400">
              {t("assetRightsPage.statBlocked", "Blocked (Do Not Use)")}
            </span>
            <p className="text-2xl font-bold text-rose-300 mt-1">{summary.do_not_use}</p>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 p-1 bg-slate-900/80 border border-slate-800 rounded-xl overflow-x-auto w-full sm:w-auto">
          {[
            { id: "all", label: t("assetRightsPage.filterAll", "All") },
            { id: "VERIFIED", label: t("assetRightsPage.filterVerified", "Verified") },
            { id: "REQUIRES_ATTRIBUTION", label: t("assetRightsPage.filterAttribution", "Requires Attribution") },
            { id: "UNKNOWN", label: t("assetRightsPage.filterUnknown", "Unknown") },
            { id: "DO_NOT_USE", label: t("assetRightsPage.filterBlocked", "Blocked") },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setSelectedStatus(f.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                selectedStatus === f.id
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search assets, creators..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Asset Table */}
      {loading ? (
        <div className="p-12 text-center text-slate-400">Loading asset rights records...</div>
      ) : filteredAssets.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center">
          <ShieldAlert className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400 text-sm">
            {t("assetRightsPage.emptyMessage", "No asset rights records found.")}
          </p>
          <button
            onClick={handleSeedDefaults}
            className="mt-4 px-4 py-2 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 text-xs font-medium hover:bg-indigo-600/30 transition"
          >
            {t("assetRightsPage.seedDefaults", "Load Starter Assets")}
          </button>
        </div>
      ) : (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 font-medium">
                <tr>
                  <th className="py-3 px-4">{t("assetRightsPage.tableTitle", "Asset Title")}</th>
                  <th className="py-3 px-4">{t("assetRightsPage.tableType", "Type")}</th>
                  <th className="py-3 px-4">{t("assetRightsPage.tableSource", "Source & Creator")}</th>
                  <th className="py-3 px-4">{t("assetRightsPage.tableLicense", "License")}</th>
                  <th className="py-3 px-4">{t("assetRightsPage.tableStatus", "Status")}</th>
                  <th className="py-3 px-4">{t("assetRightsPage.tableAttribution", "Attribution String")}</th>
                  <th className="py-3 px-4">{t("assetRightsPage.tableProof", "Proof / Notes")}</th>
                  <th className="py-3 px-4 text-right">{t("assetRightsPage.tableActions", "Actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {filteredAssets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 font-medium text-white max-w-xs truncate">
                      {asset.title}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/80 text-[11px] uppercase tracking-wider">
                        {asset.asset_type}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="text-slate-200">{asset.source}</div>
                      {asset.creator_provider && (
                        <div className="text-[11px] text-slate-400">{asset.creator_provider}</div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-[11px] text-indigo-300">{asset.license_type}</span>
                    </td>
                    <td className="py-3 px-4">{getStatusBadge(asset.status)}</td>
                    <td className="py-3 px-4 max-w-xs">
                      {asset.attribution_text ? (
                        <div className="flex items-center gap-1.5 group">
                          <span className="truncate text-slate-400 text-[11px]">
                            {asset.attribution_text}
                          </span>
                          <button
                            onClick={() => copyToClipboard(asset.attribution_text!, asset.id)}
                            className="text-slate-500 hover:text-slate-300 transition shrink-0"
                            title="Copy attribution string"
                          >
                            {copiedId === asset.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      ) : (
                        <span className="text-slate-600 text-[11px]">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 max-w-xs text-slate-400 text-[11px] truncate">
                      {asset.license_proof || asset.notes || "—"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDelete(asset.id)}
                        className="p-1 rounded hover:bg-rose-500/10 text-slate-500 hover:text-rose-400 transition"
                        title="Delete asset"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal: Register Media Asset */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-indigo-400" />
                {t("assetRightsPage.modalTitle", "Register Media Asset Provenance")}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateAsset} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">
                  {t("assetRightsPage.fieldTitle", "Asset Title")} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Synthwave Ambient Pad"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">
                    {t("assetRightsPage.fieldType", "Asset Type")}
                  </label>
                  <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="image">Image / Graphic</option>
                    <option value="bgm">Background Music (BGM)</option>
                    <option value="sfx">Sound Effect (SFX)</option>
                    <option value="font">Typography Font</option>
                    <option value="video">B-Roll Video</option>
                    <option value="chart">Benchmark Chart</option>
                    <option value="code">Code Snippet</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">
                    {t("assetRightsPage.fieldLicense", "License Type")}
                  </label>
                  <select
                    value={newLicense}
                    onChange={(e) => setNewLicense(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
                  >
                    <option value="Self-Created">Self-Created (Proprietary)</option>
                    <option value="CC0">CC0 (Public Domain)</option>
                    <option value="OFL-1.1">OFL-1.1 (Open Font)</option>
                    <option value="MIT">MIT License</option>
                    <option value="Apache-2.0">Apache 2.0</option>
                    <option value="Royalty-Free Commercial">Royalty-Free Commercial</option>
                    <option value="CC-BY-4.0">CC-BY 4.0 (Attribution)</option>
                    <option value="CC-BY-NC">CC-BY-NC (Non-Commercial - Blocked)</option>
                    <option value="Unknown">Unknown / Undocumented</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">
                    {t("assetRightsPage.fieldSource", "Source / Platform")} *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Free Music Archive"
                    value={newSource}
                    onChange={(e) => setNewSource(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">
                    {t("assetRightsPage.fieldCreator", "Creator / Provider")}
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Kevin MacLeod"
                    value={newCreator}
                    onChange={(e) => setNewCreator(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">
                  {t("assetRightsPage.fieldAttribution", "Attribution String")}
                </label>
                <input
                  type="text"
                  placeholder="e.g. 'Song Name' by Artist, CC-BY 4.0"
                  value={newAttribution}
                  onChange={(e) => setNewAttribution(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">
                  {t("assetRightsPage.fieldProof", "License Proof / Reference")}
                </label>
                <input
                  type="text"
                  placeholder="e.g. URL to license proof or invoice #12345"
                  value={newProof}
                  onChange={(e) => setNewProof(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">
                  {t("assetRightsPage.fieldNotes", "Notes / Description")}
                </label>
                <textarea
                  rows={2}
                  placeholder="Context on intended usage in video scenes..."
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition disabled:opacity-50"
                >
                  {submitting ? "Verifying..." : t("assetRightsPage.btnSave", "Save & Verify Provenance")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Live Rights Evaluator Sandbox */}
      {isEvalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                {t("assetRightsPage.evalLive", "Live Rights Evaluator")}
              </h3>
              <button
                onClick={() => {
                  setIsEvalOpen(false);
                  setEvalResult(null);
                }}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleLiveEvaluate} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Asset Name</label>
                <input
                  type="text"
                  placeholder="e.g. Sample Audio Track"
                  value={evalTitle}
                  onChange={(e) => setEvalTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Asset Type</label>
                  <select
                    value={evalType}
                    onChange={(e) => setEvalType(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="image">Image</option>
                    <option value="bgm">Background Music</option>
                    <option value="font">Font</option>
                    <option value="video">Video</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">License String</label>
                  <input
                    type="text"
                    placeholder="e.g. CC-BY-NC-4.0, MIT, CC0"
                    value={evalLicense}
                    onChange={(e) => setEvalLicense(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Attribution Credit (if known)</label>
                <input
                  type="text"
                  placeholder="e.g. by Artist Name"
                  value={evalAttribution}
                  onChange={(e) => setEvalAttribution(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                type="submit"
                disabled={evaluating}
                className="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition"
              >
                {evaluating ? "Evaluating..." : "Check Legal Rights"}
              </button>
            </form>

            {evalResult && (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-300">Evaluation Verdict:</span>
                  {getStatusBadge(evalResult.status)}
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  {evalResult.explanation}
                </p>

                {evalResult.warnings.length > 0 && (
                  <div className="space-y-1">
                    {evalResult.warnings.map((w, idx) => (
                      <p key={idx} className="text-[11px] text-amber-400 flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        {w}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
