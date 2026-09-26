"use client";

import { useEffect, useState } from "react";
import { 
  Cpu, 
  Play, 
  FileText, 
  History, 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Sliders, 
  X, 
  Sparkles,
  ArrowRight
} from "lucide-react";
import { 
  getEngines, 
  getEngineRules, 
  updateEngineRules, 
  getEngineRuns, 
  runEngine, 
  dryRunEngine, 
  EngineSummary, 
  EngineRunRecord,
  EngineResult
} from "@/lib/api";

export default function EnginesPage() {
  const [engines, setEngines] = useState<EngineSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Modal states
  const [selectedEngine, setSelectedEngine] = useState<EngineSummary | null>(null);
  const [rulesModalOpen, setRulesModalOpen] = useState(false);
  const [rulesJson, setRulesJson] = useState("");
  const [savingRules, setSavingRules] = useState(false);

  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [runs, setRuns] = useState<EngineRunRecord[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);

  const loadEngines = async () => {
    setLoading(true);
    try {
      const data = await getEngines();
      setEngines(data);
    } catch (e: any) {
      console.error("Failed to load engines:", e);
      showToast("error", "Failed to connect to Engine Registry");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEngines();
  }, []);

  const showToast = (type: "success" | "error", text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4000);
  };

  // Run Handlers
  const handleRun = async (engineId: string, isDryRun: boolean = false) => {
    setActionLoading(`${engineId}-${isDryRun ? "dry" : "run"}`);
    try {
      const result: EngineResult = isDryRun
        ? await dryRunEngine(engineId)
        : await runEngine(engineId);

      showToast(
        result.success ? "success" : "error",
        `${isDryRun ? "[Dry Run]" : "[Run]"} ${engineId}: ${result.summary}`
      );
      await loadEngines();
    } catch (e: any) {
      showToast("error", e.message || `Failed to run engine ${engineId}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Open Rules Modal
  const handleOpenRules = async (eng: EngineSummary) => {
    setSelectedEngine(eng);
    try {
      const currentRules = await getEngineRules(eng.id);
      setRulesJson(JSON.stringify(currentRules, null, 2));
      setRulesModalOpen(true);
    } catch (e: any) {
      showToast("error", "Could not fetch rules");
    }
  };

  // Save Rules
  const handleSaveRules = async () => {
    if (!selectedEngine) return;
    setSavingRules(true);
    try {
      const parsed = JSON.parse(rulesJson);
      await updateEngineRules(selectedEngine.id, parsed);
      showToast("success", `Rules updated for ${selectedEngine.name}`);
      setRulesModalOpen(false);
      await loadEngines();
    } catch (e: any) {
      showToast("error", "Invalid JSON format or update rejected");
    } finally {
      setSavingRules(false);
    }
  };

  // Open Logs Modal
  const handleOpenLogs = async (eng: EngineSummary) => {
    setSelectedEngine(eng);
    setLogsModalOpen(true);
    setLoadingRuns(true);
    try {
      const history = await getEngineRuns(eng.id);
      setRuns(history);
    } catch (e: any) {
      showToast("error", "Could not fetch run logs");
    } finally {
      setLoadingRuns(false);
    }
  };

  const healthyCount = engines.filter((e) => e.health.status === "healthy").length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between border ${
            toast.type === "success"
              ? "bg-emerald-950/80 border-emerald-800 text-emerald-300"
              : "bg-red-950/80 border-red-800 text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {toast.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400" />
            )}
            <span className="text-sm font-medium">{toast.text}</span>
          </div>
          <button onClick={() => setToast(null)} className="text-xs text-slate-400 hover:text-white">
            &times;
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Cpu className="w-6 h-6 text-indigo-400" />
            Feature Engine Registry
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Independent, decoupled feature engines with strict contracts, isolated rules, dry runs, and explainability.
          </p>
        </div>
        <button
          onClick={loadEngines}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Registry
        </button>
      </div>

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Engines</div>
          <div className="text-2xl font-bold text-white mt-1">{engines.length}</div>
          <div className="text-xs text-slate-400 mt-0.5">13 Feature + 1 Reference</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Health Status</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {healthyCount} / {engines.length}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">Operational engines</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Engine Isolation</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1">100%</div>
          <div className="text-xs text-slate-400 mt-0.5">Stable contracts & manifests</div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Auditability</div>
          <div className="text-2xl font-bold text-sky-400 mt-1">WAL Mode</div>
          <div className="text-xs text-slate-400 mt-0.5">SQLite run logs active</div>
        </div>
      </div>

      {/* Engine Cards Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-48 text-slate-400">
          <RefreshCw className="w-5 h-5 animate-spin mr-2" />
          Loading engines from registry...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {engines.map((eng) => (
            <div
              key={eng.id}
              className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 transition-all flex flex-col justify-between space-y-4"
            >
              <div>
                {/* Header row */}
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400 px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                        {eng.id}
                      </span>
                      <h3 className="text-sm font-semibold text-white">{eng.name}</h3>
                      <span className="text-[11px] text-slate-400">v{eng.version}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                      {eng.description}
                    </p>
                  </div>
                  <span
                    className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full shrink-0 border ${
                      eng.health.status === "healthy"
                        ? "bg-emerald-950/60 text-emerald-400 border-emerald-800/60"
                        : "bg-red-950/60 text-red-400 border-red-800/60"
                    }`}
                  >
                    {eng.health.status.toUpperCase()}
                  </span>
                </div>

                {/* Contracts & Dependencies */}
                <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-2 text-xs">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-400 text-[11px]">Inputs:</span>
                    {eng.inputs.length === 0 ? (
                      <span className="text-slate-400 text-[11px] italic">None</span>
                    ) : (
                      eng.inputs.map((inp) => (
                        <span key={inp} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px]">
                          {inp}
                        </span>
                      ))
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-400 text-[11px]">Outputs:</span>
                    {eng.outputs.length === 0 ? (
                      <span className="text-slate-400 text-[11px] italic">None</span>
                    ) : (
                      eng.outputs.map((out) => (
                        <span key={out} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px]">
                          {out}
                        </span>
                      ))
                    )}
                  </div>

                  {eng.dependencies.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-amber-400/90 text-[11px]">Depends on:</span>
                      {eng.dependencies.map((dep) => (
                        <span key={dep} className="px-1.5 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-900/60 text-[11px]">
                          {dep}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <div className="text-[11px] text-slate-400">
                  Runs: <span className="text-slate-200 font-semibold">{eng.total_runs_count}</span>
                  {eng.last_run_status && (
                    <span className="ml-2">
                      Last: <span className="text-slate-300 font-mono">{eng.last_run_status}</span>
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleOpenRules(eng)}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                  >
                    <Sliders className="w-3 h-3" />
                    <span>Rules</span>
                  </button>

                  <button
                    onClick={() => handleOpenLogs(eng)}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                  >
                    <History className="w-3 h-3" />
                    <span>Logs</span>
                  </button>

                  <button
                    onClick={() => handleRun(eng.id, true)}
                    disabled={actionLoading !== null}
                    className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-400 border border-slate-700 transition-colors"
                  >
                    {actionLoading === `${eng.id}-dry` ? "Running..." : "Dry Run"}
                  </button>

                  <button
                    onClick={() => handleRun(eng.id, false)}
                    disabled={actionLoading !== null}
                    className="flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20 transition-colors"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    <span>{actionLoading === `${eng.id}-run` ? "Running..." : "Run"}</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Rules Modal */}
      {rulesModalOpen && selectedEngine && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-indigo-400" />
                  Engine Rules & Config: {selectedEngine.name}
                </h3>
                <p className="text-xs text-slate-400">Rules live with the engine and maintain versioned history.</p>
              </div>
              <button onClick={() => setRulesModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                JSON Configuration
              </label>
              <textarea
                rows={12}
                value={rulesJson}
                onChange={(e) => setRulesJson(e.target.value)}
                className="w-full p-3 font-mono text-xs rounded-xl bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-slate-400">Validated against Engine manifest</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setRulesModalOpen(false)}
                  className="px-4 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveRules}
                  disabled={savingRules}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  {savingRules ? "Saving..." : "Save Rules"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Logs Modal */}
      {logsModalOpen && selectedEngine && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 space-y-4 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 shrink-0">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <History className="w-4 h-4 text-indigo-400" />
                  Execution Logs: {selectedEngine.name}
                </h3>
                <p className="text-xs text-slate-400">Audit trail of engine runs stored in SQLite WAL.</p>
              </div>
              <button onClick={() => setLogsModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {loadingRuns ? (
                <div className="text-center py-12 text-slate-400 text-sm">Loading execution logs...</div>
              ) : runs.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-sm border border-dashed border-slate-800 rounded-xl">
                  No execution records found for this engine yet. Run or Dry Run to generate logs.
                </div>
              ) : (
                runs.map((r) => (
                  <div key={r.id} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-mono px-2 py-0.5 rounded text-[10px] font-bold ${
                            r.status === "completed"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : r.status === "dry_run"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-red-500/10 text-red-400 border border-red-500/20"
                          }`}
                        >
                          {r.status.toUpperCase()}
                        </span>
                        <span className="font-mono text-slate-300">Run #{r.run_id}</span>
                        <span className="text-slate-400">&bull; {r.duration_ms}ms</span>
                      </div>
                      <span className="text-slate-400">{new Date(r.started_at).toLocaleTimeString()}</span>
                    </div>

                    <p className="text-slate-200">{r.summary}</p>

                    <div className="flex items-center gap-4 text-slate-400 text-[11px] pt-1 border-t border-slate-800/60">
                      <span>Inputs: <strong className="text-slate-300">{r.input_count}</strong></span>
                      <span>Outputs: <strong className="text-slate-300">{r.output_count}</strong></span>
                      <span>Rejected: <strong className="text-slate-300">{r.rejected_count}</strong></span>
                      <span>Errors: <strong className="text-slate-300">{r.error_count}</strong></span>
                      <span>Cost: <strong className="text-slate-300">${r.cost.toFixed(4)}</strong></span>
                    </div>

                    {r.explanations.length > 0 && (
                      <div className="mt-1 pt-1 border-t border-slate-800/40">
                        <span className="text-[10px] font-semibold uppercase text-slate-400">Explainability Factors:</span>
                        <div className="mt-0.5 space-y-0.5">
                          {r.explanations.map((exp, i) => (
                            <div key={i} className="text-[11px] text-slate-300 font-mono">
                              &bull; {JSON.stringify(exp)}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
