"use client";

import { useEffect, useState } from "react";
import { 
  ShieldCheck, 
  Layers, 
  Sparkles, 
  ExternalLink, 
  Download, 
  Upload, 
  Save, 
  Plus, 
  Trash2, 
  CheckCircle, 
  AlertCircle,
  RefreshCw,
  Brain
} from "lucide-react";
import {
  getNiche,
  updateNiche,
  seedNiche,
  getBrand,
  updateBrand,
  seedBrand,
  getBrandExemplars,
  createBrandExemplar,
  deleteBrandExemplar,
  getBrandMemory,
  recordBrandMemory,
  deleteBrandMemory,
  getPlatforms,
  updatePlatform,
  seedPlatforms,
  exportSettings,
  importSettings,
  seedAllSettings,
  NicheProfile,
  BrandProfile,
  BrandExemplar,
  BrandMemoryItem,
  PlatformSetting
} from "@/lib/api";

type Tab = "niche" | "brand" | "memory" | "exemplars" | "platforms" | "transfer";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("niche");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Niche State
  const [niche, setNiche] = useState<NicheProfile>({
    name: "",
    one_sentence_definition: "",
    audience: "",
    audience_regions: [],
    primary_problems: [],
    allowed_topics: [],
    adjacent_topics: [],
    blocked_topics: [],
    must_have_signals: [],
    negative_keywords: [],
    preferred_source_types: [],
    content_pillars: [],
    commercial_intent_topics: [],
    evergreen_topics: [],
  });

  // Brand State
  const [brand, setBrand] = useState<BrandProfile>({
    brand_name: "",
    brand_promise: "",
    audience: "",
    tone: [],
    voice_rules: [],
    preferred_vocabulary: [],
    avoid_vocabulary: [],
    banned_cliches: [],
    claim_rules: [],
    cta_style: "",
    humor_policy: "",
    controversy_policy: "",
    sponsor_policy: "",
    affiliate_disclosure_style: "",
    default_lead_magnet: "",
    newsletter_cta: "",
    digital_product_cta: "",
    visual_identity: {},
    platform_adaptations: {},
  });

  // Brand Memory State
  const [memoryItems, setMemoryItems] = useState<BrandMemoryItem[]>([]);
  const [memoryFilter, setMemoryFilter] = useState<string>("all");
  const [newMemory, setNewMemory] = useState({
    memory_type: "hook",
    content: "",
  });

  // Exemplars State
  const [exemplars, setExemplars] = useState<BrandExemplar[]>([]);
  const [newExemplar, setNewExemplar] = useState({
    category: "approved_hook",
    title: "",
    content: "",
    platform: "all",
    context_note: "",
  });

  // Platforms State
  const [platforms, setPlatforms] = useState<Record<string, PlatformSetting>>({});

  // Transfer State
  const [importJson, setImportJson] = useState("");

  const loadAll = async () => {
    setLoading(true);
    try {
      const [nData, bData, exData, pData, mData] = await Promise.all([
        getNiche(),
        getBrand(),
        getBrandExemplars(),
        getPlatforms(),
        getBrandMemory(),
      ]);

      if (nData) setNiche(nData);
      if (bData) setBrand(bData);
      if (exData) setExemplars(exData);
      if (pData) setPlatforms(pData);
      if (mData) setMemoryItems(mData);
    } catch (e) {
      console.error("Error loading settings:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const showToast = (type: "success" | "error", text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  // Niche Handlers
  const handleSaveNiche = async () => {
    setSaving(true);
    try {
      const updated = await updateNiche(niche);
      setNiche(updated);
      showToast("success", "Single Niche Profile saved successfully!");
    } catch (e: any) {
      showToast("error", e.message || "Failed to save Niche Profile");
    } finally {
      setSaving(false);
    }
  };

  const handleSeedNiche = async () => {
    setSaving(true);
    try {
      const seeded = await seedNiche();
      setNiche(seeded);
      showToast("success", "Default Niche Profile seeded from template!");
    } catch (e: any) {
      showToast("error", e.message || "Failed to seed Niche");
    } finally {
      setSaving(false);
    }
  };

  // Brand Handlers
  const handleSaveBrand = async () => {
    setSaving(true);
    try {
      const updated = await updateBrand(brand);
      setBrand(updated);
      showToast("success", "Single Brand DNA saved successfully!");
    } catch (e: any) {
      showToast("error", e.message || "Failed to save Brand Profile");
    } finally {
      setSaving(false);
    }
  };

  const handleSeedBrand = async () => {
    setSaving(true);
    try {
      const seeded = await seedBrand();
      setBrand(seeded);
      showToast("success", "Default Brand DNA seeded from template!");
    } catch (e: any) {
      showToast("error", e.message || "Failed to seed Brand");
    } finally {
      setSaving(false);
    }
  };

  // Exemplar Handlers
  const handleAddExemplar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newExemplar.title || !newExemplar.content) return;
    setSaving(true);
    try {
      const created = await createBrandExemplar(newExemplar);
      setExemplars([created, ...exemplars]);
      setNewExemplar({
        category: "approved_hook",
        title: "",
        content: "",
        platform: "all",
        context_note: "",
      });
      showToast("success", "Brand Exemplar added successfully!");
    } catch (e: any) {
      showToast("error", e.message || "Failed to add Exemplar");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteExemplar = async (id: string) => {
    try {
      await deleteBrandExemplar(id);
      setExemplars(exemplars.filter((x) => x.id !== id));
      showToast("success", "Brand Exemplar deleted.");
    } catch (e: any) {
      showToast("error", e.message || "Failed to delete Exemplar");
    }
  };

  // Brand Memory Handlers
  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemory.content.trim()) return;
    setSaving(true);
    try {
      const created = await recordBrandMemory({
        memory_type: newMemory.memory_type,
        content: newMemory.content.trim(),
      });
      setMemoryItems([created, ...memoryItems.filter((m) => m.id !== created.id)]);
      setNewMemory({
        memory_type: "hook",
        content: "",
      });
      showToast("success", "Brand memory recorded successfully!");
    } catch (e: any) {
      showToast("error", e.message || "Failed to record Brand Memory");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteMemory = async (id: string) => {
    try {
      await deleteBrandMemory(id);
      setMemoryItems(memoryItems.filter((m) => m.id !== id));
      showToast("success", "Brand memory item removed.");
    } catch (e: any) {
      showToast("error", e.message || "Failed to remove Brand Memory item");
    }
  };

  // Platform Handlers
  const handleSavePlatform = async (platName: string) => {
    const plat = platforms[platName];
    if (!plat) return;

    if (plat.channel_url && !plat.channel_url.startsWith("https://")) {
      showToast("error", `Channel URL for ${platName} must start with https://`);
      return;
    }
    if (plat.publishing_url && !plat.publishing_url.startsWith("https://")) {
      showToast("error", `Publishing URL for ${platName} must start with https://`);
      return;
    }

    setSaving(true);
    try {
      const updated = await updatePlatform(platName, plat);
      setPlatforms({ ...platforms, [platName]: updated });
      showToast("success", `${platName.toUpperCase()} launcher settings saved.`);
    } catch (e: any) {
      showToast("error", e.message || `Failed to update ${platName}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSeedPlatforms = async () => {
    setSaving(true);
    try {
      const seeded = await seedPlatforms();
      setPlatforms(seeded);
      showToast("success", "Platform Launchers seeded from template!");
    } catch (e: any) {
      showToast("error", e.message || "Failed to seed platforms");
    } finally {
      setSaving(false);
    }
  };

  // Transfer Handlers
  const handleExport = async () => {
    try {
      const data = await exportSettings();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `content-studio-config-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("success", "Configuration exported successfully!");
    } catch (e: any) {
      showToast("error", e.message || "Export failed");
    }
  };

  const handleImport = async () => {
    if (!importJson.trim()) return;
    setSaving(true);
    try {
      const parsed = JSON.parse(importJson);
      await importSettings(parsed);
      await loadAll();
      setImportJson("");
      showToast("success", "Configuration imported and applied!");
    } catch (e: any) {
      showToast("error", e.message || "Invalid JSON or Import Failed");
    } finally {
      setSaving(false);
    }
  };

  const handleSeedAll = async () => {
    if (!confirm("Seed all default configs (Niche, Brand, Platforms)?")) return;
    setSaving(true);
    try {
      await seedAllSettings();
      await loadAll();
      showToast("success", "All studio defaults seeded successfully!");
    } catch (e: any) {
      showToast("error", e.message || "Seed all failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <RefreshCw className="w-5 h-5 animate-spin mr-2" />
        Loading studio settings...
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Toast */}
      {message && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between border ${
            message.type === "success"
              ? "bg-emerald-950/80 border-emerald-800 text-emerald-300"
              : "bg-red-950/80 border-red-800 text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {message.type === "success" ? (
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400" />
            )}
            <span className="text-sm font-medium">{message.text}</span>
          </div>
          <button onClick={() => setMessage(null)} className="text-xs text-slate-400 hover:text-white">
            &times;
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Studio Settings</h1>
          <p className="text-sm text-slate-400">
            Configure the single niche, single brand identity, brand exemplars, and platform launchers.
          </p>
        </div>
        <button
          onClick={handleSeedAll}
          disabled={saving}
          className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 hover:bg-indigo-600/30 transition-colors"
        >
          Seed All Defaults
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto no-scrollbar whitespace-nowrap">
        <button
          onClick={() => setActiveTab("niche")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === "niche"
              ? "bg-indigo-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          Single Niche
        </button>

        <button
          onClick={() => setActiveTab("brand")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === "brand"
              ? "bg-indigo-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          <Layers className="w-4 h-4" />
          Brand DNA
        </button>

        <button
          onClick={() => setActiveTab("memory")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === "memory"
              ? "bg-indigo-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          <Brain className="w-4 h-4" />
          Brand Memory ({memoryItems.length})
        </button>

        <button
          onClick={() => setActiveTab("exemplars")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === "exemplars"
              ? "bg-indigo-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Brand Exemplars ({exemplars.length})
        </button>

        <button
          onClick={() => setActiveTab("platforms")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === "platforms"
              ? "bg-indigo-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          <ExternalLink className="w-4 h-4" />
          Platform Launchers
        </button>

        <button
          onClick={() => setActiveTab("transfer")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
            activeTab === "transfer"
              ? "bg-indigo-600 text-white"
              : "text-slate-400 hover:text-white hover:bg-slate-800/60"
          }`}
        >
          <Download className="w-4 h-4" />
          Export / Import
        </button>
      </div>

      {/* Tab 1: Single Niche */}
      {activeTab === "niche" && (
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Single Niche Profile</h2>
              <p className="text-xs text-slate-400">
                In accordance with invariant #1, exactly one active niche profile guides discovery and filtering.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSeedNiche}
                disabled={saving}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
              >
                Seed Example Niche
              </button>
              <button
                type="button"
                onClick={handleSaveNiche}
                disabled={saving}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20"
              >
                <Save className="w-3.5 h-3.5" />
                {saving ? "Saving..." : "Save Niche Profile"}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Niche Name
                </label>
                <input
                  type="text"
                  value={niche.name}
                  onChange={(e) => setNiche({ ...niche, name: e.target.value })}
                  placeholder="e.g. AI Engineering & Coding Automation"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Target Audience
                </label>
                <input
                  type="text"
                  value={niche.audience}
                  onChange={(e) => setNiche({ ...niche, audience: e.target.value })}
                  placeholder="e.g. Software engineers, technical founders, automation builders"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  One-Sentence Definition
                </label>
                <textarea
                  rows={3}
                  value={niche.one_sentence_definition}
                  onChange={(e) => setNiche({ ...niche, one_sentence_definition: e.target.value })}
                  placeholder="Practical AI coding agents, developer automation workflows, and local LLM tooling tested on production tasks."
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Allowed Topics (Comma-separated)
                </label>
                <input
                  type="text"
                  value={niche.allowed_topics.join(", ")}
                  onChange={(e) =>
                    setNiche({
                      ...niche,
                      allowed_topics: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="coding agents, local LLMs, developer tools"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Blocked Topics (Filtered out by Niche Guard)
                </label>
                <input
                  type="text"
                  value={niche.blocked_topics.join(", ")}
                  onChange={(e) =>
                    setNiche({
                      ...niche,
                      blocked_topics: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="crypto trading, get rich quick, general consumer gadgets"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Negative Keywords (Auto-reject signals)
                </label>
                <input
                  type="text"
                  value={niche.negative_keywords.join(", ")}
                  onChange={(e) =>
                    setNiche({
                      ...niche,
                      negative_keywords: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="secret trick, replaced all coders, 100x money"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Brand DNA */}
      {activeTab === "brand" && (
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Single Brand DNA</h2>
              <p className="text-xs text-slate-400">
                All scripts, narration, captions, and visual rules inherit this brand identity.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSeedBrand}
                disabled={saving}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
              >
                Seed Example Brand
              </button>
              <button
                type="button"
                onClick={handleSaveBrand}
                disabled={saving}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20"
              >
                <Save className="w-3.5 h-3.5" />
                {saving ? "Saving..." : "Save Brand Profile"}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Brand Name
                </label>
                <input
                  type="text"
                  value={brand.brand_name}
                  onChange={(e) => setBrand({ ...brand, brand_name: e.target.value })}
                  placeholder="e.g. Practical AI Studio"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Brand Promise
                </label>
                <input
                  type="text"
                  value={brand.brand_promise}
                  onChange={(e) => setBrand({ ...brand, brand_promise: e.target.value })}
                  placeholder="Tested AI tools, automated workflows, and honest benchmarks without hype."
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Tone Attributes (Comma-separated)
                </label>
                <input
                  type="text"
                  value={brand.tone.join(", ")}
                  onChange={(e) =>
                    setBrand({
                      ...brand,
                      tone: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="evidence-driven, concise, practical, calm, transparent"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Preferred Vocabulary
                </label>
                <input
                  type="text"
                  value={brand.preferred_vocabulary.join(", ")}
                  onChange={(e) =>
                    setBrand({
                      ...brand,
                      preferred_vocabulary: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="benchmark, latency, trade-off, failure rate, reproducible"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Avoid Vocabulary (Hype words)
                </label>
                <input
                  type="text"
                  value={brand.avoid_vocabulary.join(", ")}
                  onChange={(e) =>
                    setBrand({
                      ...brand,
                      avoid_vocabulary: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="game-changer, insane, mind-blowing, unbelievable"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Banned Clichés
                </label>
                <input
                  type="text"
                  value={brand.banned_cliches.join(", ")}
                  onChange={(e) =>
                    setBrand({
                      ...brand,
                      banned_cliches: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="In today's fast-paced world..., Without further ado..."
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Claim Rules
                </label>
                <input
                  type="text"
                  value={brand.claim_rules.join(", ")}
                  onChange={(e) =>
                    setBrand({
                      ...brand,
                      claim_rules: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="Every speed claim must cite a benchmark run or primary source."
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  CTA Style
                </label>
                <input
                  type="text"
                  value={brand.cta_style}
                  onChange={(e) => setBrand({ ...brand, cta_style: e.target.value })}
                  placeholder="Direct, educational, and low-friction"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Monetization & Conversion CTAs */}
          <div className="border-t border-slate-800 pt-6">
            <h3 className="text-sm font-semibold text-white mb-1">Monetization & Conversion CTAs</h3>
            <p className="text-xs text-slate-400 mb-4">
              Configured lead magnets, newsletter hooks, and digital product CTAs automatically available to content engines.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Default Lead Magnet CTA
                </label>
                <input
                  type="text"
                  value={brand.default_lead_magnet || ""}
                  onChange={(e) => setBrand({ ...brand, default_lead_magnet: e.target.value })}
                  placeholder="e.g. Free Local AI Architecture Guide (local-ai.guide)"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Newsletter CTA
                </label>
                <input
                  type="text"
                  value={brand.newsletter_cta || ""}
                  onChange={(e) => setBrand({ ...brand, newsletter_cta: e.target.value })}
                  placeholder="e.g. Subscribe to the Fresh AI Weekly Brief for benchmark datasets"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Digital Product CTA
                </label>
                <input
                  type="text"
                  value={brand.digital_product_cta || ""}
                  onChange={(e) => setBrand({ ...brand, digital_product_cta: e.target.value })}
                  placeholder="e.g. Download the Complete Local Studio Starter Kit ($49)"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Brand Memory & Repetition */}
      {activeTab === "memory" && (
        <div className="space-y-6">
          {/* Header & Add Memory Form */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
            <h2 className="text-base font-semibold text-white mb-1">Record Brand Memory</h2>
            <p className="text-xs text-slate-400 mb-4">
              Persistent memory store for hooks, CTAs, topics, tested products, and conclusions. Brand QA queries this memory to prevent repetition and ensure brand continuity.
            </p>

            <form onSubmit={handleAddMemory} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Memory Type
                  </label>
                  <select
                    value={newMemory.memory_type}
                    onChange={(e) => setNewMemory({ ...newMemory, memory_type: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="hook">Hook</option>
                    <option value="cta">CTA</option>
                    <option value="topic">Topic</option>
                    <option value="tested_product">Tested Product</option>
                    <option value="conclusion">Conclusion</option>
                    <option value="visual_pattern">Visual Pattern</option>
                    <option value="frequent_phrase">Frequent Phrase</option>
                    <option value="thumbnail_wording">Thumbnail Wording</option>
                  </select>
                </div>

                <div className="md:col-span-3">
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Content / Pattern
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newMemory.content}
                      onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })}
                      placeholder="e.g. Stop paying OpenAI for batch summarization when Ollama 3.1 is 10x faster."
                      className="flex-1 px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                    />
                    <button
                      type="submit"
                      disabled={saving || !newMemory.content.trim()}
                      className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white whitespace-nowrap"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add to Memory
                    </button>
                  </div>
                </div>
              </div>
            </form>
          </div>

          {/* Filter Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {[
              { id: "all", label: "All Items" },
              { id: "hook", label: "Hooks" },
              { id: "cta", label: "CTAs" },
              { id: "topic", label: "Topics" },
              { id: "tested_product", label: "Tested Products" },
              { id: "conclusion", label: "Conclusions" },
              { id: "visual_pattern", label: "Visuals" },
              { id: "frequent_phrase", label: "Phrases" },
              { id: "thumbnail_wording", label: "Thumbnails" },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setMemoryFilter(f.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors whitespace-nowrap ${
                  memoryFilter === f.id
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-900 text-slate-400 border border-slate-800 hover:text-white"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Memory Items List */}
          <div className="space-y-3">
            {memoryItems
              .filter((m) => memoryFilter === "all" || m.memory_type === memoryFilter)
              .length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
                No brand memory recorded in this category yet. Memory items are automatically recorded upon script approval or manually above.
              </div>
            ) : (
              memoryItems
                .filter((m) => memoryFilter === "all" || m.memory_type === memoryFilter)
                .map((item) => (
                  <div
                    key={item.id}
                    className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start justify-between gap-4"
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-indigo-950 text-indigo-400 border border-indigo-800">
                          {item.memory_type.replace("_", " ")}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          Used {item.usage_count} {item.usage_count === 1 ? "time" : "times"}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          • Last used: {new Date(item.last_used_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-sm text-slate-200">{item.content}</p>
                    </div>

                    <button
                      onClick={() => handleDeleteMemory(item.id)}
                      className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-950/30 rounded-lg transition-colors"
                      title="Delete Memory Item"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Brand Exemplars */}
      {activeTab === "exemplars" && (
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
            <h2 className="text-base font-semibold text-white mb-1">Add Brand Exemplar</h2>
            <p className="text-xs text-slate-400 mb-4">
              Reference examples of approved hooks, scripts, captions, and do/don't guidelines.
            </p>

            <form onSubmit={handleAddExemplar} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Category
                  </label>
                  <select
                    value={newExemplar.category}
                    onChange={(e) => setNewExemplar({ ...newExemplar, category: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="approved_hook">Approved Hook</option>
                    <option value="approved_script">Approved Script</option>
                    <option value="approved_caption">Approved Caption</option>
                    <option value="do_example">Do Example</option>
                    <option value="dont_example">Don't Example</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Title
                  </label>
                  <input
                    type="text"
                    required
                    value={newExemplar.title}
                    onChange={(e) => setNewExemplar({ ...newExemplar, title: e.target.value })}
                    placeholder="e.g. Coding Agent Stress Test Hook"
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Platform
                  </label>
                  <select
                    value={newExemplar.platform}
                    onChange={(e) => setNewExemplar({ ...newExemplar, platform: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="all">All Platforms</option>
                    <option value="youtube">YouTube</option>
                    <option value="facebook">Facebook</option>
                    <option value="instagram">Instagram</option>
                    <option value="tiktok">TikTok</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Exemplar Content
                </label>
                <textarea
                  required
                  rows={3}
                  value={newExemplar.content}
                  onChange={(e) => setNewExemplar({ ...newExemplar, content: e.target.value })}
                  placeholder="Paste exemplar text or script snippet here..."
                  className="w-full px-3 py-2 text-sm rounded-lg bg-slate-950 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Exemplar
                </button>
              </div>
            </form>
          </div>

          {/* List */}
          <div className="space-y-3">
            {exemplars.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500 border border-dashed border-slate-800 rounded-xl">
                No brand exemplars added yet. Add approved hooks and scripts to guide generation quality.
              </div>
            ) : (
              exemplars.map((ex) => (
                <div key={ex.id} className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {ex.category.replace("_", " ").toUpperCase()}
                      </span>
                      <span className="text-xs font-medium text-slate-400">Platform: {ex.platform}</span>
                      <span className="text-sm font-semibold text-white">{ex.title}</span>
                    </div>
                    <p className="text-xs text-slate-300 whitespace-pre-wrap">{ex.content}</p>
                  </div>
                  <button
                    onClick={() => handleDeleteExemplar(ex.id)}
                    className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Platform Launchers */}
      {activeTab === "platforms" && (
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Platform Launchers (Manual V1)</h2>
              <p className="text-xs text-slate-400">
                Configure direct channel and publishing URLs for YouTube, Facebook, Instagram, and TikTok. (HTTPS required).
              </p>
            </div>
            <button
              onClick={handleSeedPlatforms}
              disabled={saving}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
            >
              Seed Example URLs
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {["youtube", "facebook", "instagram", "tiktok"].map((pName) => {
              const p = platforms[pName] || {
                platform: pName,
                channel_name: "",
                channel_url: "",
                publishing_url: "",
                account_handle: "",
                is_active: true,
              };

              return (
                <div key={pName} className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-bold uppercase tracking-wider text-indigo-400">
                      {pName}
                    </span>
                    <div className="flex items-center gap-2">
                      {p.publishing_url && (
                        <a
                          href={p.publishing_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-sky-400 transition-colors"
                        >
                          <span>Test Open</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                      <button
                        onClick={() => handleSavePlatform(pName)}
                        disabled={saving}
                        className="px-2.5 py-1 text-xs font-semibold rounded bg-slate-800 hover:bg-slate-700 text-white border border-slate-700"
                      >
                        Save
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-0.5">Channel Name</label>
                    <input
                      type="text"
                      value={p.channel_name}
                      onChange={(e) =>
                        setPlatforms({
                          ...platforms,
                          [pName]: { ...p, channel_name: e.target.value },
                        })
                      }
                      placeholder={`e.g. My ${pName} Channel`}
                      className="w-full px-2.5 py-1.5 text-xs rounded bg-slate-900 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-0.5">Publishing / Studio URL (HTTPS)</label>
                    <input
                      type="text"
                      value={p.publishing_url}
                      onChange={(e) =>
                        setPlatforms({
                          ...platforms,
                          [pName]: { ...p, publishing_url: e.target.value },
                        })
                      }
                      placeholder="https://studio.youtube.com/"
                      className="w-full px-2.5 py-1.5 text-xs rounded bg-slate-900 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-0.5">Public Channel URL (HTTPS)</label>
                    <input
                      type="text"
                      value={p.channel_url}
                      onChange={(e) =>
                        setPlatforms({
                          ...platforms,
                          [pName]: { ...p, channel_url: e.target.value },
                        })
                      }
                      placeholder="https://www.youtube.com/@mychannel"
                      className="w-full px-2.5 py-1.5 text-xs rounded bg-slate-900 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 5: Transfer */}
      {activeTab === "transfer" && (
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-6">
          <div className="border-b border-slate-800 pb-4">
            <h2 className="text-base font-semibold text-white">Export & Import Configuration</h2>
            <p className="text-xs text-slate-400">
              Download your Single Niche Profile, Brand DNA, and Platform settings as portable JSON or restore from backup.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Download className="w-4 h-4 text-indigo-400" />
                Export Configuration
              </h3>
              <p className="text-xs text-slate-400">
                Downloads an atomic snapshot of your studio's active niche, brand profile, exemplars, and platform URLs.
              </p>
              <button
                onClick={handleExport}
                className="w-full py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                Download Config JSON
              </button>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Upload className="w-4 h-4 text-sky-400" />
                Import Configuration
              </h3>
              <p className="text-xs text-slate-400">
                Paste JSON content to restore or apply external configuration.
              </p>
              <textarea
                rows={4}
                value={importJson}
                onChange={(e) => setImportJson(e.target.value)}
                placeholder='{"niche": {...}, "brand": {...}}'
                className="w-full p-2 text-xs font-mono rounded bg-slate-900 border border-slate-800 text-white focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={handleImport}
                disabled={saving || !importJson.trim()}
                className="w-full py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-50 transition-colors"
              >
                Apply Imported JSON
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
