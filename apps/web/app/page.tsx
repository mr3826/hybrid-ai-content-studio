import { 
  CheckCircle2, 
  ExternalLink, 
  Layers, 
  Cpu, 
  ShieldCheck, 
  FileVideo, 
  Flame, 
  ArrowRight
} from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-8">
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
            Bootstrap Phase Active
          </span>
        </div>
      </div>

      {/* Metrics & Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Active Niche</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-base font-semibold text-white">AI Engineering</div>
          <div className="text-xs text-slate-400 mt-1">Single-Niche Profile</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Brand DNA</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-base font-semibold text-white">Practical AI Studio</div>
          <div className="text-xs text-slate-400 mt-1">Evidence-driven tone</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Feature Engines</span>
            <Cpu className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-base font-semibold text-white">13 Independent</div>
          <div className="text-xs text-slate-400 mt-1">Contract-driven isolation</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Publishing Model</span>
            <ExternalLink className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-base font-semibold text-white">Manual Browser V1</div>
          <div className="text-xs text-slate-400 mt-1">1-Click Launchers</div>
        </div>
      </div>

      {/* Two Column Layout: Invariants & Platform Launcher Preview */}
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
              <span><strong>One Niche Only:</strong> Dedicated focus; no multi-tenant workspace clutter.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>One Brand Voice:</strong> Strict vocabulary rules, banned hype clichés, and claim standards.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>Evidence-Driven:</strong> Every story requires an original test, benchmark, or verified synthesis.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span><strong>Zero CI/CD & No n8n:</strong> 100% local operation with SQLite WAL and dedicated worker daemon.</span>
            </li>
          </ul>
        </div>

        {/* Platform Launchers Card */}
        <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <ExternalLink className="w-5 h-5 text-indigo-400" />
            Platform Launchers (Manual V1)
          </h2>
          <p className="text-xs text-slate-400">
            One-click HTTPS new-tab launchers for direct upload in authenticated browser sessions.
          </p>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <a
              href="https://studio.youtube.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-xs font-medium text-slate-200 border border-slate-700/60 transition-colors"
            >
              <span>YouTube Studio</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
            <a
              href="https://www.facebook.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-xs font-medium text-slate-200 border border-slate-700/60 transition-colors"
            >
              <span>Facebook Page</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
            <a
              href="https://www.instagram.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-xs font-medium text-slate-200 border border-slate-700/60 transition-colors"
            >
              <span>Instagram</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
            <a
              href="https://www.tiktok.com/upload"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-xs font-medium text-slate-200 border border-slate-700/60 transition-colors"
            >
              <span>TikTok Upload</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
