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
  Bot,
  FlaskConical,
  Boxes,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: Layers },
  { href: "/sources", label: "Sources", icon: Rss },
  { href: "/trends", label: "Trends", icon: TrendingUp },
  { href: "/opportunities", label: "Opportunities", icon: Compass },
  { href: "/research", label: "Research", icon: BookOpen },
  { href: "/evidence", label: "Evidence", icon: ShieldCheck },
  { href: "/originality", label: "Originality", icon: FlaskConical },
  { href: "/content-families", label: "Content Families", icon: Boxes },
  { href: "/ai", label: "AI Engine", icon: Bot },
  { href: "/projects", label: "Projects", icon: Film },
  { href: "/engines", label: "Engines", icon: Cpu },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/70 p-4 flex flex-col justify-between shrink-0">
      <div>
        <div className="flex items-center gap-2 px-3 py-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20">
            EC
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-white leading-tight">Content Studio</h1>
            <p className="text-[11px] text-slate-400">Local-First Studio</p>
          </div>
        </div>

        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 mb-1">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          <span>Studio Invariants</span>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          1 Active Niche &bull; 1 Brand DNA &bull; Human-in-the-Loop &bull; No n8n
        </p>
      </div>
    </aside>
  );
}
