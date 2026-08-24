import { Computed } from "@/lib/api";

function band(alt: string) {
  return Number(alt) < 300 ? "VLEO" : "LEO";
}

function fmt(m: number) {
  return m >= 5000 ? `${(m / 1000).toFixed(0)} km` : `${m} m`;
}

export default function ComputedPanel({ c }: { c: Computed }) {
  const arrived = c.hours_until_arrival !== undefined && c.hours_until_arrival < 0;

  return (
    <div className="sheet mt-4 p-5">
      <div className="eyebrow">Computed · deterministic model, not generated</div>
      <p className="mt-2 text-[12.5px]">
        These figures come from a drag-decay calculation over the live NASA event feed.
        Granite reads them and writes the brief above; it does not produce the numbers.
      </p>

      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        {c.fastest_cme_km_s !== undefined && (
          <Stat label="Fastest CME" value={`${c.fastest_cme_km_s} km/s`} />
        )}
        {c.arrival_utc && (
          <Stat
            label={arrived ? "Arrived" : "Arrives"}
            value={
              arrived
                ? `${Math.abs(c.hours_until_arrival!)}h ago`
                : `in ${c.hours_until_arrival}h`
            }
            sub={c.arrival_utc}
          />
        )}
        <Stat label="Kp" value={String(c.kp)} sub={c.kp_basis} />
        <Stat label="Density increase" value={`+${c.density_increase_pct}%`} sub="thermosphere" />
      </div>

      <div className="mt-5">
        <div className="eyebrow">Altitude loss over 72 hours · 3U CubeSat</div>
        <table className="mt-2 w-full text-[12.5px]">
          <thead>
            <tr className="text-left opacity-60">
              <th className="py-1 font-normal">Altitude</th>
              <th className="py-1 font-normal">Band</th>
              <th className="py-1 font-normal">Quiet</th>
              <th className="py-1 font-normal">This event</th>
            </tr>
          </thead>
          <tbody>
            {Object.keys(c.decay_72h_m)
              .sort((a, b) => Number(a) - Number(b))
              .map((alt) => (
                <tr key={alt} className="border-t border-black/10">
                  <td className="py-1.5">{alt} km</td>
                  <td className="py-1.5">{band(alt)}</td>
                  <td className="py-1.5 opacity-60">{fmt(c.quiet_decay_72h_m[alt])}</td>
                  <td className="py-1.5 font-medium">{fmt(c.decay_72h_m[alt])}</td>
                </tr>
              ))}
          </tbody>
        </table>
        <p className="mt-3 text-[11.5px] opacity-60">
          Cd 2.2, A/m 0.01 m²/kg. Below 300 km the linear model understates the outcome —
          decay accelerates as altitude drops, so treat those figures as &quot;not sustainable&quot;
          rather than precise.
        </p>
      </div>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide opacity-60">{label}</div>
      <div className="mt-0.5 text-lg">{value}</div>
      {sub && <div className="text-[11px] opacity-60">{sub}</div>}
    </div>
  );
}
