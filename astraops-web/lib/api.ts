const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export interface TLERecord {
  name: string; norad_cat_id: string; epoch: string;
  mean_motion: number | null; eccentricity: number | null;
  inclination_deg: number | null; altitude_km: number | null;
}
export interface SatelliteList { count: number; fetched_at: string; source: string; satellites: TLERecord[]; }

export interface ConjunctionEvent {
  sat1_norad: string; sat1_name: string; sat2_norad: string; sat2_name: string;
  tca: string; min_range_km: number; relative_velocity_km_s: number | null;
  probability_of_collision: number | null; risk_level: string;
}
export interface ConjunctionScreen {
  screened_at: string; total_pairs_screened: number; threshold_km: number; events: ConjunctionEvent[];
  objects_screened?: number; objects_available?: number; window_minutes?: number;
}

export interface SolarFlare { flare_id: string; peak_time: string | null; class_type: string | null; active_region: string | null; source_location: string | null; }
export interface CMEEvent { activity_id: string; start_time: string | null; speed_km_s: number | null; source_location: string | null; }
export interface GeomagneticStorm { gst_id: string; start_time: string | null; kp_index_max: number | null; }
export interface SpaceWeather {
  fetched_at: string; start_date: string; end_date: string;
  solar_flares: SolarFlare[]; cmes: CMEEvent[]; geomagnetic_storms: GeomagneticStorm[];
}

export interface Computed {
  kp: number;
  kp_basis: string;
  density_increase_pct: number;
  decay_72h_m: Record<string, number>;
  quiet_decay_72h_m: Record<string, number>;
  fastest_cme_km_s?: number;
  transit_hours?: number;
  arrival_utc?: string;
  hours_until_arrival?: number;
}

export interface Brief { generated_at: string; model_used: string; subject: string; brief: string; computed?: Computed | null; }

export interface ProfilePoint {
  t: string; minutes_from_now: number;
  separation_km: number; relative_velocity_km_s: number;
}
export interface SeparationProfile {
  sat1_norad: string; sat1_name: string;
  sat2_norad: string; sat2_name: string;
  window_minutes: number; step_seconds: number;
  tca: string; min_separation_km: number; points: ProfilePoint[];
}

export interface SatPosition {
  name: string; norad_cat_id: string;
  lat: number; lon: number; alt_km: number;
  inclination_deg: number | null;
}
export interface PositionSet {
  epoch: string; group: string; count: number; satellites: SatPosition[];
}

export interface ResearchSource { document_id: string; title: string; excerpt: string; score: number; }
export interface ResearchAnswer {
  question: string; answer: string; sources: ResearchSource[];
  model_used: string; answered_at: string;
}
