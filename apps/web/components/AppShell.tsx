"use client";

import React, { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { Navigation } from "@/components/Navigation";
import { HeaderTitle } from "@/components/HeaderTitle";
import { LanguageToggle } from "@/components/LanguageToggle";
import { HealthBadge } from "@/components/HealthBadge";
import { useLanguage } from "@/lib/LanguageContext";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const { t } = useLanguage();

  // Automatically close mobile menu when navigating to a new route
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  // Close mobile menu on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-950 text-slate-100">
      {/* Desktop Sidebar (hidden on mobile and tablet screens < lg) */}
      <aside className="hidden lg:flex w-64 border-r border-slate-800 bg-slate-900/70 p-4 flex-col justify-between shrink-0 h-screen overflow-hidden">
        <Navigation />
      </aside>

      {/* Mobile Slide-Over Drawer & Overlay (lg:hidden) */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          {/* Backdrop Blur Overlay */}
          <div
            className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />

          {/* Drawer Panel */}
          <div className="fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-slate-900 border-r border-slate-800 p-4 flex flex-col justify-between shadow-2xl animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 shrink-0">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                {t("header.menu", "Menu")}
              </span>
              <button
                type="button"
                data-testid="mobile-menu-close-button"
                onClick={() => setMobileMenuOpen(false)}
                className="flex min-h-11 min-w-11 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                aria-label={t("header.closeMenu", "Close menu")}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 flex flex-col overflow-hidden min-h-0">
              <Navigation onNavigate={() => setMobileMenuOpen(false)} />
            </div>
          </div>
        </div>
      )}

      {/* Main App Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Sticky Header with responsive padding and items */}
        <header className="h-14 border-b border-slate-800 bg-slate-900/40 px-3 sm:px-6 flex items-center justify-between shrink-0 gap-2">
          <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
            {/* Hamburger button on mobile */}
            <button
              type="button"
              data-testid="mobile-menu-button"
              onClick={() => setMobileMenuOpen(true)}
              className="lg:hidden flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-800/80 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
              aria-label={t("header.menu", "Menu")}
            >
              <Menu className="w-5 h-5" />
            </button>
            <HeaderTitle />
          </div>

          <div className="flex items-center gap-1.5 sm:gap-3 shrink-0">
            <LanguageToggle />
            <HealthBadge />
          </div>
        </header>

        {/* Scrollable Page Body with Responsive Padding */}
        <main className="flex-1 overflow-y-auto p-3 sm:p-5 md:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
