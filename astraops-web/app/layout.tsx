import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AstraOps — Mission Intelligence",
  description: "Turning live space data into operational decisions.",
};

const NAV = [
  { href: "/", label: "Mission Dashboard" },
  { href: "/conjunctions", label: "Conjunction Watch" },
  { href: "/spaceweather", label: "Space Weather" },
  { href: "/research", label: "Research Copilot" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 antialiased">
        <div className="flex min-h-screen">
          <aside className="w-64 shrink-0 border-r border-slate-800 bg-slate-900/60 p-6">
            <Link href="/" className="block">
              <div className="text-xl font-semibold tracking-tight">AstraOps</div>
              <div className="mt-1 text-xs text-slate-500">Mission Intelligence</div>
            </Link>
            <nav className="mt-8 space-y-1">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href}
                  className="block rounded-md px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:text-white">
                  {n.label}
                </Link>
              ))}
            </nav>
            <div className="mt-10 border-t border-slate-800 pt-4 text-[11px] leading-relaxed text-slate-600">
              Data: CelesTrak · NASA DONKI<br/>Reasoning: IBM Granite on watsonx
            </div>
          </aside>
          <main className="flex-1 overflow-x-hidden p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
