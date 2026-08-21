/**
 * Tests for app/research/page.tsx — Research Copilot
 *
 * Coverage:
 *   - All three example question chips are rendered.
 *   - Clicking a chip fires the POST request and displays the answer.
 *   - Retrieved source passages are rendered with title and similarity score.
 *   - Typing a question and clicking Ask fires the request.
 *   - Pressing Enter in the input fires the request.
 *   - An error message is shown when the API responds with an error.
 *
 * Note: the Research page uses raw fetch() with process.env.NEXT_PUBLIC_API_URL,
 * not the api() helper, so we stub fetch directly.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Research from "@/app/research/page";

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

const RESEARCH_ANSWER = {
  question: "Why did the February 2022 Starlink satellites re-enter?",
  answer:
    "A G1 geomagnetic storm raised atmospheric density at ~210 km by ~50%, increasing drag beyond the satellites' propulsion capacity.",
  sources: [
    {
      document_id: "doc-starlink-001",
      title: "Starlink Reentry Analysis 2022",
      excerpt: "Thermospheric density increased significantly during the storm.",
      score: 0.912,
    },
    {
      document_id: "doc-donki-002",
      title: "NASA DONKI Event Log",
      excerpt: "The CME arrival was recorded on 2022-02-03.",
      score: 0.847,
    },
  ],
  model_used: "ibm/granite-4-h-small",
  answered_at: "2024-01-01T06:00:00Z",
};

const EXAMPLE_QUESTIONS = [
  "Why did the February 2022 Starlink satellites re-enter?",
  "How does a geomagnetic storm change atmospheric density at 300 km?",
  "What mitigation measures reduce debris growth in low Earth orbit?",
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Stub global fetch to return a successful research answer. */
function stubFetchSuccess(body = RESEARCH_ANSWER) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
      }),
    ),
  );
}

/** Stub global fetch to return a non-ok response with a detail field. */
function stubFetchError(detail: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        json: () => Promise.resolve({ detail }),
      }),
    ),
  );
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  // research/page.tsx uses process.env.NEXT_PUBLIC_API_URL directly.
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Research — example chips", () => {
  it("renders all three example question chips", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Research />);
    for (const q of EXAMPLE_QUESTIONS) {
      expect(screen.getByRole("button", { name: q })).toBeInTheDocument();
    }
  });

  it("renders the page heading", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Research />);
    expect(screen.getByRole("heading", { name: /Research Copilot/i })).toBeInTheDocument();
  });

  it("renders the Ask button (disabled while input is empty)", () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<Research />);
    const askBtn = screen.getByRole("button", { name: /^Ask$/i });
    expect(askBtn).toBeInTheDocument();
    expect(askBtn).toBeDisabled();
  });
});

describe("Research — successful query via chip click", () => {
  it("posts the question when a chip is clicked", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(RESEARCH_ANSWER),
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    render(<Research />);

    await user.click(screen.getByRole("button", { name: EXAMPLE_QUESTIONS[0] }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledOnce();
    });

    const [url, options] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/research\/ask/);
    expect(options.method).toBe("POST");
    const body = JSON.parse(options.body as string);
    expect(body.question).toBe(EXAMPLE_QUESTIONS[0]);
    expect(body.top_k).toBe(5);
  });

  it("displays the answer text after a successful chip-click query", async () => {
    const user = userEvent.setup();
    stubFetchSuccess();
    render(<Research />);

    await user.click(screen.getByRole("button", { name: EXAMPLE_QUESTIONS[0] }));

    await waitFor(() => {
      expect(screen.getByText(/A G1 geomagnetic storm raised atmospheric density/i)).toBeInTheDocument();
    });
  });

  it("displays retrieved source passage titles", async () => {
    const user = userEvent.setup();
    stubFetchSuccess();
    render(<Research />);

    await user.click(screen.getByRole("button", { name: EXAMPLE_QUESTIONS[0] }));

    await waitFor(() => {
      expect(screen.getByText(/Starlink Reentry Analysis 2022/i)).toBeInTheDocument();
      expect(screen.getByText(/NASA DONKI Event Log/i)).toBeInTheDocument();
    });
  });

  it("displays similarity scores for each retrieved passage", async () => {
    const user = userEvent.setup();
    stubFetchSuccess();
    render(<Research />);

    await user.click(screen.getByRole("button", { name: EXAMPLE_QUESTIONS[0] }));

    await waitFor(() => {
      // Scores are formatted with .toFixed(3): "0.912" and "0.847".
      expect(screen.getByText(/similarity 0\.912/i)).toBeInTheDocument();
      expect(screen.getByText(/similarity 0\.847/i)).toBeInTheDocument();
    });
  });

  it("displays source passage excerpts", async () => {
    const user = userEvent.setup();
    stubFetchSuccess();
    render(<Research />);

    await user.click(screen.getByRole("button", { name: EXAMPLE_QUESTIONS[0] }));

    await waitFor(() => {
      expect(
        screen.getByText(/Thermospheric density increased significantly/i),
      ).toBeInTheDocument();
    });
  });

  it("labels the answer panel with the model name", async () => {
    const user = userEvent.setup();
    stubFetchSuccess();
    render(<Research />);

    await user.click(screen.getByRole("button", { name: EXAMPLE_QUESTIONS[0] }));

    await waitFor(() => {
      expect(screen.getByText(/ibm\/granite-4-h-small/i)).toBeInTheDocument();
    });
  });
});

describe("Research — successful query via text input", () => {
  it("submits when the user types a question and clicks Ask", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(RESEARCH_ANSWER),
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    render(<Research />);

    const input = screen.getByPlaceholderText(/Ask about orbital debris/i);
    await user.type(input, "What is orbital decay?");
    await user.click(screen.getByRole("button", { name: /^Ask$/i }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledOnce();
    });
    const body = JSON.parse((fetchSpy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.question).toBe("What is orbital decay?");
  });

  it("submits when the user presses Enter in the input field", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(RESEARCH_ANSWER),
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    render(<Research />);

    const input = screen.getByPlaceholderText(/Ask about orbital debris/i);
    await user.type(input, "What is orbital decay?{Enter}");

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledOnce();
    });
  });
});

describe("Research — error handling", () => {
  it("shows an error message when the API responds with an error", async () => {
    const user = userEvent.setup();
    stubFetchError("RAG pipeline is not configured");
    render(<Research />);

    await user.click(screen.getByRole("button", { name: EXAMPLE_QUESTIONS[0] }));

    await waitFor(() => {
      expect(screen.getByText(/RAG pipeline is not configured/i)).toBeInTheDocument();
    });
  });
});
