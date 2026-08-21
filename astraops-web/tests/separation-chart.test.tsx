/**
 * Tests for components/SeparationChart.tsx
 *
 * Coverage:
 *   - Renders satellite names and minimum separation in the header.
 *   - Classifies mean relative velocity < 2 km/s as "co-planar drift".
 *   - Classifies mean relative velocity > 7 km/s as "crossing encounter".
 *   - Classifies mean relative velocity between 2 and 7 km/s as "intermediate geometry".
 *   - Displays the computed mean velocity in the header line.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SeparationChart from "@/components/SeparationChart";
import type { SeparationProfile } from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeProfile(overrides: Partial<SeparationProfile> = {}): SeparationProfile {
  return {
    sat1_norad: "25544",
    sat1_name: "ISS (ZARYA)",
    sat2_norad: "44235",
    sat2_name: "STARLINK-0001",
    window_minutes: 180,
    step_seconds: 10,
    tca: "2024-01-01T06:30:00Z",
    min_separation_km: 3.5,
    points: [],
    ...overrides,
  };
}

/** Build a points array where every point has the given constant velocity. */
function pointsWithVelocity(vel: number, count = 4) {
  return Array.from({ length: count }, (_, i) => ({
    t: `2024-01-01T0${i}:00:00Z`,
    minutes_from_now: i * 10,
    separation_km: 10 - i,
    relative_velocity_km_s: vel,
  }));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SeparationChart — header content", () => {
  it("renders the primary satellite name", () => {
    render(<SeparationChart data={makeProfile({ points: pointsWithVelocity(1.0) })} />);
    expect(screen.getByText(/ISS \(ZARYA\)/)).toBeInTheDocument();
  });

  it("renders the secondary satellite name", () => {
    render(<SeparationChart data={makeProfile({ points: pointsWithVelocity(1.0) })} />);
    expect(screen.getByText(/STARLINK-0001/)).toBeInTheDocument();
  });

  it("renders the minimum separation distance", () => {
    render(<SeparationChart data={makeProfile({ points: pointsWithVelocity(1.0), min_separation_km: 3.5 })} />);
    expect(screen.getByText(/closest 3\.5 km/)).toBeInTheDocument();
  });
});

describe("SeparationChart — velocity characterisation", () => {
  it("labels a sub-2 km/s encounter as co-planar drift", () => {
    render(
      <SeparationChart
        data={makeProfile({ points: pointsWithVelocity(1.0) })}
      />,
    );
    expect(screen.getByText(/co-planar drift/i)).toBeInTheDocument();
    expect(screen.getByText(/low energy, predictable geometry/i)).toBeInTheDocument();
  });

  it("labels a mean velocity of exactly 1.99 km/s as co-planar drift", () => {
    render(
      <SeparationChart
        data={makeProfile({ points: pointsWithVelocity(1.99) })}
      />,
    );
    expect(screen.getByText(/co-planar drift/i)).toBeInTheDocument();
  });

  it("labels a super-7 km/s encounter as a crossing encounter", () => {
    render(
      <SeparationChart
        data={makeProfile({ points: pointsWithVelocity(9.0) })}
      />,
    );
    expect(screen.getByText(/crossing encounter/i)).toBeInTheDocument();
    expect(screen.getByText(/high energy, sensitive to covariance error/i)).toBeInTheDocument();
  });

  it("labels a mean velocity of exactly 7.01 km/s as a crossing encounter", () => {
    render(
      <SeparationChart
        data={makeProfile({ points: pointsWithVelocity(7.01) })}
      />,
    );
    expect(screen.getByText(/crossing encounter/i)).toBeInTheDocument();
  });

  it("labels a 4 km/s encounter as intermediate geometry", () => {
    render(
      <SeparationChart
        data={makeProfile({ points: pointsWithVelocity(4.0) })}
      />,
    );
    expect(screen.getByText(/intermediate geometry/i)).toBeInTheDocument();
  });

  it("displays the mean relative velocity value in the header", () => {
    // All points have velocity 1.5 km/s so mean = 1.50.
    render(
      <SeparationChart
        data={makeProfile({ points: pointsWithVelocity(1.5) })}
      />,
    );
    expect(screen.getByText(/Mean relative velocity 1\.50 km\/s/)).toBeInTheDocument();
  });

  it("handles an empty points array without crashing", () => {
    // avgVel = NaN when points is empty; character should still be a string.
    render(<SeparationChart data={makeProfile({ points: [] })} />);
    // Just assert it renders without throwing.
    expect(screen.getByText(/Approach geometry/i)).toBeInTheDocument();
  });
});
