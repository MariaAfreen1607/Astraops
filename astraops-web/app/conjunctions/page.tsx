"use client";
import { useEffect, useState } from "react";
import { api, ConjunctionScreen, Brief, SeparationProfile } from "@/lib/api";
import SeparationChart from "@/components/SeparationChart";

export default function Conjunctions() {
  const [group, setGroup] = useState("starlink");
  const [threshold, setThreshold] = useState(20);
  const [data, setData] = useState<ConjunctionScreen | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [loading, setLoading] = useState(false);
  const [briefing, setBriefing] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [profile, setProfile] = useState<SeparationProfile | null>(null);
  const [profiling, setProfiling] = useState(false);

  const loadProfile = (a: string, b: string) => {
    setProfiling(true); setProfile(null);
    api<SeparationProfile>(`/conjunctions/profile?norad_a=${a}&norad_b=${b}&group=${group}&window_minutes=180&step_seconds=10`)
      .then(setProfile).catch(e => setErr(e.message)).finally(() => setProfiling(false));
  };

  const run = () => {
    setLoading(true); setErr(null); setData(null); setBrief(null); setProfile(null);
    api<ConjunctionScreen>(`/conjunctions?group=${group}&threshold_km=${threshold}`)
      .then(setData).catch(e => setErr(e.message)).finally(() => setLoading(false));
  };

  useEffect(run, []);

  const getBrief = () => {
    setBriefing(true);
    api<Brief>(`/briefs/conjunction?group=${group}&threshold_km=${threshold}`)
      .then(setBrief).catch(e => setErr(e.message)).finally(() => setBriefing(false));
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold">Conjunction Watch</h1>
      <p className="mt-1 text-sm text-slate-400">
        SGP4 propagation over a 3-hour window, refined to 1-second resolution near closest approach.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-3">
        <label className="text-xs text-slate-400">
          <div className="mb-1">CelesTrak group</div>
          <select value={group} onChange={e => setGroup(e.target.value)}
            className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100">
            <option value="starlink">starlink</option>
            <option value="stations">stations</option>
            <option value="oneweb">oneweb</option>
            <option value="iridium-NEXT">iridium-NEXT</option>
            <option value="active">active</option>
          </select>
        </label>
        <label className="text-xs text-slate-400">
          <div className="mb-1">Threshold (km)</div>
          <input type="number" value={threshold} onChange={e => setThreshold(Number(e.target.value))}
            className="w-28 rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
        </label>
        <button onClick={run} disabled={loading}
          className="rounded bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 disabled:opacity-50">
          {loading ? "Screening…" : "Run screening"}
        </button>
        {data && data.events.length > 0 && (
          <button onClick={getBrief} disabled={briefing}
            className="rounded border border-slate-700 px-4 py-2 text-sm disabled:opacity-50">
            {briefing ? "Granite is analysing…" : "AI risk brief"}
          </button>
        )}
      </div>

      {err && <div className="mt-6 rounded border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{err}</div>}

      {brief && (
        <div className="mt-6 rounded-lg border border-indigo-900 bg-indigo-950/30 p-5">
          <div className="text-xs uppercase tracking-wide text-indigo-400">
            AI brief · {brief.model_used}
          </div>
          <div className="mt-1 text-sm font-medium">{brief.subject}</div>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200">{brief.brief}</pre>
        </div>
      )}

      {data && (
        <>
          <div className="mt-8 text-xs text-slate-500">
            {data.total_pairs_screened.toLocaleString()} pairs screened · {data.events.length} below {data.threshold_km} km
          </div>
          <div className="mt-3 overflow-hidden rounded-lg border border-slate-800">
            <table className="w-full text-sm">
              <thead className="bg-slate-900 text-left text-xs uppercase text-slate-500">
                <tr><th className="p-3">Primary</th><th className="p-3">Secondary</th><th className="p-3">TCA (UTC)</th>
                    <th className="p-3">Miss (km)</th><th className="p-3">Rel. vel (km/s)</th>
                    <th className="p-3">Pc</th><th className="p-3">Risk</th></tr>
              </thead>
              <tbody>
                {data.events.map((e, i) => (
                  <tr key={i} onClick={() => loadProfile(e.sat1_norad, e.sat2_norad)}
                      className="cursor-pointer border-t border-slate-800 hover:bg-slate-900/40">
                    <td className="p-3">{e.sat1_name}<div className="text-xs text-slate-600">{e.sat1_norad}</div></td>
                    <td className="p-3">{e.sat2_name}<div className="text-xs text-slate-600">{e.sat2_norad}</div></td>
                    <td className="p-3 font-mono text-xs">{new Date(e.tca).toISOString().replace("T"," ").slice(0,19)}</td>
                    <td className="p-3 font-mono">{e.min_range_km.toFixed(3)}</td>
                    <td className="p-3 font-mono">{e.relative_velocity_km_s?.toFixed(3) ?? "—"}</td>
                    <td className="p-3 font-mono text-xs">{e.probability_of_collision?.toExponential(2) ?? "—"}</td>
                    <td className="p-3"><Badge level={e.risk_level} /></td>
                  </tr>
                ))}
                {data.events.length === 0 && (
                  <tr><td colSpan={7} className="p-4 text-slate-500">No approaches below threshold in this window.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-600">
            Click any row to plot its approach geometry.{" "}
            Pc assumes isotropic 200 m covariance and 20 m combined hard-body radius — screening defaults, not operator covariances.
          </p>
        </>
      )}

      {profiling && <div className="mt-6 text-sm text-slate-500">Propagating approach geometry…</div>}
      {profile && <div className="mt-6"><SeparationChart data={profile} /></div>}
    </div>
  );
}

function Badge({ level }: { level: string }) {
  const c = level === "HIGH" ? "bg-red-950 text-red-300 border-red-900"
    : level === "MEDIUM" ? "bg-amber-950 text-amber-300 border-amber-900"
    : "bg-slate-800 text-slate-300 border-slate-700";
  return <span className={`rounded border px-2 py-0.5 text-xs ${c}`}>{level}</span>;
}
