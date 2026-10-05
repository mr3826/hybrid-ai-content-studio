"use client";

import { useLanguage } from "@/lib/LanguageContext";
import { Globe } from "lucide-react";

export function LanguageToggle() {
  const { locale, setLocale } = useLanguage();

  return (
    <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs shadow-sm">
      <button
        type="button"
        onClick={() => setLocale("bn")}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all font-medium ${
          locale === "bn"
            ? "bg-indigo-600 text-white shadow-sm font-semibold"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
        }`}
        title="বাংলা ভাষায় পরিবর্তন করুন"
      >
        <span className="text-sm">🇧🇩</span>
        <span>বাংলা</span>
      </button>

      <button
        type="button"
        onClick={() => setLocale("en")}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all font-medium ${
          locale === "en"
            ? "bg-indigo-600 text-white shadow-sm font-semibold"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
        }`}
        title="Switch to English"
      >
        <span className="text-sm">🇺🇸</span>
        <span>English</span>
      </button>
    </div>
  );
}
