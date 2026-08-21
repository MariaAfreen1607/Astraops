import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // Inline CSS imports so component tests don't choke on them.
    css: false,
  },
  resolve: {
    alias: {
      // Mirror the @/* path alias from tsconfig.json.
      "@": import.meta.dirname,
    },
  },
});
