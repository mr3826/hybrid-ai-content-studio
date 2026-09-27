import Link from "next/link";
import { Compass, ShieldAlert, ArrowRight } from "lucide-react";

export default function OpportunitiesPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4">
        <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 mx-auto flex items-center justify-center">
          <Compass className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Opportunity Discovery Feed</h1>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
            The Opportunity Scoring Engine ranks niche signals by trend velocity, originality potential, and business value.
          </p>
        </div>
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 max-w-md mx-auto text-left flex items-start gap-3">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-300">
            Unlocks in <strong>Phase 6</strong> after RSS Discovery (Phase 4) and Trends Engine (Phase 5). Ensure your Single Niche is configured in Settings.
          </p>
        </div>
        <div className="flex items-center justify-center gap-3">
          <Link
            href="/sources"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
          >
            <span>Explore RSS Sources & Candidates</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            href="/settings"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            <span>Configure Niche</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
