"use client";

import { useEffect, useState } from "react";
import { getHealth, HealthData } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

export function HealthBadge() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const { t } = useLanguage();

  useEffect(() => {
    let mounted = true;
    async function check() {
      const data = await getHealth();
      if (mounted) {
        setHealth(data);
        setLoading(false);
      }
    }
    check();
    const interval = setInterval(check, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1 text-xs rounded-full bg-slate-800 text-slate-400 border border-slate-700">
        <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse"></span>
        {t("header.connecting", "Connecting to API...")}
      </div>
    );
  }

  if (!health || health.status !== "healthy") {
    return (
      <div className="flex items-center gap-2 px-3 py-1 text-xs rounded-full bg-red-950/60 text-red-400 border border-red-800/60">
        <span className="w-2 h-2 rounded-full bg-red-500"></span>
        {t("header.apiDisconnected", "API Disconnected (Port 8400)")}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1 text-xs rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 font-medium">
      <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
      {t("header.apiHealthy", "API Healthy")} &bull; {t("header.dbConnected", "DB Connected")} &bull; v{health.version}
    </div>
  );
}

