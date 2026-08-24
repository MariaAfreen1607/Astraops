"use client";
import { useEffect, useState } from "react";
import { api, SpaceWeather, Brief } from "@/lib/api";
import Explain from "@/components/Explain";
import { Sun } from "@/components/Sticker";
import ComputedPanel from "@/components/ComputedPanel";

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
      <div className="flex items-center gap-3">
        <Sun size={30} />
        <h1 className="doc-title">Space Weather Sentinel</h1>
      </div>
      <p className="mt-1 text-sm ">
        NOAA&apos;s G-scale was calibrated for power grids, not orbital drag. These briefs translate events into orbit-regime impact.
      </p>

      <button onClick={getBrief} disabled={briefing || !data}
        className="mt-6 rounded btn btn-primary disabled:opacity-50">
        {briefing ? "Granite is analysing…" : "Generate operational brief"}
      </button>

      {briefing && (
        <div className="sheet mt-6 p-5">
          <div className="eyebrow">Generating brief</div>
          <div className="mt-2 text-[12.5px]">Granite is reading the event data and drafting the brief. This usually takes 5–15 seconds.</div>
        </div>
      )}

      {err && <div className="mt-6 sheet p-4 text-sm">{err}</div>}

      {brief && (
        <div className="mt-6 brief-panel p-5">
          <div className="text-xs uppercase tracking-wide ">AI brief · {brief.model_used}</div>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed ">{brief.brief}</pre>
        </div>
      )}
      {brief?.computed && <ComputedPanel c={brief.computed} />}

      {data && (
        <div className="mt-9 grid grid-cols-1 gap-4 md:grid-cols-3">
          <ColNote t="Solar flares">
            Sudden X-ray brightenings, graded C, M then X — each letter is ten times stronger than
            the last. M and X class flares raise the risk of single-event upsets in spacecraft
            electronics and can black out HF radio on Earth&apos;s sunlit side.
          </ColNote>
          <ColNote t="Coronal mass ejections">
            Billion-tonne clouds of magnetised plasma thrown off the Sun. Speed matters most: a
            600 km/s CME reaches Earth in roughly three days, faster ones in under two, and the
            arrival is what heats and expands the upper atmosphere.
          </ColNote>
          <ColNote t="Geomagnetic storms">
            Disturbances in Earth&apos;s magnetic field, indexed by Kp from 0 to 9. Kp above 5 is a
            storm. Storms heat the thermosphere, which thickens the air satellites fly through and
            increases drag on everything in low orbit.
          </ColNote>
        </div>
      )}

      {data && (
        <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-3">
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
            {data.geomagnetic_storms.length === 0 && <div className="p-3 text-sm ">None in window.</div>}
          </Panel>
        </div>
      )}
      <Explain title="Why this page exists">
        <p>NASA publishes every one of these events openly, in real time. What nobody publishes is
        what they mean for a spacecraft.</p>
        <p>NOAA&apos;s storm scale was built around effects on the ground — power grids and radio.
        It was never calibrated for orbital drag. In February 2022 a storm rated G1, the mildest
        category, raised air density at 210 km enough to bring down 38 of 49 newly launched Starlink
        satellites. The number said &quot;minor&quot;; the outcome was a total loss.</p>
        <p>The brief above closes that gap. Granite reads the same events NASA publishes and states
        what they imply for each orbit band, which subsystems are exposed, and what an operator
        should do in the next 24 to 72 hours.</p>
      </Explain>
    </div>
  );
}

function ColNote({ t, children }: { t: string; children: React.ReactNode }) {
  return (
    <div className="sheet p-4">
      <div className="eyebrow">{t}</div>
      <div className="mt-2 text-[11.5px] leading-relaxed" style={{ color: "var(--ink-mid)" }}>{children}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="sheet">
      <div className=" px-4 py-3 text-xs uppercase tracking-wide ">{title}</div>
      <div className="max-h-96 overflow-y-auto ">{children}</div>
    </div>
  );
}
function Row({ main, sub }: { main: string; sub: string }) {
  return <div className="px-4 py-3"><div className="text-sm font-medium">{main}</div><div className="text-xs ">{sub}</div></div>;
}
