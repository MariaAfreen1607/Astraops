/**
 * Tests for lib/api.ts
 *
 * The `api` function is a thin fetch wrapper, so these tests focus on:
 *   1. Returning parsed JSON on a 2xx response.
 *   2. Throwing with the backend `detail` field when the response is not ok.
 *   3. Falling back to statusText when no JSON body is available.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { api } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockFetch(status: number, body: unknown, ok = status >= 200 && status < 300) {
  const bodyText = JSON.stringify(body);
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok,
      status,
      statusText: `HTTP ${status}`,
      json: vi.fn().mockResolvedValue(body),
      text: vi.fn().mockResolvedValue(bodyText),
    }),
  );
}

// ---------------------------------------------------------------------------
// Success path
// ---------------------------------------------------------------------------

describe("api() — success", () => {
  it("returns parsed JSON on a 200 response", async () => {
    mockFetch(200, { count: 42, satellites: [] });
    const result = await api<{ count: number }>("/satellites?group=stations");
    expect(result).toEqual({ count: 42, satellites: [] });
  });

  it("passes the path to fetch with the base URL prepended", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });
    vi.stubGlobal("fetch", fetchSpy);
    await api("/health");
    expect(fetchSpy).toHaveBeenCalledOnce();
    const calledUrl: string = fetchSpy.mock.calls[0][0];
    expect(calledUrl).toMatch(/\/health$/);
  });

  it("calls fetch with cache: no-store", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });
    vi.stubGlobal("fetch", fetchSpy);
    await api("/health");
    expect(fetchSpy.mock.calls[0][1]).toMatchObject({ cache: "no-store" });
  });
});

// ---------------------------------------------------------------------------
// Error path — detail field present in JSON body
// ---------------------------------------------------------------------------

describe("api() — error with detail field", () => {
  it("throws an Error whose message is the detail field", async () => {
    mockFetch(502, { detail: "CelesTrak upstream is unreachable" }, false);
    await expect(api("/satellites")).rejects.toThrow(
      "CelesTrak upstream is unreachable",
    );
  });

  it("throws for a 404 with a detail field", async () => {
    mockFetch(404, { detail: "Satellite not found" }, false);
    await expect(api("/satellites/00001")).rejects.toThrow("Satellite not found");
  });

  it("throws for a 500 with a detail field", async () => {
    mockFetch(500, { detail: "Internal server error" }, false);
    await expect(api("/conjunctions")).rejects.toThrow("Internal server error");
  });
});

// ---------------------------------------------------------------------------
// Error path — no parseable JSON body
// ---------------------------------------------------------------------------

describe("api() — error without JSON body", () => {
  it("falls back to statusText when the error response has no JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        json: vi.fn().mockRejectedValue(new SyntaxError("not json")),
      }),
    );
    await expect(api("/spaceweather")).rejects.toThrow("Service Unavailable");
  });
});
