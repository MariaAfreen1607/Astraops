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

  const posed = useRef(false);
  useEffect(() => {
    if (!data || posed.current || !globeEl.current) return;
    globeEl.current.controls().autoRotate = false;
    globeEl.current.pointOfView({ altitude: 2.6 });
    posed.current = true;
  }, [data]);

  if (err) return <div className="sheet p-4 text-sm">{err}</div>;

  return (
    <div className="sheet p-5">
      <div className="flex items-baseline justify-between">
        <div>
          <div className="text-xs uppercase tracking-wide ">Live orbital positions</div>
          <div className="mt-1 text-sm">
            {data ? `${data.count} objects · ${data.group}` : "propagating…"}
          </div>

        </div>
        {hover && (
          <div className="text-right text-xs">
            <div className="font-medium ">{hover.name}</div>
            <div >
              {hover.lat.toFixed(2)}°, {hover.lon.toFixed(2)}° · {hover.alt_km.toFixed(0)} km
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 text-center text-[12px]" style={{ color: "var(--ink-mid)" }}>
        Drag to rotate · Pinch or scroll to zoom
      </div>

      <div className="mt-3 flex justify-center">
        {data && (
          <Globe
            ref={globeEl}
            width={620}
            height={620}
            backgroundColor="rgba(0,0,0,0)"
            globeImageUrl="//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
            bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
            customLayerData={data.satellites}
            customThreeObject={(d: any) => {
              const color = d.alt_km < 500 ? 0xC0392B : d.alt_km < 1000 ? 0x1F4E79 : 0x1E7A46;
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
            atmosphereColor="#7FB2D9"
            atmosphereAltitude={0.13}
          />
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-[11px]"
           style={{ color: "var(--ink-dim)" }}>
        <span><span style={{ color: "#C0392B" }}>●</span>&nbsp; under 500 km</span>
        <span><span style={{ color: "#1F4E79" }}>●</span>&nbsp; 500–1000 km</span>
        <span><span style={{ color: "#1E7A46" }}>●</span>&nbsp; above 1000 km</span>
        <span className="ml-auto">log-compressed altitude · refreshes every 15 s</span>
      </div>
    </div>
  );
}
