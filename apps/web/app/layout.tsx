import type { Metadata } from "next";
import "./globals.css";
import { Navigation } from "@/components/Navigation";
import { HealthBadge } from "@/components/HealthBadge";
import { LanguageToggle } from "@/components/LanguageToggle";
import { HeaderTitle } from "@/components/HeaderTitle";
import { LanguageProvider } from "@/lib/LanguageContext";

export const metadata: Metadata = {
  title: "Fresh Local AI Content Studio",
  description: "Local-first AI assisted content studio",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="bn">
      <body className="flex h-screen overflow-hidden bg-slate-950 text-slate-100">
        <LanguageProvider>
          <Navigation />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <header className="h-14 border-b border-slate-800 bg-slate-900/40 px-6 flex items-center justify-between shrink-0">
              <HeaderTitle />
              <div className="flex items-center gap-3">
                <LanguageToggle />
                <HealthBadge />
              </div>
            </header>
            <main className="flex-1 overflow-y-auto p-8">
              {children}
            </main>
          </div>
        </LanguageProvider>
      </body>
    </html>
  );
}

