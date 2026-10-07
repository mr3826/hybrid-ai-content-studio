"use client";

import { useState } from "react";
import {
  X,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  ArrowRight,
  RefreshCw,
  ShieldCheck,
  FileText,
} from "lucide-react";
import {
  evaluateNicheGuard,
  evaluateBrandQA,
  NicheGuardVerdict,
  BrandQAVerdict,
} from "@/lib/api";

interface EngineTesterModalProps {
  isOpen: boolean;
  onClose: () => void;
  engineId: "niche_guard" | "brand";
  engineName: string;
}

export default function EngineTesterModal({
  isOpen,
  onClose,
  engineId,
  engineName,
}: EngineTesterModalProps) {
  // Niche Guard Form State
  const [ngTitle, setNgTitle] = useState(
    "Stress-Testing Coding Agents on Dirty Legacy Codebases"
  );
  const [ngText, setNgText] = useState(
    "Empirical comparison measuring latency and token costs with local LLMs and IDE integrations. Full code repository and reproducible benchmark data provided."
  );
  const [ngTags, setNgTags] = useState(
    "coding agents, local LLMs, evals and benchmarks"
  );
  const [ngVerdict, setNgVerdict] = useState<NicheGuardVerdict | null>(null);
  const [ngLoading, setNgLoading] = useState(false);

  // Brand QA Form State
  const [brandTitle, setBrandTitle] = useState(
    "Local Qwen 2.5 Coder Benchmark"
  );
  const [brandHook, setBrandHook] = useState(
    "Here is what happens when you run coding benchmarks locally."
  );
  const [brandBody, setBrandBody] = useState(
    "In this benchmark, we measured latency and failure rate across local workflows. The trade-off is clear when comparing reproducible tokens per second against API costs."
  );
  const [brandCta, setBrandCta] = useState(
    "Inspect the reproduction script linked below."
  );
  const [brandVerdict, setBrandVerdict] = useState<BrandQAVerdict | null>(null);
  const [brandLoading, setBrandLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  // Presets
  const loadNichePreset = (type: "in_niche" | "blocked" | "off_niche") => {
    setError(null);
    if (type === "in_niche") {
      setNgTitle("Benchmarking Claude 3.7 vs DeepSeek V3 on Local Code Repos");
      setNgText(
        "Empirical benchmark evaluating latency, tool failure rates, and token costs using local LLMs. Full reproducible code repository provided."
      );
      setNgTags("coding agents, local LLMs, evals and benchmarks");
    } else if (type === "blocked") {
      setNgTitle("Passive Income Schemes with Crypto Trading Bots");
      setNgText(
        "Make fast money with automated crypto/web3 trading algorithms and passive income schemes."
      );
      setNgTags("crypto, trading, passive income");
    } else {
      setNgTitle("Ultimate Sourdough Bread Baking Masterclass");
      setNgText(
        "Learn artisanal dough hydration, folding routines, and dutch oven baking for crusty loaves."
      );
      setNgTags("baking, recipes, sourdough");
    }
  };

  const loadBrandPreset = (type: "on_brand" | "cliche" | "hype") => {
    setError(null);
    if (type === "on_brand") {
      setBrandTitle("Local LLM Coding Benchmark");
      setBrandHook("Here is what happens when you benchmark local coding assistants.");
      setBrandBody(
        "We measured the latency and failure rate across reproducible coding workflows. The trade-off is clear when examining token latency."
      );
      setBrandCta("Inspect the reproduction script linked below.");
    } else if (type === "cliche") {
      setBrandTitle("The Future of AI Coders");
      setBrandHook("Without further ado, let's dive right in!");
      setBrandBody(
        "In today's fast-paced world, software tools move faster than ever. Without further ado, let's dive right in and see the tools."
      );
      setBrandCta("Don't forget to like and subscribe!");
    } else {
      setBrandTitle("Insane New AI Breakthrough");
      setBrandHook("You won't believe what this tool just did!");
      setBrandBody(
        "This tool is an absolute GAME-CHANGER! The unbelievable passive income results are completely insane and mind-blowing!"
      );
      setBrandCta("Click the link right now before it is gone!");
    }
  };

  // Evaluation Actions
  const handleEvaluateNiche = async () => {
    setNgLoading(true);
    setError(null);
    try {
      const tagsArray = ngTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const verdict = await evaluateNicheGuard({
        title: ngTitle,
        text: ngText,
        tags: tagsArray,
      });
      setNgVerdict(verdict);
    } catch (e: any) {
      setError(e.message || "Failed to evaluate candidate against Niche Guard.");
    } finally {
      setNgLoading(false);
    }
  };

  const handleEvaluateBrand = async () => {
    setBrandLoading(true);
    setError(null);
    try {
      const verdict = await evaluateBrandQA({
        title: brandTitle,
        hook: brandHook,
        body: brandBody,
        cta: brandCta,
      });
      setBrandVerdict(verdict);
    } catch (e: any) {
      setError(e.message || "Failed to evaluate draft against Brand QA.");
    } finally {
      setBrandLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-4xl max-h-[92vh] flex flex-col rounded-2xl bg-slate-900 border border-slate-700/80 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <span>Interactive Quality Gate Tester</span>
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {engineId}
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Test arbitrary candidates and copy against the active single {engineId === "niche_guard" ? "NicheProfile" : "BrandProfile"} rules in real time.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-red-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* NICHE GUARD TESTER */}
          {engineId === "niche_guard" && (
            <div className="space-y-5">
              {/* Preset buttons */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800 gap-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Test Presets:
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => loadNichePreset("in_niche")}
                    className="px-2.5 py-1 text-xs rounded-lg bg-emerald-950/40 text-emerald-300 border border-emerald-800/60 hover:bg-emerald-900/60 transition-colors"
                  >
                    In-Niche Sample
                  </button>
                  <button
                    type="button"
                    onClick={() => loadNichePreset("blocked")}
                    className="px-2.5 py-1 text-xs rounded-lg bg-red-950/40 text-red-300 border border-red-800/60 hover:bg-red-900/60 transition-colors"
                  >
                    Blocked Topic Sample
                  </button>
                  <button
                    type="button"
                    onClick={() => loadNichePreset("off_niche")}
                    className="px-2.5 py-1 text-xs rounded-lg bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition-colors"
                  >
                    Off-Niche Sample
                  </button>
                </div>
              </div>

              {/* Form */}
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Candidate Headline / Title
                  </label>
                  <input
                    type="text"
                    value={ngTitle}
                    onChange={(e) => setNgTitle(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                    placeholder="Enter article or video candidate title..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Summary / Candidate Text
                  </label>
                  <textarea
                    rows={3}
                    value={ngText}
                    onChange={(e) => setNgText(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                    placeholder="Enter candidate description or excerpt..."
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Tags (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={ngTags}
                    onChange={(e) => setNgTags(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                    placeholder="coding agents, local LLMs, evals"
                  />
                </div>

                <button
                  type="button"
                  onClick={handleEvaluateNiche}
                  disabled={ngLoading || !ngTitle.trim()}
                  className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs shadow-lg shadow-indigo-600/20 transition-all"
                >
                  {ngLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Evaluating against Niche Taxonomy...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      Evaluate Candidate Against Niche Guard
                    </>
                  )}
                </button>
              </div>

              {/* Verdict Display */}
              {ngVerdict && (
                <div className="mt-4 pt-4 border-t border-slate-800 space-y-4">
                  <div
                    className={`p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
                      ngVerdict.passed
                        ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                        : "bg-red-950/30 border-red-800/60 text-red-300"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {ngVerdict.passed ? (
                        <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                      ) : (
                        <AlertOctagon className="w-6 h-6 text-red-400 shrink-0" />
                      )}
                      <div>
                        <div className="font-bold text-sm">
                          {ngVerdict.passed
                            ? "PASSED — IN-NICHE CANDIDATE"
                            : "REJECTED — OUT-OF-NICHE / BLOCKED"}
                        </div>
                        <div className="text-xs text-slate-300 mt-0.5">
                          {ngVerdict.reason}
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-2xl font-black">
                        {ngVerdict.score.toFixed(1)}
                        <span className="text-xs font-normal text-slate-400">
                          /100
                        </span>
                      </div>
                      <div className="text-[10px] uppercase font-semibold text-slate-400">
                        Niche Relevance
                      </div>
                    </div>
                  </div>

                  {/* Retrofit Metadata Badges: Primary Pillar, Audience Relevance, Flags */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="px-2.5 py-1 rounded-lg bg-indigo-950/80 border border-indigo-800 text-indigo-300 font-medium">
                      Primary Pillar: <strong className="text-white">{ngVerdict.primary_pillar || "None"}</strong>
                    </span>
                    <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 font-medium">
                      Audience Relevance: <strong className="text-emerald-400">{(ngVerdict.audience_relevance ?? 0).toFixed(0)}%</strong>
                    </span>
                    {ngVerdict.is_adjacent && (
                      <span className="px-2.5 py-1 rounded-lg bg-amber-950/80 border border-amber-800 text-amber-300 font-medium">
                        Adjacent Topic
                      </span>
                    )}
                    {ngVerdict.is_blocked && (
                      <span className="px-2.5 py-1 rounded-lg bg-red-950/80 border border-red-800 text-red-300 font-medium">
                        Hard Blocked Topic
                      </span>
                    )}
                  </div>

                  {/* Taxonomy matches */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                      <div className="font-semibold text-slate-300">
                        Content Pillars Matched:
                      </div>
                      {ngVerdict.pillar_matches.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {ngVerdict.pillar_matches.map((p, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-[11px]"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-400 text-[11px]">
                          No pillar matched
                        </span>
                      )}
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                      <div className="font-semibold text-slate-300">
                        Allowed Topics Matched:
                      </div>
                      {ngVerdict.matched_allowed_topics.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {ngVerdict.matched_allowed_topics.map((t, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px]"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-400 text-[11px]">
                          No core allowed topics matched
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Blocked topics warning */}
                  {ngVerdict.blocked_topics_detected.length > 0 && (
                    <div className="p-3 rounded-xl bg-red-950/50 border border-red-800 text-xs text-red-300 space-y-1">
                      <div className="font-bold flex items-center gap-1.5 text-red-200">
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        Strictly Blocked Topics Detected:
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {ngVerdict.blocked_topics_detected.map((bt, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded bg-red-900/60 text-red-200 font-mono text-[11px]"
                          >
                            {bt}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Factor Scoring Table */}
                  {ngVerdict.factors.length > 0 && (
                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
                      <div className="font-semibold text-slate-300">
                        Scoring Breakdown & Factors:
                      </div>
                      <div className="space-y-1.5">
                        {ngVerdict.factors.map((f, i) => (
                          <div
                            key={i}
                            className="flex items-center justify-between py-1 px-2 rounded bg-slate-900/60 border border-slate-800/80"
                          >
                            <div>
                              <span className="font-mono text-slate-300 font-semibold mr-2">
                                {f.criterion}
                              </span>
                              <span className="text-slate-400">{f.detail}</span>
                            </div>
                            <span
                              className={`font-mono font-bold text-xs ${
                                f.points > 0
                                  ? "text-emerald-400"
                                  : f.points < 0
                                  ? "text-red-400"
                                  : "text-slate-400"
                              }`}
                            >
                              {f.points > 0 ? `+${f.points}` : f.points}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* BRAND QA TESTER */}
          {engineId === "brand" && (
            <div className="space-y-5">
              {/* Preset buttons */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800 gap-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Test Presets:
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => loadBrandPreset("on_brand")}
                    className="px-2.5 py-1 text-xs rounded-lg bg-emerald-950/40 text-emerald-300 border border-emerald-800/60 hover:bg-emerald-900/60 transition-colors"
                  >
                    On-Brand Sample
                  </button>
                  <button
                    type="button"
                    onClick={() => loadBrandPreset("cliche")}
                    className="px-2.5 py-1 text-xs rounded-lg bg-amber-950/40 text-amber-300 border border-amber-800/60 hover:bg-amber-900/60 transition-colors"
                  >
                    Banned Clichés Sample
                  </button>
                  <button
                    type="button"
                    onClick={() => loadBrandPreset("hype")}
                    className="px-2.5 py-1 text-xs rounded-lg bg-red-950/40 text-red-300 border border-red-800/60 hover:bg-red-900/60 transition-colors"
                  >
                    Hype & Blacklist Sample
                  </button>
                </div>
              </div>

              {/* Form */}
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Script Title / Headline
                    </label>
                    <input
                      type="text"
                      value={brandTitle}
                      onChange={(e) => setBrandTitle(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Opening Hook (First 5 seconds)
                    </label>
                    <input
                      type="text"
                      value={brandHook}
                      onChange={(e) => setBrandHook(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Script Body / Companion Post Copy
                  </label>
                  <textarea
                    rows={4}
                    value={brandBody}
                    onChange={(e) => setBrandBody(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Call to Action (CTA)
                  </label>
                  <input
                    type="text"
                    value={brandCta}
                    onChange={(e) => setBrandCta(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <button
                  type="button"
                  onClick={handleEvaluateBrand}
                  disabled={brandLoading || !brandBody.trim()}
                  className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs shadow-lg shadow-indigo-600/20 transition-all"
                >
                  {brandLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Auditing against Brand DNA...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      Audit Script Against Brand QA Gate
                    </>
                  )}
                </button>
              </div>

              {/* Verdict Display */}
              {brandVerdict && (
                <div className="mt-4 pt-4 border-t border-slate-800 space-y-4">
                  <div
                    className={`p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
                      brandVerdict.on_brand
                        ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                        : "bg-red-950/30 border-red-800/60 text-red-300"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {brandVerdict.on_brand ? (
                        <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                      ) : (
                        <AlertOctagon className="w-6 h-6 text-red-400 shrink-0" />
                      )}
                      <div>
                        <div className="font-bold text-sm">
                          {brandVerdict.on_brand
                            ? "PASSED — ON-BRAND COMPLIANT"
                            : "FAILED — BRAND VIOLATIONS DETECTED"}
                        </div>
                        <div className="text-xs text-slate-300 mt-0.5">
                          {brandVerdict.violations.length === 0
                            ? "Zero critical brand violations detected. Approved for script production."
                            : `${brandVerdict.violations.length} violation(s) flagged against brand voice and editorial rules.`}
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-2xl font-black">
                        {brandVerdict.overall_score.toFixed(1)}
                        <span className="text-xs font-normal text-slate-400">
                          /100
                        </span>
                      </div>
                      <div className="text-[10px] uppercase font-semibold text-slate-400">
                        Brand Score
                      </div>
                    </div>
                  </div>

                  {/* The 6 Formal Brand QA Dimensions */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-center text-xs">
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[11px] text-slate-400 font-medium">
                        Tone
                      </div>
                      <div className="text-base font-bold text-slate-200 mt-0.5">
                        {brandVerdict.tone_score.toFixed(0)}%
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[11px] text-slate-400 font-medium">
                        Vocabulary
                      </div>
                      <div className="text-base font-bold text-slate-200 mt-0.5">
                        {brandVerdict.vocabulary_score.toFixed(0)}%
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[11px] text-slate-400 font-medium">
                        Repetition
                      </div>
                      <div className="text-base font-bold text-slate-200 mt-0.5">
                        {brandVerdict.repetition_score.toFixed(0)}%
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[11px] text-slate-400 font-medium">
                        Audience Fit
                      </div>
                      <div className="text-base font-bold text-slate-200 mt-0.5">
                        {(brandVerdict.audience_fit_score ?? 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[11px] text-slate-400 font-medium">
                        CTA Fit
                      </div>
                      <div className="text-base font-bold text-slate-200 mt-0.5">
                        {(brandVerdict.cta_fit_score ?? 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="text-[11px] text-slate-400 font-medium">
                        Platform Fit
                      </div>
                      <div className="text-base font-bold text-slate-200 mt-0.5">
                        {(brandVerdict.platform_fit_score ?? 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  {/* Brand Memory Repetition Warnings */}
                  {brandVerdict.repetition_warnings && brandVerdict.repetition_warnings.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/80 text-amber-200 text-xs space-y-1.5">
                      <div className="font-semibold flex items-center gap-1.5 text-amber-300">
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                        Brand Memory Repetition Warnings ({brandVerdict.repetition_warnings.length}):
                      </div>
                      <ul className="list-disc list-inside space-y-1 text-slate-300 pl-1">
                        {brandVerdict.repetition_warnings.map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Violations List */}
                  {brandVerdict.violations.length > 0 && (
                    <div className="space-y-2 text-xs">
                      <div className="font-semibold text-slate-300">
                        Flagged Violations:
                      </div>
                      {brandVerdict.violations.map((v, i) => (
                        <div
                          key={i}
                          className={`p-3 rounded-xl border flex items-start gap-2.5 ${
                            v.severity === "critical"
                              ? "bg-red-950/30 border-red-800/60 text-red-200"
                              : "bg-amber-950/30 border-amber-800/60 text-amber-200"
                          }`}
                        >
                          {v.severity === "critical" ? (
                            <AlertOctagon className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          )}
                          <div className="flex-1 space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="font-mono uppercase font-bold text-[10px] px-1.5 py-0.5 rounded bg-black/40">
                                {v.rule_type}
                              </span>
                              <span className="font-semibold text-slate-200">
                                &ldquo;{v.matched_phrase}&rdquo;
                              </span>
                            </div>
                            <div className="text-slate-300">{v.message}</div>
                            {v.suggestion && (
                              <div className="text-slate-400 text-[11px] flex items-center gap-1.5 pt-0.5">
                                <ArrowRight className="w-3 h-3 text-indigo-400" />
                                <span>{v.suggestion}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Preferred Words */}
                  {brandVerdict.matched_preferred_words.length > 0 && (
                    <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 text-xs">
                      <div className="font-semibold text-slate-300">
                        Approved Preferred Terminology Matched:
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {brandVerdict.matched_preferred_words.map((w, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[11px]"
                          >
                            {w}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
