import Link from "next/link";
import { Film, Sparkles, ArrowRight } from "lucide-react";

export default function ProjectsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4">
        <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 mx-auto flex items-center justify-center">
          <Film className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Content Projects & Script Studio</h1>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
            Storyboarding, script block editing, scene asset attachments, and Brand QA checks.
          </p>
        </div>
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 max-w-md mx-auto text-left flex items-start gap-3">
          <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-300">
            Unlocks in <strong>Phase 10 (Script Studio)</strong> & <strong>Phase 11 (Scene Studio)</strong>. All scripts inherit the active Brand DNA configured in Settings.
          </p>
        </div>
        <Link
          href="/settings"
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          <span>Configure Brand in Settings</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
