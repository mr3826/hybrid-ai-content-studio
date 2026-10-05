"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { Locale, translations } from "./translations";

interface LanguageContextType {
  locale: Locale;
  setLocale: (loc: Locale) => void;
  toggleLocale: () => void;
  t: (path: string, fallback?: string) => string;
  isBangla: boolean;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const STORAGE_KEY = "studio_locale";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  // Default to 'bn' as requested by the user
  const [locale, setLocaleState] = useState<Locale>("bn");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as Locale | null;
      if (saved === "bn" || saved === "en") {
        setLocaleState(saved);
      } else {
        // Default to 'bn'
        localStorage.setItem(STORAGE_KEY, "bn");
      }
    } catch {
      // ignore localStorage errors (e.g. incognito)
    }
    setMounted(true);
  }, []);

  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale);
    try {
      localStorage.setItem(STORAGE_KEY, newLocale);
      document.documentElement.lang = newLocale;
    } catch {
      // ignore
    }
  };

  const toggleLocale = () => {
    setLocale(locale === "bn" ? "en" : "bn");
  };

  const t = (path: string, fallback?: string): string => {
    const keys = path.split(".");
    let current: any = translations[locale];

    for (const k of keys) {
      if (current && typeof current === "object" && k in current) {
        current = current[k];
      } else {
        current = undefined;
        break;
      }
    }

    if (typeof current === "string") {
      return current;
    }

    // Try fallback to english if current is missing in target locale
    if (locale !== "en") {
      let enFallback: any = translations.en;
      for (const k of keys) {
        if (enFallback && typeof enFallback === "object" && k in enFallback) {
          enFallback = enFallback[k];
        } else {
          enFallback = undefined;
          break;
        }
      }
      if (typeof enFallback === "string") {
        return enFallback;
      }
    }

    return fallback ?? path;
  };

  return (
    <LanguageContext.Provider
      value={{
        locale,
        setLocale,
        toggleLocale,
        t,
        isBangla: locale === "bn",
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
