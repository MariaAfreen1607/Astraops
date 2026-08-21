/**
 * Tests for app/page.tsx — Mission Dashboard
 *
 * Coverage:
 *   - Three metric cards render their labels on mount.
 *   - Card values update once API responses resolve.
 *   - Backend-unreachable banner appears when the API rejects.
 *   - No network calls are made outside the mocked fetch.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Dashboard from "@/app/page";

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

const SATELLITES_RESPONSE = {
  count: 7,
  fetched_at: "2024-01-01T00:00:00Z",
  source: "CelesTrak",
  satellites: [],
};

const SPACEWEATHER_RESPONSE = {
  fetched_at: "2024-01-01T00:00:00Z",
  start_date: "2023-12-25",
  end_date: "2024-01-01",
  solar_flares: [
    {
      flare_id: "f1",
      peak_time: "2024-01-01T06:00Z",
      class_type: "M2.3",
      active_region: "13500",
      source_location: "N10W05",
    },
  ],
  cmes: [],
  geomagnetic_storms: [],
};

const CONJUNCTIONS_RESPONSE = {
  screened_at: "2024-01-01T00:00:00Z",
  total_pairs_screened: 21,
  threshold_km: 500,
  events: [],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Stub global fetch; routes every URL to the correct fixture. */
function stubFetch(overrides: Record<string, unknown> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      const u = String(url);
      let body: unknown;

      if (u.includes("/satellites/positions")) {
        body = overrides["positions"] ?? { epoch: "", group: "stations", count: 0, satellites: [] };
      } else if (u.includes("/satellites")) {
        body = overrides["satellites"] ?? SATELLITES_RESPONSE;
      } else if (u.includes("/spaceweather")) {
        body = overrides["spaceweather"] ?? SPACEWEATHER_RESPONSE;
      } else if (u.includes("/conjunctions")) {
        body = overrides["conjunctions"] ?? CONJUNCTIONS_RESPONSE;
      } else {
        body = {};
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "OK",
        json: () => Promise.resolve(body),
      });
    }),
  );
}

/** Make every fetch return a non-ok response so the satellite error path fires. */
function stubFetchReject(errorMessage: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 502,
        statusText: errorMessage,
        json: () => Promise.reject(new SyntaxError("no json")),
      }),
    ),
  );
}

// ---------------------------------------------------------------------------
// Teardown — real timers, no leaking mocks
// ---------------------------------------------------------------------------

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Dashboard — metric cards", () => {
  it("renders all three card labels on initial mount", () => {
    stubFetch();
    render(<Dashboard />);
    expect(screen.getByText("Objects tracked")).toBeInTheDocument();
    expect(screen.getByText("Close approaches")).toBeInTheDocument();
    expect(screen.getByText("Strongest flare")).toBeInTheDocument();
  });

  it("shows loading placeholder '…' before API data arrives", () => {
    // Never resolve the fetch so we stay in the loading state.
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    render(<Dashboard />);
    const placeholders = screen.getAllByText("…");
    expect(placeholders.length).toBeGreaterThanOrEqual(3);
  });

  it("shows the satellite count from the API response", async () => {
    stubFetch();
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText("7")).toBeInTheDocument();
    });
  });

  it("shows 0 close approaches when the conjunction event list is empty", async () => {
    stubFetch();
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText("0")).toBeInTheDocument();
    });
  });

  it("shows the strongest flare class from the space weather response", async () => {
    stubFetch();
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText("M2.3")).toBeInTheDocument();
    });
  });

  it("shows 'quiet' for strongest flare when no flares are present", async () => {
    stubFetch({ spaceweather: { ...SPACEWEATHER_RESPONSE, solar_flares: [] } });
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText("quiet")).toBeInTheDocument();
    });
  });
});

describe("Dashboard — backend-unreachable banner", () => {
  it("shows the unreachable message when the satellites call rejects", async () => {
    stubFetchReject("connection refused");
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText(/Backend unreachable/)).toBeInTheDocument();
    });
  });

  it("includes the error detail in the unreachable banner", async () => {
    stubFetchReject("connection refused");
    render(<Dashboard />);
    await waitFor(() => {
      // getAllByText because OrbitGlobe may also render an error with the same text.
      expect(screen.getAllByText(/connection refused/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows the uvicorn hint command in the unreachable banner", async () => {
    stubFetchReject("ECONNREFUSED");
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText(/uvicorn main:app/)).toBeInTheDocument();
    });
  });
});
