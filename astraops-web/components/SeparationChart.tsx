"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from "recharts";
import { SeparationProfile } from "@/lib/api";

export default function SeparationChart({ data }: { data: SeparationProfile }) {
  const tcaMinutes = data.points.find(p => p.separation_km === data.min_separation_km)?.minutes_from_now ?? 0;
  const avgVel = data.points.reduce((s, p) => s + p.relative_velocity_km_s, 0) / data.points.length;
  const character = avgVel < 2 ? "co-planar drift — low energy, predictable geometry"
    : avgVel > 7 ? "crossing encounter — high energy, sensitive to covariance error"
    : "intermediate geometry";

  return (
    <div className="sheet p-5">
      <div className="text-xs uppercase tracking-wide ">Approach geometry</div>
      <div className="mt-1 text-sm">
        {data.sat1_name} / {data.sat2_name} — closest {data.min_separation_km} km
      </div>
      <div className="mt-1 text-xs ">
        Mean relative velocity {avgVel.toFixed(2)} km/s · {character}
      </div>

      <div className="mt-5 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.points} margin={{ top: 5, right: 20, bottom: 25, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="minutes_from_now" stroke="#64748b" fontSize={11}
              label={{ value: "minutes from now", position: "insideBottom", offset: -15, fill: "#64748b", fontSize: 11 }} />
            <YAxis stroke="#64748b" fontSize={11}
              label={{ value: "separation (km)", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 6, fontSize: 12 }}
              labelFormatter={(v) => `t + ${v} min`}
              formatter={(v: number) => [`${v} km`, "separation"]} />
            <ReferenceLine x={tcaMinutes} stroke="#f59e0b" strokeDasharray="4 4"
              label={{ value: "TCA", fill: "#f59e0b", fontSize: 11, position: "top" }} />
            <Line type="monotone" dataKey="separation_km" stroke="#818cf8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
