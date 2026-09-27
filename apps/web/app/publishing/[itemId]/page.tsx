"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  Copy,
  ExternalLink,
  FileArchive,
  FileText,
  FolderArchive,
  RefreshCw,
  Share2,
  ShieldCheck,
  AlertTriangle,
  Check,
  Clock,
  Video,
  FileCheck,
  Hash,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { getPlatformIcon } from "@/components/PlatformIcons";
import {
  PublishingOverview,
  PlatformPublicationData,
  ExportPackageData,
  getPublishingOverview,
  createExportPackage,
  updatePlatformPublication,
  getExportDownloadUrl,
} from "@/lib/api";

const PLATFORM_COLORS: Record<string, { bg: string; text: string; border: string; btn: string }> = {
  youtube: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/30",
    btn: "bg-red-600 hover:bg-red-500 text-white",
  },
  facebook: {
    bg: "bg-blue-500/10",
    text: "text-blue-400",
    border: "border-blue-500/30",
    btn: "bg-blue-600 hover:bg-blue-500 text-white",
  },
  instagram: {
    bg: "bg-pink-500/10",
    text: "text-pink-400",
    border: "border-pink-500/30",
    btn: "bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white",
  },
  tiktok: {
    bg: "bg-cyan-500/10",
    text: "text-cyan-400",
    border: "border-cyan-500/30",
    btn: "bg-cyan-600 hover:bg-cyan-500 text-white",
  },
};

const CHECKLIST_LABELS: Record<string, string> = {
  media_ready: "Final Media Render Ready",
  thumbnail_ready: "High-CTR Thumbnail Ready",
  title_caption_ready: "Platform Title & Caption Finalized",
  sources_checked: "Sources & Citations Fact-Checked",
  affiliate_disclosure_needed: "Affiliate Disclosures Declared",
  ai_disclosure_recommended: "AI Tool Transparency Disclosed",
  asset_rights_verified: "Visual & Audio Rights Verified",
};

