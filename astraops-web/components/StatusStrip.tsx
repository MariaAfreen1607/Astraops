"use client";
import { useEffect, useState } from "react";
import { api, SatelliteList } from "@/lib/api";

export default function StatusStrip() {
  const [utc, setUtc] = useState("--:--:--");
  const [fetched, setFetched] = useState<Date | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const tick = () => setUtc(new Date().toISOString().slice(11, 19));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const poll = () =>
      api<SatelliteList>("/satellites?group=stations")
        .then(d => { setFetched(new Date(d.fetched_at)); setOnline(true); })
        .catch(() => setOnline(false));
    poll();
    const t = setInterval(poll, 30000);
    return () => clearInterval(t);
  }, []);

  const ageMin = fetched ? Math.floor((Date.now() - fetched.getTime()) / 60000) : null;

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-b px-4 py-2 text-[11px] md:gap-x-7 md:px-6"
         style={{ borderColor: "var(--rule)", background: "var(--sheet)" }}>
      <div className="flex items-center gap-2">
        <span className="live-dot text-[9px]"
              style={{ color: online === false ? "var(--oxide)" : "var(--plot)" }}>●</span>
        <span className="eyebrow" style={{ color: online === false ? "var(--oxide)" : "var(--plot)" }}>
          {online === false ? "Feed offline" : "Feed live"}
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="eyebrow">UTC</span>
        <span className="mono" style={{ letterSpacing: "0.06em" }}>{utc}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="eyebrow">Element set age</span>
        <span className="mono" style={{ color: ageMin !== null && ageMin > 120 ? "var(--amber)" : "var(--ink-dim)" }}>
          {ageMin === null ? "—" : `${ageMin} min`}
        </span>
      </div>
      <div className="ml-auto hidden eyebrow sm:block" style={{ color: "var(--ink-dim)" }}>
        CelesTrak refreshes every 2 h
      </div>
    </div>
  );
}
