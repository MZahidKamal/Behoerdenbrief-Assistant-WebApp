import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Lets tests use the "@/..." import alias from tsconfig.json.
    tsconfigPaths: true,
  },
  test: {
    environment: "jsdom",
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    setupFiles: ["tests/unit/setup.ts"],
    coverage: {
      provider: "v8",
      include: [
        "app/**/*.{ts,tsx}",
        "features/**/*.{ts,tsx}",
        "components/**/*.{ts,tsx}",
        "lib/**/*.{ts,tsx}",
      ],
      // Generated files are not measured (RULES §10.1).
      exclude: ["**/*.d.ts", "lib/api/openapi.json"],
      thresholds: {
        lines: 70,
      },
    },
  },
});
