import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/AppShell";
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
      <body className="h-screen w-full overflow-hidden bg-slate-950 text-slate-100">
        <LanguageProvider>
          <AppShell>{children}</AppShell>
        </LanguageProvider>
      </body>
    </html>
  );
}