export default function PublishingAssistantPage({
  params,
}: {
  params: Promise<{ itemId: string }>;
}) {
  const resolvedParams = use(params);
  const itemId = resolvedParams.itemId;

  const [overview, setOverview] = useState<PublishingOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [savingPlatform, setSavingPlatform] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Form states per publication ID
  const [formValues, setFormValues] = useState<
    Record<
      string,
      {
        status: string;
        post_url: string;
        platform_post_id: string;
        notes: string;
        checklist: Record<string, boolean>;
      }
    >
  >({});

  const loadOverview = async () => {
    try {
      setLoading(true);
      setErrorBanner(null);
      const data = await getPublishingOverview(itemId);
      setOverview(data);

      // Initialize form values
      const initialForms: Record<string, any> = {};
      data.publications.forEach((pub) => {
        initialForms[pub.id] = {
          status: pub.status,
          post_url: pub.post_url || "",
          platform_post_id: pub.platform_post_id || "",
          notes: pub.notes || "",
          checklist: {
            media_ready: false,
            thumbnail_ready: false,
            title_caption_ready: true,
            sources_checked: true,
            affiliate_disclosure_needed: false,
            ai_disclosure_recommended: true,
            asset_rights_verified: true,
            ...(pub.checklist || {}),
          },
        };
      });
      setFormValues(initialForms);
    } catch (err: any) {
      console.error("Failed to load publishing overview:", err);
      setErrorBanner(err.message || "Failed to load publishing assistant.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOverview();
  }, [itemId]);

  const handleCopy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    } catch (e) {
      console.error("Copy failed:", e);
    }
  };

  const handleGenerateExport = async () => {
    try {
      setGenerating(true);
      setErrorBanner(null);
      await createExportPackage(itemId);
      setSuccessBanner("Export package successfully generated with offline markdown and manifest files!");
      await loadOverview();
    } catch (err: any) {
      setErrorBanner(err.message || "Export package generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  const handleChecklistToggle = (pubId: string, checkKey: string) => {
    setFormValues((prev) => {
      const current = prev[pubId] || { checklist: {} };
      const currentVal = !!current.checklist[checkKey];
      return {
        ...prev,
        [pubId]: {
          ...current,
          checklist: {
            ...current.checklist,
            [checkKey]: !currentVal,
          },
        },
      };
    });
  };

  const handleSavePublication = async (pubId: string) => {
    const fv = formValues[pubId];
    if (!fv) return;

    if (fv.status === "PUBLISHED" && (!fv.post_url || !fv.post_url.startsWith("https://"))) {
      setErrorBanner("A valid HTTPS post URL is required to mark a platform as PUBLISHED.");
      return;
    }

    try {
      setSavingPlatform(pubId);
      setErrorBanner(null);
      await updatePlatformPublication(pubId, {
        status: fv.status as any,
        post_url: fv.post_url || undefined,
        platform_post_id: fv.platform_post_id || undefined,
        notes: fv.notes || undefined,
        checklist: fv.checklist,
      });
      setSuccessBanner("Publication record successfully updated!");
      await loadOverview();
    } catch (err: any) {
      setErrorBanner(err.message || "Failed to update publication record.");
    } finally {
      setSavingPlatform(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
          <p className="text-sm text-slate-400">Loading Publishing Assistant...</p>
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="p-8 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h2 className="text-lg font-bold text-white">Item Not Found</h2>
        <p className="text-sm text-slate-400">Content item {itemId} could not be loaded.</p>
        <Link
          href="/publishing"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-800 text-white rounded-lg text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Publishing
        </Link>
      </div>
    );
  }

  const { content_item, export_package, publications, platform_launch_urls } = overview;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-16">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Link
              href={`/script-studio/${content_item.id}`}
              className="hover:text-indigo-400 transition-colors flex items-center gap-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Script Studio
            </Link>
            <span>&bull;</span>
            <Link
              href={`/content-families/${content_item.content_family_id}`}
              className="hover:text-indigo-400 transition-colors"
            >
              Parent Family
            </Link>
            <span>&bull;</span>
            <span>Manual Publishing Assistant</span>
          </div>
          <div className="flex items-center gap-3 flex-wrap pt-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {content_item.working_title}
            </h1>
            <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">
              {content_item.format.replace(/_/g, " ")}
            </span>
            <span
              className={`px-2.5 py-0.5 rounded text-xs font-bold border font-mono ${
                content_item.status === "PUBLISHED"
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : content_item.status === "PARTIALLY_PUBLISHED"
                  ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
                  : content_item.status === "READY_TO_PUBLISH"
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                  : "bg-slate-800 text-slate-300 border-slate-700"
              }`}
            >
              {content_item.status}
            </span>
          </div>
        </div>

        {/* Global Action Bar */}
        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          {export_package && (
            <a
              href={getExportDownloadUrl(content_item.id)}
              download
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700 transition-colors shadow-sm"
            >
              <FileArchive className="w-4 h-4 text-amber-400" />
              Download ZIP Package
            </a>
          )}
          <button
            onClick={handleGenerateExport}
            disabled={generating}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-md shadow-indigo-600/20 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${generating ? "animate-spin" : ""}`} />
            {export_package ? "Re-generate Package" : "Generate Export Package"}
          </button>
        </div>
      </div>

      {/* Alert Banners */}
      {errorBanner && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-sm flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorBanner}</span>
          </div>
          <button onClick={() => setErrorBanner(null)} className="text-xs font-bold text-rose-400 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {successBanner && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-200 text-sm flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <span>{successBanner}</span>
          </div>
          <button onClick={() => setSuccessBanner(null)} className="text-xs font-bold text-emerald-400 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Export Package Card */}
      <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <FolderArchive className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white">Offline Export Package</h2>
                {export_package ? (
                  <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Compiled & Checksummed
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Pending Package Generation
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {export_package
                  ? `Stored locally at ${export_package.export_dir}`
                  : "Click 'Generate Export Package' above to assemble sources, script, asset requirements, and social files."}
              </p>
            </div>
          </div>

          {export_package && (
            <div className="text-right text-xs space-y-0.5">
              <div className="text-slate-400">
                SHA-256: <span className="font-mono text-slate-200">{export_package.checksum.substring(0, 16)}...</span>
              </div>
              <div className="text-slate-500 text-[11px]">
                {export_package.files.length} verified files &bull; {new Date(export_package.created_at).toLocaleString()}
              </div>
            </div>
          )}
        </div>

        {/* Files Badges */}
        {export_package && (
          <div className="pt-3 border-t border-slate-800/80 flex items-center gap-2 flex-wrap text-xs">
            <span className="text-slate-400 font-medium">Included Files:</span>
            {export_package.files.map((file) => (
              <span
                key={file}
                className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 flex items-center gap-1.5"
              >
                <FileText className="w-3 h-3 text-indigo-400" />
                {file}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Platform Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {publications.map((pub) => {
          const colors = PLATFORM_COLORS[pub.platform] || PLATFORM_COLORS.youtube;
          const fv = formValues[pub.id] || {
            status: pub.status,
            post_url: "",
            platform_post_id: "",
            notes: "",
            checklist: {},
          };
          const launchUrl = platform_launch_urls[pub.platform] || "https://studio.youtube.com/";
          const isSaving = savingPlatform === pub.id;

          return (
            <div
              key={pub.id}
              className={`p-6 rounded-2xl bg-slate-900/60 border transition-all space-y-5 ${
                pub.status === "PUBLISHED"
                  ? "border-emerald-500/30"
                  : pub.status === "READY"
                  ? "border-amber-500/30"
                  : "border-slate-800"
              }`}
            >
              {/* Card Header */}
              <div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${colors.bg} ${colors.text} border ${colors.border}`}>
                    {getPlatformIcon(pub.platform, "w-5 h-5")}
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white capitalize">{pub.platform} Publishing</h3>
                    <p className="text-xs text-slate-400">Manual launcher & metadata copy card</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded text-xs font-bold border font-mono uppercase ${
                      pub.status === "PUBLISHED"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                        : pub.status === "READY"
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                        : pub.status === "SKIPPED"
                        ? "bg-slate-800 text-slate-400 border-slate-700"
                        : "bg-slate-800 text-slate-300 border-slate-700"
                    }`}
                  >
                    {pub.status}
                  </span>
                </div>
              </div>

              {/* One-Click Copy Buttons Section */}
              <div className="space-y-3">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Copy className="w-3.5 h-3.5 text-indigo-400" />
                  One-Click Copyable Metadata
                </p>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {pub.title && (
                    <button
                      onClick={() => handleCopy(pub.title, `${pub.id}-title`)}
                      className="px-3 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 flex items-center justify-between transition-colors"
                    >
                      <span className="truncate mr-2">Copy Title</span>
                      {copiedKey === `${pub.id}-title` ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      )}
                    </button>
                  )}

                  {pub.caption && (
                    <button
                      onClick={() => handleCopy(pub.caption, `${pub.id}-caption`)}
                      className="px-3 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 flex items-center justify-between transition-colors"
                    >
                      <span className="truncate mr-2">Copy Caption</span>
                      {copiedKey === `${pub.id}-caption` ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      )}
                    </button>
                  )}

                  {pub.hashtags && pub.hashtags.length > 0 && (
                    <button
                      onClick={() => handleCopy(pub.hashtags.join(" "), `${pub.id}-hashtags`)}
                      className="px-3 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 flex items-center justify-between transition-colors"
                    >
                      <span className="truncate mr-2">Copy Hashtags</span>
                      {copiedKey === `${pub.id}-hashtags` ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : (
                        <Hash className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      )}
                    </button>
                  )}

                  {pub.pinned_comment && (
                    <button
                      onClick={() => handleCopy(pub.pinned_comment, `${pub.id}-pinned`)}
                      className="px-3 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 flex items-center justify-between transition-colors"
                    >
                      <span className="truncate mr-2">Copy Comment</span>
                      {copiedKey === `${pub.id}-pinned` ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : (
                        <MessageSquare className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      )}
                    </button>
                  )}
                </div>

                {/* Previews */}
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2 text-xs">
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 block mb-0.5">
                      Tailored Title ({pub.title.length} chars):
                    </span>
                    <p className="text-slate-200 font-medium">{pub.title || "(None)"}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 block mb-0.5">
                      Tailored Caption / Description:
                    </span>
                    <p className="text-slate-300 font-mono text-[11px] line-clamp-3 whitespace-pre-line">
                      {pub.caption || "(None)"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Platform Launcher Button */}
              <div>
                <a
                  href={launchUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-md ${colors.btn}`}
                >
                  {getPlatformIcon(pub.platform, "w-4 h-4")}
                  <span>Open {pub.platform.toUpperCase()} in Browser</span>
                  <ExternalLink className="w-3.5 h-3.5 opacity-80" />
                </a>
                <p className="text-[11px] text-slate-500 text-center mt-1.5">
                  Opens authenticated studio URL in a new browser tab ({launchUrl}). No iframe embeds.
                </p>
              </div>

              {/* 7-Point Publishing Checklist */}
              <div className="space-y-2.5 pt-2 border-t border-slate-800">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  7-Point Pre-Publication Checklist
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {Object.entries(CHECKLIST_LABELS).map(([key, label]) => {
                    const isChecked = !!fv.checklist[key];
                    return (
                      <label
                        key={key}
                        onClick={() => handleChecklistToggle(pub.id, key)}
                        className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer select-none transition-all ${
                          isChecked
                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                            : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          className="rounded border-slate-700 text-emerald-500 focus:ring-0 bg-slate-900"
                        />
                        <span className="text-[11px] font-medium leading-tight">{label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Manual Publication Record Form */}
              <div className="space-y-3 pt-2 border-t border-slate-800">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Publication State & Audit Record
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1 font-medium">Platform Status</label>
                    <select
                      value={fv.status}
                      onChange={(e) =>
                        setFormValues((prev) => ({
                          ...prev,
                          [pub.id]: { ...prev[pub.id], status: e.target.value },
                        }))
                      }
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    >
                      <option value="NOT_READY">NOT_READY</option>
                      <option value="READY">READY</option>
                      <option value="PUBLISHED">PUBLISHED</option>
                      <option value="SKIPPED">SKIPPED</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-400 mb-1 font-medium">Platform Post ID (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. dQw4w9WgXcQ"
                      value={fv.platform_post_id}
                      onChange={(e) =>
                        setFormValues((prev) => ({
                          ...prev,
                          [pub.id]: { ...prev[pub.id], platform_post_id: e.target.value },
                        }))
                      }
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1 text-xs font-medium">
                    Published Post URL (Required for PUBLISHED)
                  </label>
                  <input
                    type="url"
                    placeholder="https://..."
                    value={fv.post_url}
                    onChange={(e) =>
                      setFormValues((prev) => ({
                        ...prev,
                        [pub.id]: { ...prev[pub.id], post_url: e.target.value },
                      }))
                    }
                    className={`w-full bg-slate-950 border rounded-lg px-3 py-2 text-xs text-white focus:outline-none ${
                      fv.status === "PUBLISHED" && (!fv.post_url || !fv.post_url.startsWith("https://"))
                        ? "border-rose-500/50 focus:border-rose-500"
                        : "border-slate-800 focus:border-indigo-500"
                    }`}
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1 text-xs font-medium">Notes & Context</label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Uploaded at 3pm, pinned discussion comment in thread."
                    value={fv.notes}
                    onChange={(e) =>
                      setFormValues((prev) => ({
                        ...prev,
                        [pub.id]: { ...prev[pub.id], notes: e.target.value },
                      }))
                    }
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex items-center justify-between pt-1">
                  <div className="text-[11px] text-slate-500">
                    {pub.published_at
                      ? `Published at ${new Date(pub.published_at).toLocaleString()}`
                      : "Not published yet"}
                  </div>
                  <button
                    onClick={() => handleSavePublication(pub.id)}
                    disabled={isSaving}
                    className="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
                  >
                    {isSaving ? "Saving..." : "Save Record"}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
