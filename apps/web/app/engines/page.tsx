import Link from "next/link";
import { Cpu, CheckCircle2, ArrowRight } from "lucide-react";

export default function EnginesPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-4">
        <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 mx-auto flex items-center justify-center">
          <Cpu className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">13 Independent Feature Engines</h1>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
            Independent manifests, stable contracts, dry runs, rules, logs, and explainability for all 13 studio engines.
          </p>
        </div>
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 max-w-md mx-auto text-left flex items-start gap-3">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-300">
            Full Engine Registry UI, lifecycle runners, logs, and dry-run execution will be implemented in <strong>Phase 2 (Engine Framework)</strong>.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
        >
          <span>Back to Dashboard</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
