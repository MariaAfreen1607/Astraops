"use client";
import { useEffect, useState } from "react";
import { api, SpaceWeather, Brief } from "@/lib/api";

export default function SpaceWeatherPage() {
  const [data, setData] = useState<SpaceWeather | null>(null);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [briefing, setBriefing] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<SpaceWeather>("/spaceweather").then(setData).catch(e => setErr(e.message));
  }, []);

  const getBrief = () => {
    setBriefing(true);
    api<Brief>("/briefs/spaceweather").then(setBrief)
      .catch(e => setErr(e.message)).finally(() => setBriefing(false));
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold">Space Weather Sentinel</h1>
      <p className="mt-1 text-sm text-slate-400">
        NOAA&apos;s G-scale was calibrated for power grids, not orbital drag. These briefs translate events into orbit-regime impact.
      </p>

      <button onClick={getBrief} disabled={briefing || !data}
        className="mt-6 rounded bg-slate-100 px-4 py-2 text-sm font-medium text-slate-900 disabled:opacity-50">
        {briefing ? "Granite is analysing…" : "Generate operational brief"}
      </button>

      {err && <div className="mt-6 rounded border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{err}</div>}

      {brief && (
        <div className="mt-6 rounded-lg border border-indigo-900 bg-indigo-950/30 p-5">
          <div className="text-xs uppercase tracking-wide text-indigo-400">AI brief · {brief.model_used}</div>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-200">{brief.brief}</pre>
        </div>
      )}

      {data && (
        <div className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Panel title={`Solar flares (${data.solar_flares.length})`}>
            {data.solar_flares.map(f => (
              <Row key={f.flare_id} main={f.class_type ?? "?"}
                   sub={`${f.peak_time?.slice(0,16).replace("T"," ") ?? "?"} · AR ${f.active_region ?? "?"}`} />
            ))}
          </Panel>
          <Panel title={`CMEs (${data.cmes.length})`}>
            {data.cmes.map(c => (
              <Row key={c.activity_id} main={c.speed_km_s ? `${c.speed_km_s} km/s` : "unknown speed"}
                   sub={c.start_time?.slice(0,16).replace("T"," ") ?? "?"} />
            ))}
          </Panel>
          <Panel title={`Geomagnetic storms (${data.geomagnetic_storms.length})`}>
            {data.geomagnetic_storms.map(s => (
              <Row key={s.gst_id} main={s.kp_index_max ? `Kp ${s.kp_index_max}` : "?"}
                   sub={s.start_time?.slice(0,16).replace("T"," ") ?? "?"} />
            ))}
            {data.geomagnetic_storms.length === 0 && <div className="p-3 text-sm text-slate-500">None in window.</div>}
          </Panel>
        </div>
      )}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40">
      <div className="border-b border-slate-800 px-4 py-3 text-xs uppercase tracking-wide text-slate-400">{title}</div>
      <div className="max-h-96 overflow-y-auto divide-y divide-slate-800">{children}</div>
    </div>
  );
}
function Row({ main, sub }: { main: string; sub: string }) {
  return <div className="px-4 py-3"><div className="text-sm font-medium">{main}</div><div className="text-xs text-slate-500">{sub}</div></div>;
}
