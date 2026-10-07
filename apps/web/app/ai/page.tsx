"use client";

import { useEffect, useState } from "react";
import {
  Bot,
  Sparkles,
  Zap,
  Activity,
  DollarSign,
  Clock,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  Play,
  Terminal,
  FileCode,
  Layers,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Cpu,
} from "lucide-react";
import {
  getAIStatus,
  getAIAnalytics,
  getAILogs,
  generateAIText,
  generateAIStructured,
  analyzeAIContent,
  AIProviderStatus,
  AIAnalyticsSummary,
  AIInvocationLog,
  AIResponse,
} from "@/lib/api";

type ActiveTab = "playground" | "telemetry" | "architecture";

export default function AIStudioPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("playground");
  const [status, setStatus] = useState<AIProviderStatus | null>(null);
  const [analytics, setAnalytics] = useState<AIAnalyticsSummary | null>(null);
  const [logs, setLogs] = useState<AIInvocationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Playground state
  const [playgroundMode, setPlaygroundMode] = useState<"text" | "structured" | "analyze">("text");
  const [prompt, setPrompt] = useState(
    "Explain how local model inference benchmarks on unified memory eliminate hallucination in tech video scripts."
  );
  const [taskName, setTaskName] = useState("script_concept");
  const [providerPref, setProviderPref] = useState<string>("auto");
  const [simulateFailure, setSimulateFailure] = useState<string>("none");
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<AIResponse | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);

  // Telemetry filter
  const [logFilterProvider, setLogFilterProvider] = useState<string>("all");
  const [logFilterFallback, setLogFilterFallback] = useState<string>("all");

  const loadData = async () => {
    try {
      const [st, an, lg] = await Promise.all([
        getAIStatus(),
        getAIAnalytics(30),
        getAILogs({ limit: 50 }),
      ]);
      setStatus(st);
      setAnalytics(an);
      setLogs(lg);
    } catch (err: any) {
      console.error("Failed to load AI Provider data:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleExecutePlayground = async () => {
    setExecuting(true);
    setExecutionError(null);
    setExecutionResult(null);

    const preferred = providerPref === "auto" ? undefined : providerPref;
    const simFail = simulateFailure === "none" ? undefined : simulateFailure;

    try {
      let res: AIResponse;
      if (playgroundMode === "text") {
        res = await generateAIText({
          prompt,
          task: taskName,
          preferred_provider: preferred,
          simulate_failure: simFail,
        });
      } else if (playgroundMode === "structured") {
        res = await generateAIStructured({
          prompt,
          response_schema: {
            type: "object",
            properties: {
              hook_angle: { type: "string" },
              hardware_requirements: { type: "string" },
              empirical_metric: { type: "string" },
              confidence_score: { type: "number" },
            },
            required: ["hook_angle", "hardware_requirements", "empirical_metric", "confidence_score"],
          },
          task: taskName,
          preferred_provider: preferred,
          simulate_failure: simFail,
        });
      } else {
        res = await analyzeAIContent({
          content: prompt,
          instruction: "Audit factual clarity and ensure all claims reference reproducible benchmarks.",
          criteria: ["empirical_verifiability", "clarity", "no_hype"],
          task: taskName,
          preferred_provider: preferred,
          simulate_failure: simFail,
        });
      }

      setExecutionResult(res);
      // Refresh telemetry in background
      loadData();
    } catch (err: any) {
      setExecutionError(err?.message || "Failed to execute AI request");
    } finally {
      setExecuting(false);
    }
  };

  const filteredLogs = logs.filter((l) => {
    if (logFilterProvider !== "all" && l.provider !== logFilterProvider) return false;
    if (logFilterFallback === "fallback_only" && !l.fallback_used) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-8 w-8 animate-spin text-indigo-400" />
          <p className="text-sm text-slate-400">Loading AI Provider telemetry & status...</p>
        </div>
      </div>
    );
  }

  const dailySpend = status?.daily_spend_today ?? 0;
  const budgetLimit = status?.daily_budget_limit ?? 5.0;
  const budgetPercent = Math.min(100, Math.round((dailySpend / budgetLimit) * 100));

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">AI Provider Engine</h1>
              <p className="text-xs text-slate-400">
                Centralized LLM router with Gemini primary, Qwen fallback, and token cost telemetry
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh Telemetry
          </button>
        </div>
      </div>

      {/* Provider Health & Budget Banner */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Primary Adapter Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Primary Adapter</span>
            <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <h3 className="text-base font-bold text-white capitalize">{status?.primary_provider || "Gemini"}</h3>
            <span className="text-xs font-mono text-indigo-400">{status?.primary_model}</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            {status?.mock_mode ? "⚡ Mock Mode Active (Zero API cost)" : "Connected to Google Generative API"}
          </p>
        </div>

        {/* Fallback Adapter Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Failover Adapter</span>
            <span className="flex h-2 w-2 rounded-full bg-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <h3 className="text-base font-bold text-white capitalize">{status?.fallback_provider || "Qwen"}</h3>
            <span className="text-xs font-mono text-amber-400">{status?.fallback_model}</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            Triggers strictly on technical 429/500/503 or schema failures
          </p>
        </div>

        {/* Daily Budget Gauge Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Daily AI Budget</span>
            <DollarSign className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-lg font-bold text-white">${dailySpend.toFixed(4)}</span>
            <span className="text-xs text-slate-400">Limit: ${budgetLimit.toFixed(2)}</span>
          </div>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full transition-all ${
                budgetPercent > 80 ? "bg-rose-500" : budgetPercent > 50 ? "bg-amber-400" : "bg-emerald-500"
              }`}
              style={{ width: `${budgetPercent}%` }}
            />
          </div>
        </div>

        {/* Telemetry Stats Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">30-Day Activity</span>
            <Activity className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-lg font-bold text-white">{analytics?.total_calls ?? 0} calls</span>
            <span className="text-xs font-medium text-emerald-400">{analytics?.success_rate ?? 100}% success</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">
            {analytics?.fallback_count ?? 0} failovers ({analytics?.fallback_rate ?? 0}% rate)
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800">
        <button
          onClick={() => setActiveTab("playground")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === "playground"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Play className="h-3.5 w-3.5" />
          Interactive Studio Playground
        </button>
        <button
          onClick={() => setActiveTab("telemetry")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === "telemetry"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Terminal className="h-3.5 w-3.5" />
          Invocation Telemetry Logs ({logs.length})
        </button>
        <button
          onClick={() => setActiveTab("architecture")}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-colors ${
            activeTab === "architecture"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="h-3.5 w-3.5" />
          Invariants & Routing Architecture
        </button>
      </div>

      {/* Tab Content: Playground */}
      {activeTab === "playground" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Controls Form */}
          <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Execution Parameters</h2>
              <div className="flex rounded-lg bg-slate-800 p-0.5">
                {(["text", "structured", "analyze"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setPlaygroundMode(m)}
                    className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize transition-colors ${
                      playgroundMode === m ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Task Identifier</label>
              <input
                type="text"
                value={taskName}
                onChange={(e) => setTaskName(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                {playgroundMode === "analyze" ? "Content to Analyze" : "Prompt / Instructions"}
              </label>
              <textarea
                rows={5}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/80 p-3 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Preferred Provider</label>
                <select
                  value={providerPref}
                  onChange={(e) => setProviderPref(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value="auto">Auto (Gemini Primary)</option>
                  <option value="gemini">Gemini</option>
                  <option value="qwen">Qwen</option>
                  <option value="mock">Mock Offline</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Failover Simulation Test</label>
                <select
                  value={simulateFailure}
                  onChange={(e) => setSimulateFailure(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value="none">None (Normal Execution)</option>
                  <option value="server_error">Simulate 503 Server Error (Failover to Qwen)</option>
                  <option value="rate_limit">Simulate 429 Rate Limit (Failover to Qwen)</option>
                  <option value="schema_error">Simulate Malformed JSON (Schema Failover)</option>
                </select>
              </div>
            </div>

            {simulateFailure !== "none" && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>
                  Simulation active: Primary provider will artificially fail, triggering the automated technical fallback to Qwen.
                </span>
              </div>
            )}

            <button
              onClick={handleExecutePlayground}
              disabled={executing || !prompt.trim()}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-colors disabled:opacity-50"
            >
              {executing ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Routing to LLM Adapter...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Execute via AI Engine
                </>
              )}
            </button>
          </div>

          {/* Results Panel */}
          <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h2 className="text-sm font-semibold text-white">Live Execution Result</h2>
                {executionResult && (
                  <div className="flex items-center gap-2">
                    {executionResult.fallback_used ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-300 border border-amber-500/30">
                        <Zap className="h-3 w-3" />
                        Failover: {executionResult.provider}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-300 border border-emerald-500/30">
                        <CheckCircle2 className="h-3 w-3" />
                        Primary: {executionResult.provider}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {executionError && (
                <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300 flex items-start gap-2">
                  <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{executionError}</span>
                </div>
              )}

              {executionResult ? (
                <div className="mt-4 space-y-4">
                  {executionResult.fallback_used && (
                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                      <span className="font-semibold">Technical Failover Activated: </span>
                      {executionResult.fallback_reason || "Primary adapter failed technical validation."}
                    </div>
                  )}

                  {/* Telemetry Chips */}
                  <div className="grid grid-cols-4 gap-2 text-center text-xs">
                    <div className="rounded-lg bg-slate-800/80 p-2">
                      <p className="text-[10px] text-slate-400">Model</p>
                      <p className="font-mono text-white text-[11px] truncate">{executionResult.model}</p>
                    </div>
                    <div className="rounded-lg bg-slate-800/80 p-2">
                      <p className="text-[10px] text-slate-400">Tokens</p>
                      <p className="font-mono text-indigo-400">{executionResult.total_tokens}</p>
                    </div>
                    <div className="rounded-lg bg-slate-800/80 p-2">
                      <p className="text-[10px] text-slate-400">Latency</p>
                      <p className="font-mono text-emerald-400">{executionResult.latency_ms.toFixed(1)}ms</p>
                    </div>
                    <div className="rounded-lg bg-slate-800/80 p-2">
                      <p className="text-[10px] text-slate-400">Cost</p>
                      <p className="font-mono text-amber-400">${executionResult.cost.toFixed(5)}</p>
                    </div>
                  </div>

                  {/* Body Content */}
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Generated Output</label>
                    <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-700 bg-slate-950/70 p-3 font-mono text-xs text-slate-200 whitespace-pre-wrap">
                      {executionResult.structured_data
                        ? JSON.stringify(executionResult.structured_data, null, 2)
                        : executionResult.text}
                    </div>
                  </div>
                </div>
              ) : !executionError ? (
                <div className="flex flex-col items-center justify-center py-16 text-center text-slate-500">
                  <Terminal className="h-10 w-10 text-slate-600 mb-2" />
                  <p className="text-xs">Select parameters and click "Execute via AI Engine" to test routing.</p>
                </div>
              ) : null}
            </div>

            <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
              <span>Zero-Secrets Invariant: API keys and raw authorization headers are never logged or stored.</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab Content: Telemetry Logs */}
      {activeTab === "telemetry" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">Filter Provider</label>
              <select
                value={logFilterProvider}
                onChange={(e) => setLogFilterProvider(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-white focus:outline-none"
              >
                <option value="all">All Providers</option>
                <option value="gemini">Gemini</option>
                <option value="qwen">Qwen</option>
                <option value="mock">Mock</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">Failover Filter</label>
              <select
                value={logFilterFallback}
                onChange={(e) => setLogFilterFallback(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-white focus:outline-none"
              >
                <option value="all">All Logs</option>
                <option value="fallback_only">Failovers Only</option>
              </select>
            </div>
          </div>

          {/* Logs Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
            <table className="w-full min-w-[700px] text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-800/40 text-slate-400">
                <tr>
                  <th className="px-4 py-3 font-semibold">Timestamp</th>
                  <th className="px-4 py-3 font-semibold">Task</th>
                  <th className="px-4 py-3 font-semibold">Provider / Model</th>
                  <th className="px-4 py-3 font-semibold">Tokens</th>
                  <th className="px-4 py-3 font-semibold">Cost</th>
                  <th className="px-4 py-3 font-semibold">Latency</th>
                  <th className="px-4 py-3 font-semibold">Routing</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-3 font-medium text-white">{log.task}</td>
                    <td className="px-4 py-3">
                      <span className="capitalize font-semibold text-slate-200">{log.provider}</span>{" "}
                      <span className="text-[10px] text-slate-400">({log.model})</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-300">{log.total_tokens}</td>
                    <td className="px-4 py-3 font-mono text-amber-300">${log.cost.toFixed(5)}</td>
                    <td className="px-4 py-3 font-mono text-slate-400">{log.latency_ms.toFixed(1)}ms</td>
                    <td className="px-4 py-3">
                      {log.fallback_used ? (
                        <span className="inline-flex items-center gap-1 rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-300 border border-amber-500/30">
                          ⚡ Failover
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                          Direct
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {log.success ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Success
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-medium" title={log.error_message || ""}>
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {filteredLogs.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500">
                      No invocation telemetry records matching filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab Content: Architecture */}
      {activeTab === "architecture" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
            <div className="flex items-center gap-2 text-indigo-400">
              <Zap className="h-5 w-5" />
              <h3 className="font-semibold text-sm text-white">Centralized LLM Router</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              All downstream studio engines (Research, Content, Scene, Analytics) access generative intelligence exclusively via the centralized AI Provider Engine contracts (`generate_text`, `generate_structured`, `analyze`). Direct, unmonitored SDK calls are forbidden.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
            <div className="flex items-center gap-2 text-amber-400">
              <ShieldAlert className="h-5 w-5" />
              <h3 className="font-semibold text-sm text-white">Technical-Only Failover</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Fallback from Gemini to Qwen triggers strictly on infrastructure errors (HTTP 429 rate limits, 500/503 service outages, or malformed schema parsing). Failover is strictly prohibited to manufacture factual support or override editorial rejections.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
            <div className="flex items-center gap-2 text-emerald-400">
              <ShieldCheck className="h-5 w-5" />
              <h3 className="font-semibold text-sm text-white">Zero Secrets & Cost Caps</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              API tokens are loaded from local environment configurations and never committed or persisted in SQLite telemetry tables. A hard daily budget ceiling ($5.00/day) prevents runaway costs during automated signal harvesting.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
