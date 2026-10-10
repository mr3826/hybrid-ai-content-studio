"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  Bot,
  Boxes,
  CheckSquare,
  ChevronDown,
  Compass,
  Cpu,
  Film,
  FlaskConical,
  HardDrive,
  Headphones,
  Layers,
  Lightbulb,
  Rss,
  Settings as SettingsIcon,
  Share2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  Video,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";

interface NavigationItem {
  href: string;
  key: string;
  fallback: string;
  icon: LucideIcon;
}

interface NavigationGroup {
  id: string;
  key: string;
  fallback: string;
  icon: LucideIcon;
  number?: string;
  items: NavigationItem[];
}

const DASHBOARD: NavigationItem = {
  href: "/",
  key: "nav.dashboard",
  fallback: "Dashboard",
  icon: Layers,
};

const NAV_GROUPS: NavigationGroup[] = [
  {
    id: "discover",
    number: "01",
    key: "nav.stageDiscover",
    fallback: "Discover",
    icon: Compass,
    items: [
      { href: "/sources", key: "nav.sources", fallback: "Sources", icon: Rss },
      { href: "/trends", key: "nav.trends", fallback: "Trends", icon: TrendingUp },
      { href: "/opportunities", key: "nav.opportunities", fallback: "Opportunities", icon: Compass },
    ],
  },
  {
    id: "verify",
    number: "02",
    key: "nav.stageVerify",
    fallback: "Verify",
    icon: ShieldCheck,
    items: [
      { href: "/research", key: "nav.research", fallback: "Research", icon: BookOpen },
      { href: "/evidence", key: "nav.evidence", fallback: "Evidence", icon: ShieldCheck },
      { href: "/originality", key: "nav.originality", fallback: "Originality", icon: FlaskConical },
    ],
  },
  {
    id: "create",
    number: "03",
    key: "nav.stageCreate",
    fallback: "Create",
    icon: Boxes,
    items: [
      { href: "/content-families", key: "nav.contentFamilies", fallback: "Content Families", icon: Boxes },
      { href: "/projects", key: "nav.projects", fallback: "Projects", icon: Film },
    ],
  },
  {
    id: "produce",
    number: "04",
    key: "nav.stageProduce",
    fallback: "Produce",
    icon: Film,
    items: [
      { href: "/asset-rights", key: "nav.assetRights", fallback: "Asset Rights", icon: ShieldAlert },
      { href: "/scene-studio", key: "nav.sceneStudio", fallback: "Scene Studio", icon: Video },
      { href: "/media-studio", key: "nav.mediaStudio", fallback: "Media Studio", icon: Headphones },
      { href: "/quality-gate", key: "nav.qualityGate", fallback: "Quality Gate", icon: CheckSquare },
    ],
  },
  {
    id: "publish",
    number: "05",
    key: "nav.stagePublish",
    fallback: "Publish",
    icon: Share2,
    items: [
      { href: "/publishing", key: "nav.publishing", fallback: "Publishing", icon: Share2 },
    ],
  },
  {
    id: "learn",
    number: "06",
    key: "nav.stageLearn",
    fallback: "Learn",
    icon: BarChart3,
    items: [
      { href: "/analytics", key: "nav.analytics", fallback: "Analytics", icon: BarChart3 },
      { href: "/feedback", key: "nav.feedback", fallback: "Feedback & Memory", icon: Lightbulb },
      { href: "/audience", key: "nav.audience", fallback: "Owned Audience", icon: Users },
    ],
  },
  {
    id: "tools",
    key: "nav.studioTools",
    fallback: "Studio tools",
    icon: Cpu,
    items: [
      { href: "/ai", key: "nav.ai", fallback: "AI Engine", icon: Bot },
      { href: "/engines", key: "nav.engines", fallback: "Engine Catalog", icon: Cpu },
      { href: "/cleanup", key: "nav.cleanup", fallback: "Cleanup & Backup", icon: HardDrive },
      { href: "/settings", key: "nav.settings", fallback: "Settings", icon: SettingsIcon },
    ],
  },
];

function isPathActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Navigation({ onNavigate }: { onNavigate?: () => void } = {}) {
  const pathname = usePathname();
  const { t } = useLanguage();
  const instanceId = useId().replace(/:/g, "");
  const activeGroupId = NAV_GROUPS.find((group) =>
    group.items.some((item) => isPathActive(pathname, item.href))
  )?.id ?? null;
  const [openGroupId, setOpenGroupId] = useState<string | null>(activeGroupId ?? "discover");

  useEffect(() => {
    if (activeGroupId) setOpenGroupId(activeGroupId);
  }, [activeGroupId]);

  const dashboardActive = isPathActive(pathname, DASHBOARD.href);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="mb-3 flex shrink-0 items-center gap-2 px-3 py-2">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 font-bold text-white shadow-md shadow-indigo-500/20">
          EC
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold leading-tight tracking-tight text-white">
            {t("nav.studioTitle", "Content Studio")}
          </h1>
          <p className="truncate text-[11px] text-slate-400">
            {t("nav.studioSubtitle", "Local-First Studio")}
          </p>
        </div>
      </div>

      <nav aria-label={t("nav.creatorNavigation", "Creator navigation")} className="flex min-h-0 flex-1 flex-col overflow-y-auto pr-1 custom-scrollbar">
        <Link
          href={DASHBOARD.href}
          onClick={onNavigate}
          aria-current={dashboardActive ? "page" : undefined}
          className={`mb-3 flex min-h-11 items-center gap-3 rounded-lg border px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 ${
            dashboardActive
              ? "border-indigo-500/30 bg-indigo-600/20 font-semibold text-indigo-300"
              : "border-transparent text-slate-300 hover:bg-slate-800/70 hover:text-white"
          }`}
        >
          <DASHBOARD.icon aria-hidden="true" className="h-4 w-4 shrink-0" />
          <span className="truncate">{t(DASHBOARD.key, DASHBOARD.fallback)}</span>
        </Link>

        <p className="mb-1 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
          {t("nav.creatorStages", "Creator journey")}
        </p>

        <div className="space-y-1">
          {NAV_GROUPS.map((group) => {
            const isOpen = openGroupId === group.id;
            const hasActiveItem = group.items.some((item) => isPathActive(pathname, item.href));
            const groupContentId = `${instanceId}-${group.id}-links`;
            const GroupIcon = group.icon;
            const isToolsGroup = group.id === "tools";

            const handleToggle = () => {
              setOpenGroupId((current) => current === group.id ? null : group.id);
            };

            return (
              <section
                key={group.id}
                className={isToolsGroup ? "mt-3 border-t border-slate-800/80 pt-3" : undefined}
              >
                <button
                  type="button"
                  aria-expanded={isOpen}
                  aria-controls={groupContentId}
                  onClick={handleToggle}
                  className={`flex min-h-11 w-full items-center gap-2 rounded-lg px-2.5 text-left text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 ${
                    hasActiveItem || isOpen
                      ? "text-slate-100"
                      : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                  }`}
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-slate-800/80 text-slate-300">
                    <GroupIcon aria-hidden="true" className="h-4 w-4" />
                  </span>
                  {group.number && (
                    <span className="w-5 shrink-0 text-[10px] font-bold tabular-nums text-slate-500">
                      {group.number}
                    </span>
                  )}
                  <span className="min-w-0 flex-1 truncate">{t(group.key, group.fallback)}</span>
                  <ChevronDown
                    aria-hidden="true"
                    className={`h-4 w-4 shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`}
                  />
                </button>

                <div
                  id={groupContentId}
                  hidden={!isOpen}
                  className="ml-5 mt-1 space-y-1 border-l border-slate-800 pl-2"
                >
                  {group.items.map((item) => {
                    const ItemIcon = item.icon;
                    const isActive = isPathActive(pathname, item.href);
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={onNavigate}
                        aria-current={isActive ? "page" : undefined}
                        className={`flex min-h-11 items-center gap-2.5 rounded-lg border px-2.5 py-2 text-[13px] font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 ${
                          isActive
                            ? "border-indigo-500/30 bg-indigo-600/20 font-semibold text-indigo-300"
                            : "border-transparent text-slate-400 hover:bg-slate-800/70 hover:text-slate-200"
                        }`}
                      >
                        <ItemIcon aria-hidden="true" className="h-4 w-4 shrink-0" />
                        <span className="truncate">{t(item.key, item.fallback)}</span>
                      </Link>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
      </nav>

      <div className="mt-3 shrink-0 rounded-lg border border-slate-800/80 bg-slate-950/60 p-3">
        <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-slate-300">
          <Sparkles aria-hidden="true" className="h-3.5 w-3.5 shrink-0 text-amber-400" />
          <span>{t("nav.invariantsTitle", "Studio Invariants")}</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          {t("nav.invariantsDesc", "1 Active Niche • 1 Brand DNA • Human-in-the-Loop • No n8n")}
        </p>
      </div>
    </div>
  );
}
