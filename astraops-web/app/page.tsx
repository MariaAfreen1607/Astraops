"use client";
import { useEffect, useState } from "react";
import { api, SatelliteList, SpaceWeather, ConjunctionScreen } from "@/lib/api";
import OrbitGlobe from "@/components/OrbitGlobe";
import Explain from "@/components/Explain";

export default function Dashboard() {
  const [sats, setSats] = useState<SatelliteList | null>(null);
  const [sw, setSw] = useState<SpaceWeather | null>(null);
  const [conj, setConj] = useState<ConjunctionScreen | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<SatelliteList>("/satellites?group=stations").then(setSats).catch(e => setErr(e.message));
    api<SpaceWeather>("/spaceweather").then(setSw).catch(() => {});
    api<ConjunctionScreen>("/conjunctions?group=stations&threshold_km=50").then(setConj).catch(() => {});
  }, []);

  const flares = sw?.solar_flares?.filter(f => f.class_type) ?? [];
  const strongest = [...flares].sort((a, b) =>
    (b.class_type ?? "").localeCompare(a.class_type ?? ""))[0];
  const mClass = flares.filter(f => /^[MX]/.test(f.class_type ?? "")).length;

  return (
    <div>
      <h1 className="doc-title">Mission Dashboard</h1>

      <p className="mt-4 text-[13px] leading-relaxed" style={{ maxWidth: "76ch" }}>
        Space agencies publish orbital and solar data openly and continuously. Almost none of it is
        translated into a decision. AstraOps reads those feeds, runs the physics, and states what
        the numbers mean for a spacecraft.
      </p>

      {err && (
        <div className="sheet mt-6 p-4 text-[12.5px]" style={{ borderLeft: "3px solid var(--oxide)" }}>
          Backend unreachable — {err}. Start the API with{" "}
          <span className="mono">uvicorn main:app --port 8000</span>.
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card
          label="Objects tracked"
          value={sats ? String(sats.count) : "…"}
          unit="crewed stations & visiting vehicles"
          note="Orbital element sets pulled live from CelesTrak and propagated with SGP4." />
        <Card
          label="Close approaches"
          value={conj ? String(conj.events.length) : "…"}
          unit={conj ? `within ${conj.threshold_km} km, next 3 h` : "screening"}
          note={conj
            ? `${conj.total_pairs_screened.toLocaleString()} satellite pairs checked. Zero is the healthy result.`
            : "Propagating every pair forward in time."} />
        <Card
          label="Strongest flare"
          value={strongest?.class_type ?? (sw ? "quiet" : "…")}
          unit="past 7 days"
          note={strongest
            ? `${mClass} M-or-X class event${mClass === 1 ? "" : "s"} this week. Region ${strongest.active_region ?? "unnumbered"}.`
            : "No flares recorded by NASA DONKI in this window."} />
      </div>

      <section className="mt-9">
        <div className="eyebrow">Where everything is right now</div>
        <p className="mt-2 text-[12px]" style={{ color: "var(--ink-mid)", maxWidth: "76ch" }}>
          Each marker is a real object, positioned by propagating its current element set to this
          second. Altitude is compressed logarithmically so low orbit and geostationary orbit are
          both readable — at true scale, GEO would sit five Earth-radii off the screen.
        </p>
        <div className="mt-3">
          <OrbitGlobe group="stations" limit={400} />
        </div>
      </section>

      <section className="mt-10">
        <div className="eyebrow">Closest approaches in the next three hours</div>
        <div className="sheet mt-3 overflow-hidden">
          <table className="ops">
            <thead>
              <tr><th>Primary</th><th>Secondary</th><th>Miss</th><th>Relative velocity</th><th>Risk</th></tr>
            </thead>
            <tbody>
              {conj?.events.slice(0, 5).map((e, i) => (
                <tr key={i}>
                  <td>{e.sat1_name}</td>
                  <td>{e.sat2_name}</td>
                  <td className="num">{e.min_range_km.toFixed(2)} km</td>
                  <td className="num">{e.relative_velocity_km_s?.toFixed(2) ?? "—"} km/s</td>
                  <td><Risk level={e.risk_level} /></td>
                </tr>
              ))}
              {conj && conj.events.length === 0 && (
                <tr><td colSpan={5} className="text-[12px]">
                  Nothing within {conj.threshold_km} km. All {conj.total_pairs_screened.toLocaleString()} pairs
                  screened clear — open Conjunctions to screen a larger constellation.
                </td></tr>
              )}
              {!conj && <tr><td colSpan={5} className="text-[12px]">Propagating orbits…</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <Explain title="What the four pages do">
        <p><b>Dashboard</b> — current state at a glance: what is up there, what is getting close,
        and how active the Sun has been this week.</p>
        <p><b>Conjunctions</b> — screen any satellite group for close approaches. Results include the
        exact time of closest approach, miss distance, relative velocity, and a collision probability,
        with an AI brief that explains what the geometry actually means.</p>
        <p><b>Space weather</b> — live solar flare, CME and geomagnetic storm data from NASA, turned
        into an operational impact assessment per orbit band.</p>
        <p><b>Research</b> — ask a question and get an answer drawn from indexed space-operations
        papers, with the source passages shown.</p>
      </Explain>

      <Explain title="How it is built">
        <p>Three layers. Ingest pulls live data from CelesTrak and NASA DONKI. Compute runs the
        deterministic physics — SGP4 orbit propagation, pairwise conjunction screening, NOAA
        impact scales. Interpret hands the computed results to IBM Granite on watsonx.</p>
        <p>The language model never does arithmetic. Every number on this site comes from orbital
        mechanics or a published feed; the model only explains what those numbers mean.</p>
      </Explain>
    </div>
  );
}

function Card({ label, value, unit, note }: { label: string; value: string; unit: string; note: string }) {
  return (
    <div className="sheet p-5">
      <div className="eyebrow">{label}</div>
      <div className="metric mt-3">{value}</div>
      <div className="mt-1.5 text-[11px]" style={{ color: "var(--ink-dim)" }}>{unit}</div>
      <div className="mt-3 border-t pt-3 text-[11px] leading-relaxed"
           style={{ borderColor: "var(--rule)", color: "var(--ink-mid)" }}>{note}</div>
    </div>
  );
}

function Risk({ level }: { level: string }) {
  const c = level === "HIGH" ? "chip-high" : level === "MEDIUM" ? "chip-medium" : "chip-low";
  return <span className={`chip ${c}`}>{level}</span>;
}
