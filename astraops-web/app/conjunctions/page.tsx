"use client";
import { useEffect, useState } from "react";
import { api, ConjunctionScreen, Brief, SeparationProfile } from "@/lib/api";
import SeparationChart from "@/components/SeparationChart";
import Explain from "@/components/Explain";

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
      <h1 className="doc-title">Conjunction Watch</h1>
      <p className="mt-1 text-sm ">
        SGP4 propagation over a 3-hour window, refined to 1-second resolution near closest approach.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-3">
        <label className="text-xs ">
          <div className="mb-1">CelesTrak group</div>
          <select value={group} onChange={e => setGroup(e.target.value)}
            className="field ">
            <option value="starlink">starlink</option>
            <option value="stations">stations</option>
            <option value="oneweb">oneweb</option>
            <option value="iridium-NEXT">iridium-NEXT</option>
            <option value="active">active</option>
          </select>
        </label>
        <label className="text-xs ">
          <div className="mb-1">Threshold (km)</div>
          <input type="number" value={threshold} onChange={e => setThreshold(Number(e.target.value))}
            className="w-28 field" />
        </label>
        <button onClick={run} disabled={loading}
          className="rounded btn btn-primary disabled:opacity-50">
          {loading ? "Screening…" : "Run screening"}
        </button>
        {data && data.events.length > 0 && (
          <button onClick={getBrief} disabled={briefing}
            className="btn disabled:opacity-50">
            {briefing ? "Granite is analysing…" : "AI risk brief"}
          </button>
        )}
      </div>

      {err && <div className="mt-6 sheet p-4 text-sm">{err}</div>}

      {brief && (
        <div className="mt-6 brief-panel p-5">
          <div className="text-xs uppercase tracking-wide ">
            AI brief · {brief.model_used}
          </div>
          <div className="mt-1 text-sm font-medium">{brief.subject}</div>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed ">{brief.brief}</pre>
        </div>
      )}

      {data && (
        <>
          <div className="mt-8 text-xs ">
            {data.total_pairs_screened.toLocaleString()} pairs screened · {data.events.length} below {data.threshold_km} km
          </div>
          <div className="mt-3 sheet overflow-hidden">
            <table className="ops">
              <thead className="text-left">
                <tr><th className="p-3">Primary</th><th className="p-3">Secondary</th><th className="p-3">TCA (UTC)</th>
                    <th className="p-3">Miss (km)</th><th className="p-3">Rel. vel (km/s)</th>
                    <th className="p-3">Pc</th><th className="p-3">Risk</th></tr>
              </thead>
              <tbody>
                {data.events.map((e, i) => (
                  <tr key={i} onClick={() => loadProfile(e.sat1_norad, e.sat2_norad)}
                      className="cursor-pointer ">
                    <td className="p-3">{e.sat1_name}<div className="text-xs ">{e.sat1_norad}</div></td>
                    <td className="p-3">{e.sat2_name}<div className="text-xs ">{e.sat2_norad}</div></td>
                    <td className="p-3 font-mono text-xs">{new Date(e.tca).toISOString().replace("T"," ").slice(0,19)}</td>
                    <td className="p-3 font-mono">{e.min_range_km.toFixed(3)}</td>
                    <td className="p-3 font-mono">{e.relative_velocity_km_s?.toFixed(3) ?? "—"}</td>
                    <td className="p-3 font-mono text-xs">{e.probability_of_collision?.toExponential(2) ?? "—"}</td>
                    <td className="p-3"><Badge level={e.risk_level} /></td>
                  </tr>
                ))}
                {data.events.length === 0 && (
                  <tr><td colSpan={7} className="p-4 ">No approaches below threshold in this window.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs ">
            Click any row to plot its approach geometry.{" "}
            Pc assumes isotropic 200 m covariance and 20 m combined hard-body radius — screening defaults, not operator covariances.
          </p>
        </>
      )}

      {profiling && <div className="mt-6 text-sm ">Propagating approach geometry…</div>}
      {profile && <div className="mt-6"><SeparationChart data={profile} /></div>}
      <Explain title="How screening works">
        <p>Every satellite is propagated forward from its element set using SGP4, the standard
        orbital model, across a three-hour window sampled every thirty seconds.</p>
        <p>At each step the distance between all pairs is computed, and the running minimum is kept.
        Any pair that comes within the threshold is then re-propagated at one-second resolution
        around that minimum to pin down the exact time and distance of closest approach.</p>
        <p>Relative velocity is as important as miss distance. Two satellites drifting past each
        other at under 2 km/s are near-co-planar — predictable geometry, low energy. A crossing
        encounter above 7 km/s carries far more kinetic energy and leaves much less margin if the
        position estimate is off.</p>
        <p>Click any result row to plot how the separation evolves over the window.</p>
      </Explain>
    </div>
  );
}

function Badge({ level }: { level: string }) {
  const c = level === "HIGH" ? "bg-red-950  border-red-900"
    : level === "MEDIUM" ? "chip chip-medium"
    : "bg-slate-800  border-slate-700";
  return <span className={`chip ${c}`}>{level}</span>;
}
