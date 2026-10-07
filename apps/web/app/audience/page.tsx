"use client";

import { useEffect, useState } from "react";
import {
  Users,
  Magnet,
  Link2,
  TrendingUp,
  DollarSign,
  CheckCircle,
  Copy,
  ExternalLink,
  Plus,
  Trash2,
  Edit3,
  Sparkles,
  Info,
  X,
  Share2,
  MousePointerClick,
  FileText,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import {
  LeadMagnet,
  AudienceConversion,
  AudienceSummary,
  UTMBuilderResponse,
  AudienceExplainResponse,
  getAudienceSummary,
  listLeadMagnets,
  createLeadMagnet,
  updateLeadMagnet,
  deleteLeadMagnet,
  listAudienceConversions,
  recordAudienceConversion,
  buildUTM,
  explainAudienceEconomics,
} from "@/lib/api";

export default function AudiencePage() {
  const { t } = useLanguage();

  const [summary, setSummary] = useState<AudienceSummary | null>(null);
  const [magnets, setMagnets] = useState<LeadMagnet[]>([]);
  const [conversions, setConversions] = useState<AudienceConversion[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"magnets" | "utmBuilder" | "conversions" | "economics">("magnets");

  // Modals & Drawers
  const [showMagnetModal, setShowMagnetModal] = useState(false);
  const [editingMagnet, setEditingMagnet] = useState<LeadMagnet | null>(null);
  const [magnetSaving, setMagnetSaving] = useState(false);
  const [magnetForm, setMagnetForm] = useState({
    title: "",
    slug: "",
    description: "",
    magnet_type: "cheat_sheet",
    landing_page_url: "",
    cta_copy: "Get the free blueprint and companion resource: {url}",
    status: "ACTIVE",
    target_pillar: "Core",
    estimated_value_usd: 15.0,
  });

  const [showConversionModal, setShowConversionModal] = useState(false);
  const [conversionSaving, setConversionSaving] = useState(false);
  const [conversionForm, setConversionForm] = useState({
    lead_magnet_id: "",
    content_item_id: "",
    platform: "youtube",
    utm_source: "youtube",
    utm_medium: "video_description",
    utm_campaign: "sc_general",
    clicks: 100,
    signups: 5,
    customers: 0,
    revenue_usd: 0.0,
    notes: "",
  });

  // UTM Tool State
  const [utmForm, setUtmForm] = useState({
    base_url: "",
    platform: "youtube",
    lead_magnet_slug: "",
    content_slug: "",
    campaign_name: "",
    custom_medium: "",
  });
  const [utmResult, setUtmResult] = useState<UTMBuilderResponse | null>(null);
  const [utmLoading, setUtmLoading] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Valuation Explanation Modal
  const [showExplainModal, setShowExplainModal] = useState(false);
  const [explanation, setExplanation] = useState<AudienceExplainResponse | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [sumRes, magnetsRes, convRes] = await Promise.all([
        getAudienceSummary(),
        listLeadMagnets(),
        listAudienceConversions(),
      ]);
      setSummary(sumRes);
      setMagnets(magnetsRes);
      setConversions(convRes);

      // Pre-select first magnet in UTM builder if available
      if (magnetsRes.length > 0 && !utmForm.lead_magnet_slug) {
        setUtmForm((prev) => ({
          ...prev,
          base_url: magnetsRes[0].landing_page_url,
          lead_magnet_slug: magnetsRes[0].slug,
        }));
      }
    } catch (err) {
      console.error("Failed to load audience data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleOpenCreateMagnet = () => {
    setEditingMagnet(null);
    setMagnetForm({
      title: "",
      slug: "",
      description: "",
      magnet_type: "cheat_sheet",
      landing_page_url: "",
      cta_copy: "Get the free blueprint and companion resource: {url}",
      status: "ACTIVE",
      target_pillar: "Core",
      estimated_value_usd: 15.0,
    });
    setShowMagnetModal(true);
  };

  const handleOpenEditMagnet = (m: LeadMagnet) => {
    setEditingMagnet(m);
    setMagnetForm({
      title: m.title,
      slug: m.slug,
      description: m.description,
      magnet_type: m.magnet_type,
      landing_page_url: m.landing_page_url,
      cta_copy: m.cta_copy,
      status: m.status,
      target_pillar: m.target_pillar,
      estimated_value_usd: m.estimated_value_usd,
    });
    setShowMagnetModal(true);
  };

  const handleSaveMagnet = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setMagnetSaving(true);
      if (editingMagnet) {
        await updateLeadMagnet(editingMagnet.id, magnetForm);
      } else {
        await createLeadMagnet(magnetForm);
      }
      setShowMagnetModal(false);
      await fetchData();
    } catch (err) {
      console.error("Failed to save lead magnet:", err);
      alert("Error saving lead magnet. Verify that slug is unique.");
    } finally {
      setMagnetSaving(false);
    }
  };

  const handleDeleteMagnet = async (id: string) => {
    if (!confirm("Are you sure you want to delete this lead magnet?")) return;
    try {
      await deleteLeadMagnet(id);
      await fetchData();
    } catch (err) {
      console.error("Failed to delete lead magnet:", err);
    }
  };

  const handleQuickUTM = (m: LeadMagnet) => {
    setUtmForm((prev) => ({
      ...prev,
      base_url: m.landing_page_url,
      lead_magnet_slug: m.slug,
      campaign_name: m.slug,
    }));
    setActiveTab("utmBuilder");
    handleBuildUTM({
      base_url: m.landing_page_url,
      platform: utmForm.platform,
      lead_magnet_slug: m.slug,
      content_slug: utmForm.content_slug,
      campaign_name: m.slug,
      custom_medium: utmForm.custom_medium,
    });
  };

  const handleBuildUTM = async (customPayload?: typeof utmForm) => {
    const payload = customPayload || utmForm;
    if (!payload.base_url) return;
    try {
      setUtmLoading(true);
      const res = await buildUTM({
        base_url: payload.base_url,
        platform: payload.platform,
        lead_magnet_slug: payload.lead_magnet_slug || undefined,
        content_slug: payload.content_slug || undefined,
        campaign_name: payload.campaign_name || undefined,
        custom_medium: payload.custom_medium || undefined,
      });
      setUtmResult(res);
    } catch (err) {
      console.error("Failed to generate UTM:", err);
    } finally {
      setUtmLoading(false);
    }
  };

  const handleSaveConversion = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setConversionSaving(true);
      await recordAudienceConversion({
        lead_magnet_id: conversionForm.lead_magnet_id || undefined,
        content_item_id: conversionForm.content_item_id || undefined,
        platform: conversionForm.platform,
        utm_source: conversionForm.utm_source,
        utm_medium: conversionForm.utm_medium,
        utm_campaign: conversionForm.utm_campaign,
        clicks: Number(conversionForm.clicks),
        signups: Number(conversionForm.signups),
        customers: Number(conversionForm.customers),
        revenue_usd: Number(conversionForm.revenue_usd),
        notes: conversionForm.notes || undefined,
        source: "MANUAL",
      });
      setShowConversionModal(false);
      await fetchData();
    } catch (err) {
      console.error("Failed to record conversion:", err);
    } finally {
      setConversionSaving(false);
    }
  };

  const handleOpenExplain = async () => {
    try {
      const exp = await explainAudienceEconomics();
      setExplanation(exp);
      setShowExplainModal(true);
    } catch (err) {
      console.error("Failed to fetch explanation:", err);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">
                {t("audiencePage.title", "Owned Audience & Lead Magnet Hub")}
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                {t("audiencePage.subtitle", "Convert rented social views into owned email subscribers and track subscriber asset valuation")}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleOpenExplain}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 text-sm font-medium transition-colors"
          >
            <Info className="w-4 h-4 text-indigo-400" />
            <span>{t("audiencePage.actions.explainModel", "Valuation Model")}</span>
          </button>
          <button
            onClick={handleOpenCreateMagnet}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium shadow-lg shadow-indigo-600/20 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>{t("audiencePage.actions.addMagnet", "New Lead Magnet")}</span>
          </button>
        </div>
      </div>

      {/* Executive KPIs */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider">{t("audiencePage.kpis.totalMagnets", "Lead Magnets")}</span>
              <Magnet className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-2xl font-bold text-white">{summary.total_lead_magnets}</div>
            <div className="text-[11px] text-emerald-400 mt-1">
              {summary.active_magnets} {t("audiencePage.kpis.activeMagnets", "Active")}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider">{t("audiencePage.kpis.totalClicks", "Traffic Clicks")}</span>
              <MousePointerClick className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold text-white">{summary.total_clicks.toLocaleString()}</div>
            <div className="text-[11px] text-slate-400 mt-1">Across all UTM links</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider">{t("audiencePage.kpis.totalSignups", "Owned Subscribers")}</span>
              <Users className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-400">{summary.total_signups.toLocaleString()}</div>
            <div className="text-[11px] text-slate-400 mt-1">Verified email leads</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider">{t("audiencePage.kpis.overallConversion", "Opt-In Rate")}</span>
              <TrendingUp className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-white">{summary.overall_conversion_rate_pct}%</div>
            <div className="text-[11px] text-slate-400 mt-1">
              {summary.overall_conversion_rate_pct >= 5.0 ? (
                <span className="text-emerald-400 font-semibold">Viral Benchmark</span>
              ) : summary.overall_conversion_rate_pct >= 3.0 ? (
                <span className="text-amber-400 font-semibold">On Target (3%)</span>
              ) : (
                <span className="text-slate-400">Baseline</span>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider">{t("audiencePage.kpis.listValue", "Est. List Value")}</span>
              <DollarSign className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-300">
              ${summary.estimated_total_list_value_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">Asset LTV valuation</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm">
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider">{t("audiencePage.kpis.directRevenue", "Direct Revenue")}</span>
              <Sparkles className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-purple-300">
              ${summary.total_revenue_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {summary.total_customers} {t("audiencePage.kpis.customers", "Customers")}
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2 overflow-x-auto no-scrollbar whitespace-nowrap">
        <button
          onClick={() => setActiveTab("magnets")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === "magnets"
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
          }`}
        >
          <Magnet className="w-4 h-4" />
          <span>{t("audiencePage.tabs.magnets", "Lead Magnets")}</span>
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-400">{magnets.length}</span>
        </button>

        <button
          onClick={() => setActiveTab("utmBuilder")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === "utmBuilder"
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
          }`}
        >
          <Link2 className="w-4 h-4" />
          <span>{t("audiencePage.tabs.utmBuilder", "UTM & CTA Generator")}</span>
        </button>

        <button
          onClick={() => setActiveTab("conversions")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === "conversions"
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>{t("audiencePage.tabs.conversions", "Conversions & Attribution")}</span>
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-400">{conversions.length}</span>
        </button>

        <button
          onClick={() => setActiveTab("economics")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === "economics"
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
          }`}
        >
          <DollarSign className="w-4 h-4" />
          <span>{t("audiencePage.tabs.economics", "Subscriber Economics")}</span>
        </button>
      </div>

      {/* TAB 1: Lead Magnets */}
      {activeTab === "magnets" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Active Lead Magnet Assets</h2>
            <button
              onClick={handleOpenCreateMagnet}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{t("audiencePage.actions.addMagnet", "Add Lead Magnet")}</span>
            </button>
          </div>

          {magnets.length === 0 ? (
            <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 border-dashed">
              <Magnet className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-300">
                {t("audiencePage.empty.magnets", "No lead magnets created yet")}
              </h3>
              <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
                Create checklists, architecture cheat sheets, templates or code repositories to capture durable owned subscribers.
              </p>
              <button
                onClick={handleOpenCreateMagnet}
                className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
              >
                Create First Lead Magnet
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {magnets.map((m) => (
                <div
                  key={m.id}
                  className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between space-y-4 group"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {m.magnet_type}
                      </span>
                      <span
                        className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                          m.status === "ACTIVE"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {m.status}
                      </span>
                    </div>

                    <h3 className="text-base font-semibold text-white mt-2 group-hover:text-indigo-400 transition-colors">
                      {m.title}
                    </h3>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1">{m.description}</p>
                    <div className="text-[11px] text-slate-500 font-mono mt-2 truncate">
                      /{m.slug}
                    </div>
                  </div>

                  {/* Metrics Badge */}
                  <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 grid grid-cols-3 gap-2 text-center">
                    <div>
                      <div className="text-xs font-bold text-white">{m.total_clicks}</div>
                      <div className="text-[10px] text-slate-500">Clicks</div>
                    </div>
                    <div>
                      <div className="text-xs font-bold text-emerald-400">{m.total_signups}</div>
                      <div className="text-[10px] text-slate-500">Signups</div>
                    </div>
                    <div>
                      <div className="text-xs font-bold text-amber-400">{m.conversion_rate_pct}%</div>
                      <div className="text-[10px] text-slate-500">Opt-in %</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/60 pt-3">
                    <div>
                      <span>List Value: </span>
                      <span className="font-semibold text-emerald-400">
                        ${m.estimated_asset_value_usd.toFixed(2)}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleQuickUTM(m)}
                        title="Create Tracking Link"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800"
                      >
                        <Link2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleOpenEditMagnet(m)}
                        title="Edit Lead Magnet"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteMagnet(m.id)}
                        title="Delete"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: UTM Builder & CTA Generator */}
      {activeTab === "utmBuilder" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Builder Form */}
          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-white">
                {t("audiencePage.utmTool.title", "Platform Tracking Link & Video Description CTA Generator")}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Construct deterministic UTM URLs that attribute subscriber opt-ins directly back to video descriptions and platform posts.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Lead Magnet Asset
                </label>
                <select
                  value={utmForm.lead_magnet_slug}
                  onChange={(e) => {
                    const selSlug = e.target.value;
                    const found = magnets.find((m) => m.slug === selSlug);
                    setUtmForm((prev) => ({
                      ...prev,
                      lead_magnet_slug: selSlug,
                      base_url: found ? found.landing_page_url : prev.base_url,
                      campaign_name: selSlug,
                    }));
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">-- Choose Lead Magnet --</option>
                  {magnets.map((m) => (
                    <option key={m.id} value={m.slug}>
                      {m.title} ({m.slug})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Landing Page Destination URL
                </label>
                <input
                  type="url"
                  value={utmForm.base_url}
                  onChange={(e) => setUtmForm({ ...utmForm, base_url: e.target.value })}
                  placeholder="https://yourbrand.com/free-checklist"
                  className="w-full px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-sm text-white font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Target Platform
                  </label>
                  <select
                    value={utmForm.platform}
                    onChange={(e) => setUtmForm({ ...utmForm, platform: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="youtube">YouTube</option>
                    <option value="tiktok">TikTok</option>
                    <option value="instagram">Instagram</option>
                    <option value="facebook">Facebook</option>
                    <option value="newsletter">Newsletter</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="direct">Direct</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Custom Medium (optional)
                  </label>
                  <input
                    type="text"
                    value={utmForm.custom_medium}
                    onChange={(e) => setUtmForm({ ...utmForm, custom_medium: e.target.value })}
                    placeholder="e.g. video_description, bio_link"
                    className="w-full px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Campaign Name Tag
                  </label>
                  <input
                    type="text"
                    value={utmForm.campaign_name}
                    onChange={(e) => setUtmForm({ ...utmForm, campaign_name: e.target.value })}
                    placeholder="e.g. video_series_ep12"
                    className="w-full px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Content Identifier Slug
                  </label>
                  <input
                    type="text"
                    value={utmForm.content_slug}
                    onChange={(e) => setUtmForm({ ...utmForm, content_slug: e.target.value })}
                    placeholder="e.g. stop-using-raw-threads"
                    className="w-full px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleBuildUTM()}
                disabled={utmLoading || !utmForm.base_url}
                className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-colors flex items-center justify-center gap-2"
              >
                {utmLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Link2 className="w-4 h-4" />
                )}
                <span>{t("audiencePage.utmTool.generateBtn", "Generate Tracking Link")}</span>
              </button>
            </div>
          </div>

          {/* Generated Result & Copy Snippets */}
          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-6">
            <h2 className="text-lg font-semibold text-white">
              {t("audiencePage.utmTool.outputTitle", "Tracked URL & Ready-to-Paste Copy")}
            </h2>

            {utmResult ? (
              <div className="space-y-4">
                {/* 1. Raw URL */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-300">Tracked Destination URL</span>
                    <button
                      onClick={() => handleCopy(utmResult.tracking_url, "raw")}
                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-mono"
                    >
                      {copiedKey === "raw" ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedKey === "raw" ? "Copied!" : "Copy"}</span>
                    </button>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-950 font-mono text-xs text-slate-300 break-all border border-slate-800 select-all">
                    {utmResult.tracking_url}
                  </div>
                </div>

                {/* 2. Markdown Link */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-300">Markdown Format</span>
                    <button
                      onClick={() => handleCopy(utmResult.formatted_markdown_link, "md")}
                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-mono"
                    >
                      {copiedKey === "md" ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedKey === "md" ? "Copied!" : "Copy"}</span>
                    </button>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-950 font-mono text-xs text-slate-300 break-all border border-slate-800 select-all">
                    {utmResult.formatted_markdown_link}
                  </div>
                </div>

                {/* 3. YouTube Video Description Snippet */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-300">YouTube / Social CTA Snippet</span>
                    <button
                      onClick={() => handleCopy(utmResult.copy_paste_cta, "cta")}
                      className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-mono"
                    >
                      {copiedKey === "cta" ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedKey === "cta" ? "Copied!" : "Copy"}</span>
                    </button>
                  </div>
                  <pre className="p-3 rounded-lg bg-slate-950 font-sans text-xs text-emerald-300 whitespace-pre-wrap border border-slate-800 select-all">
                    {utmResult.copy_paste_cta}
                  </pre>
                </div>

                {/* Tags Breakdown */}
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                  <div>
                    <span className="text-slate-500">Source:</span> {utmResult.utm_source}
                  </div>
                  <div>
                    <span className="text-slate-500">Medium:</span> {utmResult.utm_medium}
                  </div>
                  <div>
                    <span className="text-slate-500">Campaign:</span> {utmResult.utm_campaign}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center rounded-xl bg-slate-950/40 border border-slate-800/80 text-slate-500 text-sm">
                Select a lead magnet and click &quot;Generate Tracking Link&quot; to build copy-paste attribution snippets.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: Conversions & Attribution */}
      {activeTab === "conversions" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Conversion & Attribution Snapshots</h2>
              <p className="text-xs text-slate-400">
                Logged traffic and opt-in records attributing subscriber growth across platforms.
              </p>
            </div>
            <button
              onClick={() => setShowConversionModal(true)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-xs font-medium"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{t("audiencePage.actions.logConversion", "Log Conversion")}</span>
            </button>
          </div>

          {conversions.length === 0 ? (
            <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 border-dashed">
              <TrendingUp className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-300">
                {t("audiencePage.empty.conversions", "No conversion snapshots recorded yet")}
              </h3>
              <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
                Log manual snapshots from your email service provider (ConvertKit, Beehiiv, Mailchimp) or landing page software.
              </p>
              <button
                onClick={() => setShowConversionModal(true)}
                className="mt-4 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
              >
                Log First Conversion
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/40">
              <table className="w-full min-w-[750px] text-left text-xs text-slate-300">
                <thead className="bg-slate-950/60 text-slate-400 font-mono border-b border-slate-800">
                  <tr>
                    <th className="p-3">Platform</th>
                    <th className="p-3">Lead Magnet</th>
                    <th className="p-3">Campaign / Source</th>
                    <th className="p-3 text-right">Clicks</th>
                    <th className="p-3 text-right">Signups</th>
                    <th className="p-3 text-right">Opt-In %</th>
                    <th className="p-3 text-right">Customers</th>
                    <th className="p-3 text-right">Revenue ($)</th>
                    <th className="p-3">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {conversions.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="p-3 font-semibold text-white capitalize">{c.platform}</td>
                      <td className="p-3 font-medium text-indigo-400 truncate max-w-[200px]">
                        {c.lead_magnet_title || "General List"}
                      </td>
                      <td className="p-3 font-mono text-slate-400">{c.utm_campaign || c.utm_source || "organic"}</td>
                      <td className="p-3 text-right font-mono text-white">{c.clicks}</td>
                      <td className="p-3 text-right font-mono font-bold text-emerald-400">{c.signups}</td>
                      <td className="p-3 text-right font-mono font-bold text-amber-400">{c.conversion_rate_pct}%</td>
                      <td className="p-3 text-right font-mono text-purple-400">{c.customers}</td>
                      <td className="p-3 text-right font-mono text-white">${c.revenue_usd.toFixed(2)}</td>
                      <td className="p-3 text-slate-400 truncate max-w-[150px]">{c.notes || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Subscriber Economics */}
      {activeTab === "economics" && summary && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Platform Attribution Breakdown */}
            <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
              <h3 className="text-base font-semibold text-white">Platform Conversion Attribution</h3>
              <p className="text-xs text-slate-400">
                Comparing audience conversion velocity and revenue across target social distribution channels.
              </p>

              <div className="space-y-3">
                {Object.entries(summary.by_platform).map(([platform, data]) => (
                  <div key={platform} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-white capitalize text-sm">{platform}</span>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {data.clicks} clicks • {data.signups} signups
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-emerald-400">{data.conversion_rate_pct}% Opt-In</div>
                      <div className="text-[11px] text-purple-300">${data.revenue_usd.toFixed(2)} direct revenue</div>
                    </div>
                  </div>
                ))}

                {Object.keys(summary.by_platform).length === 0 && (
                  <div className="text-xs text-slate-500 p-4 text-center">No platform conversions recorded yet.</div>
                )}
              </div>
            </div>

            {/* Top Performing Lead Magnets */}
            <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
              <h3 className="text-base font-semibold text-white">Top Converting Lead Magnets</h3>
              <p className="text-xs text-slate-400">
                Ranked by owned subscriber acquisition volume and estimated list equity.
              </p>

              <div className="space-y-3">
                {summary.top_performing_magnets.map((m) => (
                  <div key={m.id} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-white text-sm">{m.title}</span>
                      <div className="text-[11px] text-indigo-400 font-mono mt-0.5">/{m.slug}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-emerald-400">{m.signups} Leads ({m.conversion_rate_pct}%)</div>
                      <div className="text-[11px] text-slate-400">
                        ${m.estimated_asset_value_usd.toFixed(2)} asset value
                      </div>
                    </div>
                  </div>
                ))}

                {summary.top_performing_magnets.length === 0 && (
                  <div className="text-xs text-slate-500 p-4 text-center">No lead magnets with conversions yet.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CREATE / EDIT LEAD MAGNET MODAL */}
      {showMagnetModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-semibold text-white">
                {editingMagnet
                  ? t("audiencePage.magnetModal.editTitle", "Edit Lead Magnet")
                  : t("audiencePage.magnetModal.createTitle", "Create New Lead Magnet")}
              </h3>
              <button onClick={() => setShowMagnetModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveMagnet} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  {t("audiencePage.magnetModal.title", "Asset Title")} *
                </label>
                <input
                  type="text"
                  required
                  value={magnetForm.title}
                  onChange={(e) => {
                    const title = e.target.value;
                    const autoSlug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
                    setMagnetForm((prev) => ({
                      ...prev,
                      title,
                      slug: editingMagnet ? prev.slug : autoSlug,
                    }));
                  }}
                  placeholder="e.g. FastAPI Microservices Architecture Checklist"
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    {t("audiencePage.magnetModal.slug", "Unique Slug")} *
                  </label>
                  <input
                    type="text"
                    required
                    value={magnetForm.slug}
                    onChange={(e) => setMagnetForm({ ...magnetForm, slug: e.target.value })}
                    placeholder="fastapi-checklist"
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    {t("audiencePage.magnetModal.type", "Resource Type")}
                  </label>
                  <select
                    value={magnetForm.magnet_type}
                    onChange={(e) => setMagnetForm({ ...magnetForm, magnet_type: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="cheat_sheet">Cheat Sheet</option>
                    <option value="checklist">Checklist</option>
                    <option value="template">Template</option>
                    <option value="code_repository">Code Repository</option>
                    <option value="free_guide">Free Guide</option>
                    <option value="mini_course">Mini Course</option>
                    <option value="tool">Tool / Calculator</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  {t("audiencePage.magnetModal.url", "Landing Page Destination URL")} *
                </label>
                <input
                  type="url"
                  required
                  value={magnetForm.landing_page_url}
                  onChange={(e) => setMagnetForm({ ...magnetForm, landing_page_url: e.target.value })}
                  placeholder="https://yourbrand.com/fastapi-checklist"
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  {t("audiencePage.magnetModal.cta", "Call-to-Action Copy")}
                </label>
                <textarea
                  rows={2}
                  value={magnetForm.cta_copy}
                  onChange={(e) => setMagnetForm({ ...magnetForm, cta_copy: e.target.value })}
                  placeholder="Download the full code repository and blueprint here: {url}"
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    {t("audiencePage.magnetModal.estValue", "Estimated Value / Lead ($)")}
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={magnetForm.estimated_value_usd}
                    onChange={(e) => setMagnetForm({ ...magnetForm, estimated_value_usd: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    {t("audiencePage.magnetModal.status", "Asset Status")}
                  </label>
                  <select
                    value={magnetForm.status}
                    onChange={(e) => setMagnetForm({ ...magnetForm, status: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="PAUSED">PAUSED</option>
                    <option value="ARCHIVED">ARCHIVED</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowMagnetModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={magnetSaving}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
                >
                  {magnetSaving ? "Saving..." : t("audiencePage.magnetModal.save", "Save Lead Magnet")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RECORD CONVERSION MODAL */}
      {showConversionModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-semibold text-white">
                {t("audiencePage.conversionModal.title", "Log Traffic & Conversion Snapshot")}
              </h3>
              <button onClick={() => setShowConversionModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveConversion} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Lead Magnet Asset
                </label>
                <select
                  value={conversionForm.lead_magnet_id}
                  onChange={(e) => setConversionForm({ ...conversionForm, lead_magnet_id: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">General Audience / No Magnet</option>
                  {magnets.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Platform
                  </label>
                  <select
                    value={conversionForm.platform}
                    onChange={(e) => {
                      const p = e.target.value;
                      setConversionForm((prev) => ({
                        ...prev,
                        platform: p,
                        utm_source: p,
                      }));
                    }}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="youtube">YouTube</option>
                    <option value="tiktok">TikTok</option>
                    <option value="instagram">Instagram</option>
                    <option value="facebook">Facebook</option>
                    <option value="newsletter">Newsletter</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="direct">Direct</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Campaign / Medium Tag
                  </label>
                  <input
                    type="text"
                    value={conversionForm.utm_campaign}
                    onChange={(e) => setConversionForm({ ...conversionForm, utm_campaign: e.target.value })}
                    placeholder="sc_growth"
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Link Clicks
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={conversionForm.clicks}
                    onChange={(e) => setConversionForm({ ...conversionForm, clicks: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Subscribers / Signups
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={conversionForm.signups}
                    onChange={(e) => setConversionForm({ ...conversionForm, signups: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Paying Customers
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={conversionForm.customers}
                    onChange={(e) => setConversionForm({ ...conversionForm, customers: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Direct Revenue ($ USD)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={conversionForm.revenue_usd}
                    onChange={(e) => setConversionForm({ ...conversionForm, revenue_usd: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Notes & Context
                </label>
                <textarea
                  rows={2}
                  value={conversionForm.notes}
                  onChange={(e) => setConversionForm({ ...conversionForm, notes: e.target.value })}
                  placeholder="Traffic spike from long-form YouTube video timestamp 04:22..."
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowConversionModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={conversionSaving}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors"
                >
                  {conversionSaving ? "Saving..." : t("audiencePage.conversionModal.save", "Save Conversion Record")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EXPLANATION MODAL */}
      {showExplainModal && explanation && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-5 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-indigo-400" />
                <h3 className="text-lg font-semibold text-white">Audience Valuation & Attribution Model</h3>
              </div>
              <button onClick={() => setShowExplainModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed">{explanation.summary}</p>

            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase text-slate-400 tracking-wider">Evaluation Factors</h4>
              {explanation.factors.map((f, i) => (
                <div key={i} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="flex items-center justify-between text-xs font-semibold text-white">
                    <span>{f.factor}</span>
                    <span className="text-indigo-400 font-mono">{(f.weight * 100).toFixed(0)}% Weight</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{f.description}</p>
                </div>
              ))}
            </div>

            <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-500/20 text-xs text-indigo-300">
              <div className="font-semibold text-white mb-1">Economics Formula:</div>
              <div>{explanation.economics_breakdown.formula}</div>
              <div className="mt-1 text-[11px] text-slate-400">
                Target Benchmark: {explanation.economics_breakdown.target_conversion_rate_pct}% opt-in rate
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowExplainModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
