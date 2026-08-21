import type { Metadata } from "next";
import "./globals.css";
import NavRail from "@/components/NavRail";
import StatusStrip from "@/components/StatusStrip";

export const metadata: Metadata = {
  title: "AstraOps — Mission Intelligence",
  description: "Live orbital and heliophysics data, screened and interpreted.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=IBM+Plex+Sans+Condensed:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap" />
      </head>
      <body>
        <StatusStrip />
        <div className="flex min-h-screen">
          <aside className="w-56 shrink-0 border-r px-6 py-7" style={{ borderColor: "var(--rule)", background: "var(--sheet)" }}>
            <div className="text-[16px] font-medium tracking-[0.22em]">ASTRAOPS</div>
            <div className="eyebrow mt-1.5">Mission intelligence</div>
            <NavRail />
            <div className="mt-12 space-y-1 text-[10px] leading-relaxed" style={{ color: "var(--ink-dim)" }}>
              <div>CELESTRAK · NASA DONKI</div>
              <div>IBM GRANITE ON WATSONX</div>
            </div>
          </aside>
          <main className="min-w-0 flex-1 px-9 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
