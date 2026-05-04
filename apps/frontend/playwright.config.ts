import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const appDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"]],
  use: {
    // Dedicated port so we never attach to an unrelated Vite on 5173 (reuseExistingServer + local dev).
    baseURL: "http://localhost:5174",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "Mobile Chrome",
      use: {
        // Pixel 5 profile uses Chromium (iPhone 12 uses WebKit and needs extra browser install).
        ...devices["Pixel 5"],
      },
    },
  ],
  webServer: {
    // Avoid pnpm.cmd subprocess quirks on Windows; invoke Vite directly.
    command:
      "node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5174 --strictPort",
    cwd: appDir,
    url: "http://localhost:5174",
    timeout: 120_000,
    reuseExistingServer: false,
    env: {
      ...process.env,
      VITE_API_BASE_URL: process.env.VITE_API_BASE_URL ?? "http://localhost:18080",
    },
  },
});
