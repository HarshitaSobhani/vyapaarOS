import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  oxc: { jsx: { runtime: "automatic" } },
  resolve: { alias: { "@": path.resolve(import.meta.dirname) } },
  test: { environment: "jsdom", setupFiles: ["./tests/setup.ts"], globals: true, css: false },
});
