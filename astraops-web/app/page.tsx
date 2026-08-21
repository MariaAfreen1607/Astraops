"use client";
import { useEffect, useState } from "react";
import { api, SatelliteList, SpaceWeather, ConjunctionScreen } from "@/lib/api";

export default function Dashboard() {
  const [sats, setSats] = useState<SatelliteList | null>(null);
  const [sw, setSw] = useState<SpaceWeather | null>(null);
  const [conj, setConj] = useState<ConjunctionScreen | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<SatelliteList>("/satellites?group=stations").then(setSats).catch(e => setErr(e.message));
    api<SpaceWeather>("/spaceweather").then(setSw).catch(() => {});
    api<ConjunctionScreen>("/conjunctions?group=starlink&threshold_km=20").then(setConj).catch(() => {});
  }, []);

  const strongestFlare = sw?.solar_flares
    ?.filter(f => f.class_type)
    .sort((a, b) => (b.class_type ?? "").localeCompare(a.class_type ?? ""))[0];

  return (
    <div>
      <h1 className="text-2xl font-semibold">Mission Dashboard</h1>
      <p className="mt-1 text-sm text-slate-400">
        Live orbital and heliophysics data, screened and interpreted.
      </p>

      {err && <div className="mt-6 rounded border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">
        Backend unreachable: {err}. Is the API running on port 8000?
      </div>}

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card title="Tracked objects (stations)" value={sats ? String(sats.count) : "…"}
              sub={sats ? `source: ${sats.source}` : "loading"} />
        <Card title="Conjunctions < 20 km" value={conj ? String(conj.events.length) : "…"}
              sub={conj ? `${conj.total_pairs_screened.toLocaleString()} pairs screened` : "screening…"} />
        <Card title="Strongest flare (7d)" value={strongestFlare?.class_type ?? (sw ? "none" : "…")}
              sub={strongestFlare?.active_region ? `active region ${strongestFlare.active_region}` : "NASA DONKI"} />
      </div>

      <section className="mt-10">
        <h2 className="text-sm font-medium uppercase tracking-wide text-slate-400">Highest-risk approaches</h2>
        <div className="mt-3 overflow-hidden rounded-lg border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900 text-left text-xs uppercase text-slate-500">
              <tr><th className="p-3">Primary</th><th className="p-3">Secondary</th>
                  <th className="p-3">Miss (km)</th><th className="p-3">Rel. vel (km/s)</th><th className="p-3">Risk</th></tr>
            </thead>
            <tbody>
              {conj?.events.slice(0, 5).map((e, i) => (
                <tr key={i} className="border-t border-slate-800">
                  <td className="p-3">{e.sat1_name}</td>
                  <td className="p-3">{e.sat2_name}</td>
                  <td className="p-3 font-mono">{e.min_range_km.toFixed(2)}</td>
                  <td className="p-3 font-mono">{e.relative_velocity_km_s?.toFixed(2) ?? "—"}</td>
                  <td className="p-3"><RiskBadge level={e.risk_level} /></td>
                </tr>
              ))}
              {conj && conj.events.length === 0 && (
                <tr><td colSpan={5} className="p-4 text-slate-500">No approaches below threshold.</td></tr>
              )}
              {!conj && <tr><td colSpan={5} className="p-4 text-slate-500">Propagating orbits…</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Card({ title, value, sub }: { title: string; value: string; sub: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-5">
      <div className="text-xs uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-2 text-3xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{sub}</div>
    </div>
  );
}

export function RiskBadge({ level }: { level: string }) {
  const c = level === "HIGH" ? "bg-red-950 text-red-300 border-red-900"
    : level === "MEDIUM" ? "bg-amber-950 text-amber-300 border-amber-900"
    : "bg-slate-800 text-slate-300 border-slate-700";
  return <span className={`rounded border px-2 py-0.5 text-xs ${c}`}>{level}</span>;
}
