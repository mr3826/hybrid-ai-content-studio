"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Compass, 
  Sparkles, 
  Film, 
  Cpu, 
  Settings as SettingsIcon,
  Layers,
  Rss,
  TrendingUp,
  BookOpen,
  ShieldCheck,
  ShieldAlert,
  Bot,
  FlaskConical,
  Boxes,
  Share2,
  Video,
  Headphones,
  CheckSquare,
  BarChart3,
  Lightbulb,
  Users,
} from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";

const NAV_CONFIG = [
  { href: "/", key: "nav.dashboard", fallback: "Dashboard", icon: Layers },
  { href: "/sources", key: "nav.sources", fallback: "Sources", icon: Rss },
  { href: "/trends", key: "nav.trends", fallback: "Trends", icon: TrendingUp },
  { href: "/opportunities", key: "nav.opportunities", fallback: "Opportunities", icon: Compass },
  { href: "/research", key: "nav.research", fallback: "Research", icon: BookOpen },
  { href: "/evidence", key: "nav.evidence", fallback: "Evidence", icon: ShieldCheck },
  { href: "/originality", key: "nav.originality", fallback: "Originality", icon: FlaskConical },
  { href: "/content-families", key: "nav.contentFamilies", fallback: "Content Families", icon: Boxes },
  { href: "/publishing", key: "nav.publishing", fallback: "Publishing", icon: Share2 },
  { href: "/asset-rights", key: "nav.assetRights", fallback: "Asset Rights", icon: ShieldAlert },
  { href: "/scene-studio", key: "nav.sceneStudio", fallback: "Scene Studio", icon: Video },
  { href: "/media-studio", key: "nav.mediaStudio", fallback: "Media Studio", icon: Headphones },
  { href: "/quality-gate", key: "nav.qualityGate", fallback: "Quality Gate", icon: CheckSquare },
  { href: "/analytics", key: "nav.analytics", fallback: "Analytics", icon: BarChart3 },
  { href: "/feedback", key: "nav.feedback", fallback: "Feedback & Memory", icon: Lightbulb },
  { href: "/audience", key: "nav.audience", fallback: "Owned Audience", icon: Users },
  { href: "/ai", key: "nav.ai", fallback: "AI Engine", icon: Bot },
  { href: "/projects", key: "nav.projects", fallback: "Projects", icon: Film },
  { href: "/engines", key: "nav.engines", fallback: "Engines", icon: Cpu },
  { href: "/settings", key: "nav.settings", fallback: "Settings", icon: SettingsIcon },
];

export function Navigation() {
  const pathname = usePathname();
  const { t } = useLanguage();

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/70 p-4 flex flex-col justify-between shrink-0">
      <div>
        <div className="flex items-center gap-2 px-3 py-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20">
            EC
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-white leading-tight">
              {t("nav.studioTitle", "Content Studio")}
            </h1>
            <p className="text-[11px] text-slate-400">
              {t("nav.studioSubtitle", "Local-First Studio")}
            </p>
          </div>
        </div>

        <nav className="space-y-1">
          {NAV_CONFIG.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 font-semibold"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className="truncate">{t(item.key, item.fallback)}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-1">
          <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span>{t("nav.invariantsTitle", "Studio Invariants")}</span>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          {t("nav.invariantsDesc", "1 Active Niche • 1 Brand DNA • Human-in-the-Loop • No n8n")}
        </p>
      </div>
    </aside>
  );
}

