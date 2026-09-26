"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink, 
  Layers, 
  Cpu, 
  ShieldCheck, 
  Sparkles, 
  ArrowRight,
  RefreshCw
} from "lucide-react";
import { getStudioStatus, getPlatforms, StudioStatus, PlatformSetting } from "@/lib/api";

export default function DashboardPage() {
  const [status, setStatus] = useState<StudioStatus | null>(null);
  const [platforms, setPlatforms] = useState<Record<string, PlatformSetting>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [statusData, platformsData] = await Promise.all([
          getStudioStatus(),
          getPlatforms(),
        ]);
        if (statusData) setStatus(statusData);
        if (platformsData) setPlatforms(platformsData);
      } catch (e) {
        console.error("Dashboard data load error:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* First-Run Setup Notice Banner if setup is incomplete */}
      {!loading && status && !status.is_setup_completed && (
        <div className="p-5 rounded-2xl bg-amber-950/40 border border-amber-800/60 flex items-center justify-between">
          <div className="flex items-center gap-3.5">
            <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 shrink-0">
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-amber-200">First-Run Setup Required</h2>
              <p className="text-xs text-amber-300/80 mt-0.5">
                {!status.niche_configured && !status.brand_configured
                  ? "Single Niche and Brand profiles must be configured before discovery and content engines unlock."
                  : !status.niche_configured
                  ? "Configure your single niche profile in Settings to enable RSS & Trends discovery."
                  : "Configure your brand profile in Settings to enable content & script generation."}
              </p>
            </div>
          </div>
          <Link
            href="/settings"
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-md shadow-amber-500/20 transition-colors shrink-0"
          >
            <span>Complete Setup</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Hero Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-950 border border-indigo-900/30">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white mb-2">
              Fresh Local AI Content Studio
            </h1>
            <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
              Converting niche-specific signals into verified, brand-consistent content packages with rigorous human approval gates and local-first execution.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
            Phase 1 Active &bull; Foundation
          </span>
        </div>
      </div>

      {/* Metrics & Quality Gates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Niche Card */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Active Niche</span>
            <ShieldCheck className={`w-4 h-4 ${status?.niche_configured ? "text-emerald-400" : "text-amber-400"}`} />
          </div>
          <div className="text-base font-semibold text-white truncate">
            {status?.active_niche_name || "Unconfigured"}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            {status?.niche_configured ? "Single-Niche Locked" : "Setup needed"}
          </div>
        </div>

        {/* Brand Card */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Brand DNA</span>
            <Layers className={`w-4 h-4 ${status?.brand_configured ? "text-indigo-400" : "text-amber-400"}`} />
          </div>
          <div className="text-base font-semibold text-white truncate">
            {status?.active_brand_name || "Unconfigured"}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            {status?.brand_configured ? "Brand Consistency Active" : "Setup needed"}
          </div>
        </div>

        {/* Discovery Gate */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Discovery Gate</span>
            <Cpu className={`w-4 h-4 ${status?.discovery_ready ? "text-emerald-400" : "text-slate-600"}`} />
          </div>
          <div className="text-base font-semibold text-white">
            {status?.discovery_ready ? "Ready" : "Blocked (Niche)"}
          </div>
          <div className="text-xs text-slate-400 mt-1">RSS & Trends Guard</div>
        </div>

        {/* Content Gate */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Content Gate</span>
            <Sparkles className={`w-4 h-4 ${status?.generation_ready ? "text-emerald-400" : "text-slate-600"}`} />
          </div>
          <div className="text-base font-semibold text-white">
            {status?.generation_ready ? "Ready" : "Blocked (Brand)"}
          </div>
          <div className="text-xs text-slate-400 mt-1">Brand QA & Scripts</div>
        </div>
      </div>

      {/* Two Column Layout: Invariants & Platform Launchers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Invariants Card */}
        <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
            Architectural Guarantees
          </h2>
          <ul className="space-y-3 text-sm text-slate-300">
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>One Niche Only:</strong> Dedicated focus; multi-tenant workspace clutter is strictly forbidden.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>One Brand Voice:</strong> Strict vocabulary rules, banned hype clichés, and claim standards.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>Human Quality Gates:</strong> Mandatory human verification at topic, research, and script stages.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>Zero CI/CD & No n8n:</strong> 100% local operation with SQLite WAL and dedicated worker daemon.</span>
            </li>
          </ul>
        </div>

        {/* Platform Launchers Card */}
        <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <ExternalLink className="w-5 h-5 text-indigo-400" />
              Platform Launchers (Manual V1)
            </h2>
            <Link href="/settings" className="text-xs text-indigo-400 hover:text-indigo-300">
              Configure URLs &rarr;
            </Link>
          </div>
          <p className="text-xs text-slate-400">
            One-click HTTPS new-tab launchers for direct upload in authenticated browser sessions.
          </p>

          <div className="grid grid-cols-2 gap-3 pt-2">
            {["youtube", "facebook", "instagram", "tiktok"].map((pName) => {
              const p = platforms[pName];
              const targetUrl = p?.publishing_url || p?.channel_url || "https://studio.youtube.com/";

              return (
                <a
                  key={pName}
                  href={targetUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-xs font-medium text-slate-200 border border-slate-700/60 transition-colors"
                >
                  <span className="capitalize">{pName}</span>
                  <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                </a>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
