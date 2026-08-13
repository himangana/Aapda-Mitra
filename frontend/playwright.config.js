import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: process.env.E2E_BASE_URL || "https://frontend-phi-seven-12.vercel.app",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
