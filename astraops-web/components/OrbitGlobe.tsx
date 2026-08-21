"use client";
import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import * as THREE from "three";
import { api, PositionSet, SatPosition } from "@/lib/api";

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });
const EARTH_RADIUS_KM = 6371;

export default function OrbitGlobe({ group = "starlink", limit = 400 }: { group?: string; limit?: number }) {
  const [data, setData] = useState<PositionSet | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [hover, setHover] = useState<SatPosition | null>(null);
  const globeEl = useRef<any>(null);

  const load = () => {
    api<PositionSet>(`/satellites/positions?group=${group}&limit=${limit}`)
      .then(setData).catch(e => setErr(e.message));
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 15000); // refresh positions every 15 s
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [group, limit]);

  useEffect(() => {
    if (globeEl.current) {
      globeEl.current.controls().autoRotate = true;
      globeEl.current.controls().autoRotateSpeed = 0.4;
      globeEl.current.pointOfView({ altitude: 2.6 });
    }
  }, [data]);

  if (err) return <div className="rounded border border-red-900 bg-red-950/50 p-4 text-sm text-red-300">{err}</div>;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-5">
      <div className="flex items-baseline justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-400">Live orbital positions</div>
          <div className="mt-1 text-sm">
            {data ? `${data.count} objects · ${data.group}` : "propagating…"}
          </div>
        </div>
        {hover && (
          <div className="text-right text-xs">
            <div className="font-medium text-slate-200">{hover.name}</div>
            <div className="text-slate-500">
              {hover.lat.toFixed(2)}°, {hover.lon.toFixed(2)}° · {hover.alt_km.toFixed(0)} km
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 flex justify-center">
        {data && (
          <Globe
            ref={globeEl}
            width={620}
            height={620}
            backgroundColor="rgba(0,0,0,0)"
            globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
            customLayerData={data.satellites}
            customThreeObject={(d: any) => {
              const color = d.alt_km < 500 ? 0xf87171 : d.alt_km < 1000 ? 0x818cf8 : 0x4ade80;
              return new THREE.Mesh(
                new THREE.SphereGeometry(1.1, 6, 6),
                new THREE.MeshBasicMaterial({ color })
              );
            }}
            customThreeObjectUpdate={(obj: any, d: any) => {
              // Compress the altitude scale logarithmically so LEO and GEO
              // are both legible on one globe (true scale puts GEO 5.6 radii out).
              const alt = Math.log10(1 + d.alt_km / 200) * 0.06;
              Object.assign(obj.position, globeEl.current?.getCoords(d.lat, d.lon, alt) ?? {});
            }}
            atmosphereColor="#60a5fa"
            atmosphereAltitude={0.16}
          />
        )}
      </div>

      <div className="mt-3 flex gap-4 text-xs text-slate-500">
        <span><span className="text-red-400">●</span> under 500 km</span>
        <span><span className="text-indigo-400">●</span> 500–1000 km</span>
        <span><span className="text-green-400">●</span> above 1000 km</span>
        <span className="ml-auto">log-compressed altitude · refreshes every 15 s</span>
      </div>
    </div>
  );
}
