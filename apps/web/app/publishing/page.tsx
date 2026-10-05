"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  CheckCircle2,
  ExternalLink,
  FileArchive,
  FileCheck,
  FolderArchive,
  Layers,
  RefreshCw,
  Send,
  Share2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { PublishableItemSummary, listPublishableItems } from "@/lib/api";
import { getPlatformIcon } from "@/components/PlatformIcons";
import { useLanguage } from "@/lib/LanguageContext";

export default function PublishingHubPage() {
  const { t } = useLanguage();
  const [items, setItems] = useState<PublishableItemSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const loadData = async (filter?: string) => {
    try {
      setLoading(true);
      const data = await listPublishableItems(filter);
      setItems(data);
    } catch (e) {
      console.error("Failed to load publishable items:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(filterStatus);
  }, [filterStatus]);

  const readyToPublishCount = items.filter((i) => i.status === "READY_TO_PUBLISH").length;
  const partiallyPublishedCount = items.filter((i) => i.status === "PARTIALLY_PUBLISHED").length;
  const publishedCount = items.filter((i) => i.status === "PUBLISHED").length;
  const exportedCount = items.filter((i) => i.has_export).length;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1 font-mono">
              <Share2 className="w-3.5 h-3.5" />
              {t("publishing.phaseNotice", "Phase 13 Active")}
            </span>
            <span className="text-xs text-slate-500">&bull;</span>
            <span className="text-xs text-slate-400 font-mono">
              {t("publishing.manualNotice", "Manual Platform Publishing")}
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            {t("publishing.title", "Publishing Hub & Platform Launchers")}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            {t("publishing.subtitle", "Manage offline export packages, 7-point pre-flight checklists, copyable metadata, and browser distribution launchers.")}
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Link
            href="/settings"
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition flex items-center gap-1.5"
          >
            {t("publishing.configureChannels", "Configure Channels →")}
          </Link>
          <button
            onClick={() => loadData(filterStatus)}
            disabled={loading}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition"
            title={t("common.refresh", "Refresh")}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
            {t("publishing.exportedPackages", "Offline Packages")}
          </span>
          <div className="mt-2 text-2xl font-bold text-white flex items-baseline gap-2">
            {exportedCount}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30">
          <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider block">
            {t("publishing.readyToPublish", "Ready to Publish")}
          </span>
          <div className="mt-2 text-2xl font-bold text-amber-400 flex items-baseline gap-2">
            {readyToPublishCount}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-sky-950/20 border border-sky-500/30">
          <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider block">
            {t("publishing.partiallyPublished", "Partially Published")}
          </span>
          <div className="mt-2 text-2xl font-bold text-sky-400 flex items-baseline gap-2">
            {partiallyPublishedCount}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider block">
            {t("publishing.fullyPublished", "Fully Published")}
          </span>
          <div className="mt-2 text-2xl font-bold text-emerald-400 flex items-baseline gap-2">
            {publishedCount}
          </div>
        </div>
      </div>

      {/* Invariant Reminder Banner */}
      <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80 flex items-start gap-3">
        <Sparkles className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-400 leading-relaxed space-y-1">
          <span className="font-semibold text-slate-200">Strict Studio Publishing Invariants: </span>
          <span>
            Automated social API auto-posting is strictly forbidden. All publishing actions open the verified HTTPS channel URLs in your normal browser (<code>target="_blank"</code>, <code>rel="noopener noreferrer"</code>) with pre-formatted title, caption, and hashtags copied to your clipboard.
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-medium">Status Filter:</span>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-medium"
          >
            <option value="all">All Publishable Items</option>
            <option value="SCRIPT_APPROVED">SCRIPT_APPROVED (Ready for Export)</option>
            <option value="EXPORTED">EXPORTED (Package Assembled)</option>
            <option value="READY_TO_PUBLISH">READY_TO_PUBLISH (Pre-flight Passed)</option>
            <option value="PARTIALLY_PUBLISHED">PARTIALLY_PUBLISHED</option>
            <option value="PUBLISHED">PUBLISHED</option>
          </select>
        </div>

        <p className="text-xs text-slate-500">
          Showing {items.length} items
        </p>
      </div>

      {/* Items List */}
      {items.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-slate-800 rounded-2xl bg-slate-900/20 space-y-3">
          <Share2 className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-slate-300">No Publishable Items Found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Items reach the Publishing Hub once their script is reviewed and approved in Script Studio.
          </p>
          <div className="pt-2">
            <Link
              href="/content-families"
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm"
            >
              Open Content Families &rarr;
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {items.map((item) => (
            <div
              key={item.id}
              className={`p-5 rounded-xl border transition-all ${
                item.status === "PUBLISHED"
                  ? "bg-slate-900/60 border-emerald-500/30"
                  : item.status === "READY_TO_PUBLISH"
                  ? "bg-slate-900/80 border-amber-500/30"
                  : "bg-slate-900/40 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">
                      {item.format.replace(/_/g, " ")}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                      Target: {item.platform_target}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-bold border font-mono ${
                        item.status === "PUBLISHED"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                          : item.status === "PARTIALLY_PUBLISHED"
                          ? "bg-sky-500/10 text-sky-400 border-sky-500/30"
                          : item.status === "READY_TO_PUBLISH"
                          ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                          : "bg-slate-800 text-slate-300 border-slate-700"
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-white truncate">{item.working_title}</h3>

                  <div className="flex items-center gap-3 text-xs text-slate-400 flex-wrap">
                    {item.family_title && (
                      <span className="flex items-center gap-1 text-slate-400">
                        <Boxes className="w-3.5 h-3.5 text-indigo-400" />
                        Family: {item.family_title}
                      </span>
                    )}

                    {item.has_export ? (
                      <span className="flex items-center gap-1 text-emerald-400 font-mono text-[11px]">
                        <FolderArchive className="w-3.5 h-3.5" />
                        {item.export_slug}
                      </span>
                    ) : (
                      <span className="text-amber-400/80 text-[11px]">
                        &bull; Pending Package Assembly
                      </span>
                    )}
                  </div>
                </div>

                {/* Platform Status Indicators & Action */}
                <div className="flex flex-col sm:flex-row sm:items-center gap-4 shrink-0">
                  <div className="flex items-center gap-1.5 bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                    {["youtube", "facebook", "instagram", "tiktok"].map((p) => {
                      const pStatus = item.platform_statuses[p] || "NOT_READY";
                      return (
                        <div
                          key={p}
                          title={`${p.toUpperCase()}: ${pStatus}`}
                          className={`p-1.5 rounded flex items-center gap-1 text-xs font-mono ${
                            pStatus === "PUBLISHED"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : pStatus === "READY"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : pStatus === "SKIPPED"
                              ? "bg-slate-800/40 text-slate-600 line-through"
                              : "bg-slate-800/60 text-slate-500"
                          }`}
                        >
                          {getPlatformIcon(p, "w-3.5 h-3.5")}
                        </div>
                      );
                    })}
                  </div>

                  <Link
                    href={`/publishing/${item.id}`}
                    className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 shadow-md shadow-indigo-600/20 transition-colors"
                  >
                    <span>Open Assistant</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
