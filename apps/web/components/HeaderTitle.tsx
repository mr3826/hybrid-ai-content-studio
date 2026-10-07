"use client";

import { useLanguage } from "@/lib/LanguageContext";

export function HeaderTitle() {
  const { t } = useLanguage();

  return (
    <div className="flex items-center gap-2 min-w-0">
      <span className="text-xs font-mono px-2 sm:px-2.5 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700 tracking-wide font-medium shadow-sm truncate max-w-[130px] xs:max-w-[200px] sm:max-w-none">
        <span className="hidden sm:inline">{t("header.appTitle", "Fresh Local AI Content Studio")}</span>
        <span className="sm:hidden font-semibold">{t("header.appTitleShort", "AI Studio")}</span>
      </span>
    </div>
  );
}
