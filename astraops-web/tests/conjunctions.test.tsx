/**
 * Tests for app/conjunctions/page.tsx — Conjunction Watch
 *
 * Coverage:
 *   - Page renders its controls (group selector, threshold input, run button) on mount.
 *   - No screening call is made automatically on mount.
 *   - "Ready to screen" idle panel is visible before the first run.
 *   - After a successful screening, the results table headers are rendered.
 *   - Event rows appear for each conjunction event returned.
 *   - "AI risk brief" button only appears after a successful run with events.
 *   - Error text is shown when the screening call rejects.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Conjunctions from "@/app/conjunctions/page";

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

const CONJUNCTION_EVENT = {
  sat1_norad: "25544",
  sat1_name: "ISS (ZARYA)",
  sat2_norad: "44235",
  sat2_name: "STARLINK-0001",
  tca: "2024-01-01T06:30:00Z",
  min_range_km: 4.567,
  relative_velocity_km_s: 0.82,
  probability_of_collision: 1.23e-5,
  risk_level: "MEDIUM",
};

const SCREEN_RESPONSE_WITH_EVENTS = {
  screened_at: "2024-01-01T00:00:00Z",
  total_pairs_screened: 6,
  threshold_km: 500,
  events: [CONJUNCTION_EVENT],
};

const SCREEN_RESPONSE_EMPTY = {
  screened_at: "2024-01-01T00:00:00Z",
  total_pairs_screened: 6,
  threshold_km: 500,
  events: [],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function stubFetch(conjBody: unknown = SCREEN_RESPONSE_WITH_EVENTS) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      const u = String(url);
      let body: unknown;
      if (u.includes("/conjunctions/profile")) {
        body = {
          sat1_name: "A", sat2_name: "B", sat1_norad: "1", sat2_norad: "2",
          window_minutes: 180, step_seconds: 10, tca: "", min_separation_km: 5,
          points: [],
        };
      } else if (u.includes("/conjunctions")) {
        body = conjBody;
      } else {
        body = {};
      }
      return Promise.resolve({
        ok: true, status: 200, statusText: "OK",
        json: () => Promise.resolve(body),
      });
    }),
  );
}

function stubFetchError(detail: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: false, status: 500, statusText: "Error",
        json: () => Promise.resolve({ detail }),
      }),
    ),
  );
}

// ---------------------------------------------------------------------------
// Teardown
// ---------------------------------------------------------------------------

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Conjunctions — initial render", () => {
  it("renders the page heading", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Conjunctions />);
    expect(screen.getByRole("heading", { name: /Conjunction Watch/i })).toBeInTheDocument();
  });

  it("renders the CelesTrak group selector", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Conjunctions />);
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("renders the threshold input with default value 500", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Conjunctions />);
    const input = screen.getByRole("spinbutton");
    expect(input).toBeInTheDocument();
    expect((input as HTMLInputElement).value).toBe("500");
  });

  it("renders the Run screening button", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Conjunctions />);
    expect(screen.getByRole("button", { name: /Run screening/i })).toBeInTheDocument();
  });

  it("does NOT call fetch on mount (no auto-run)", () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    vi.stubGlobal("fetch", fetchSpy);
    render(<Conjunctions />);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows the 'Ready to screen' idle panel before any run", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Conjunctions />);
    expect(screen.getByText(/Ready to screen/i)).toBeInTheDocument();
  });

  it("does NOT render the results table before any run", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Conjunctions />);
    expect(screen.queryByRole("columnheader", { name: /Primary/i })).not.toBeInTheDocument();
  });
});

describe("Conjunctions — after a successful screening run", () => {
  it("shows the results table with correct column headers", async () => {
    const user = userEvent.setup();
    stubFetch(SCREEN_RESPONSE_WITH_EVENTS);
    render(<Conjunctions />);

    await user.click(screen.getByRole("button", { name: /Run screening/i }));

    await waitFor(() => {
      expect(screen.getByRole("columnheader", { name: /Primary/i })).toBeInTheDocument();
    });
    expect(screen.getByRole("columnheader", { name: /Secondary/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /TCA/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Miss/i })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Rel. vel/i })).toBeInTheDocument();
  });

  it("renders a row for each conjunction event", async () => {
    const user = userEvent.setup();
    stubFetch(SCREEN_RESPONSE_WITH_EVENTS);
    render(<Conjunctions />);

    await user.click(screen.getByRole("button", { name: /Run screening/i }));

    await waitFor(() => {
      expect(screen.getByText("ISS (ZARYA)")).toBeInTheDocument();
    });
    expect(screen.getByText("STARLINK-0001")).toBeInTheDocument();
  });

  it("shows the miss distance in the event row", async () => {
    const user = userEvent.setup();
    stubFetch(SCREEN_RESPONSE_WITH_EVENTS);
    render(<Conjunctions />);

    await user.click(screen.getByRole("button", { name: /Run screening/i }));

    await waitFor(() => {
      expect(screen.getByText("4.567")).toBeInTheDocument();
    });
  });

  it("shows the risk level badge for each event", async () => {
    const user = userEvent.setup();
    stubFetch(SCREEN_RESPONSE_WITH_EVENTS);
    render(<Conjunctions />);

    await user.click(screen.getByRole("button", { name: /Run screening/i }));

    await waitFor(() => {
      expect(screen.getByText("MEDIUM")).toBeInTheDocument();
    });
  });

  it("shows the 'AI risk brief' button only when events are present", async () => {
    const user = userEvent.setup();
    stubFetch(SCREEN_RESPONSE_WITH_EVENTS);
    render(<Conjunctions />);

    // Must not exist before running.
    expect(screen.queryByRole("button", { name: /AI risk brief/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Run screening/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /AI risk brief/i })).toBeInTheDocument();
    });
  });

  it("does NOT show the 'AI risk brief' button when there are no events", async () => {
    const user = userEvent.setup();
    stubFetch(SCREEN_RESPONSE_EMPTY);
    render(<Conjunctions />);

    await user.click(screen.getByRole("button", { name: /Run screening/i }));

    await waitFor(() => {
      expect(screen.getByText(/No approaches below threshold/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /AI risk brief/i })).not.toBeInTheDocument();
  });
});

describe("Conjunctions — error handling", () => {
  it("shows an error message when the screening call fails", async () => {
    const user = userEvent.setup();
    stubFetchError("SGP4 propagation failed");
    render(<Conjunctions />);

    await user.click(screen.getByRole("button", { name: /Run screening/i }));

    await waitFor(() => {
      expect(screen.getByText(/SGP4 propagation failed/i)).toBeInTheDocument();
    });
  });
});
