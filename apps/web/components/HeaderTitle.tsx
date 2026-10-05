"use client";

import { useLanguage } from "@/lib/LanguageContext";

export function HeaderTitle() {
  const { t } = useLanguage();

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700 tracking-wide font-medium shadow-sm">
        {t("header.appTitle", "Fresh Local AI Content Studio")}
      </span>
    </div>
  );
}
