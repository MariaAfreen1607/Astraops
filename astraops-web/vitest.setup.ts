import "@testing-library/jest-dom";
import { vi } from "vitest";

// ---------------------------------------------------------------------------
// ResizeObserver — not available in jsdom; needed by Recharts ResponsiveContainer.
// ---------------------------------------------------------------------------
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// ---------------------------------------------------------------------------
// next/navigation — usePathname and other hooks are unavailable outside the
// Next.js runtime.  Mock the whole module with stable return values.
// ---------------------------------------------------------------------------
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// ---------------------------------------------------------------------------
// next/link — render as a plain <a> so tests can assert on href.
// No JSX here; vitest.setup.ts is a .ts file so we use React.createElement.
// ---------------------------------------------------------------------------
vi.mock("next/link", async () => {
  const { createElement } = await import("react");
  return {
    default: ({ href, children, ...rest }: any) =>
      createElement("a", { href, ...rest }, children),
  };
});

// ---------------------------------------------------------------------------
// next/dynamic — return the module's default export synchronously so
// dynamically-imported components (OrbitGlobe → react-globe.gl) render in tests.
// ---------------------------------------------------------------------------
vi.mock("next/dynamic", () => ({
  default: (loader: () => Promise<any>) => {
    // Return a component that renders nothing during test; the important thing
    // is that the *parent* component (OrbitGlobe) can mount without errors.
    const MockDynamic = () => null;
    MockDynamic.displayName = "MockDynamic";
    return MockDynamic;
  },
}));

// ---------------------------------------------------------------------------
// react-globe.gl — requires WebGL which jsdom cannot provide.
// The module-level mock in __mocks__/react-globe.gl.tsx handles this, but
// explicit factory mock here as belt-and-braces for the dynamic() path.
// ---------------------------------------------------------------------------
vi.mock("react-globe.gl", () => ({
  default: () => null,
}));

// ---------------------------------------------------------------------------
// three — OrbitGlobe imports THREE; provide a minimal stub so the module
// resolves without attempting to set up a WebGL context.
// ---------------------------------------------------------------------------
vi.mock("three", () => ({
  Mesh: class {},
  SphereGeometry: class {},
  MeshBasicMaterial: class {},
}));
