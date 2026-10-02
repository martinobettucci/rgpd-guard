// @spec docs/BACKLOG.md#RG-013 | docs/BACKLOG.md#RG-014 | docs/BACKLOG.md#RG-015 | docs/BACKLOG.md#RG-016 | docs/DESIGN_SYSTEM.md#13.2 | docs/DESIGN_SYSTEM_APP.md#captures
// Parcours canonique du tableau de bord : captures JPEG et vidéos webm conservées comme preuves visuelles.
import { defineConfig, devices } from "@playwright/test";

const executablePath = process.env.PW_CHROMIUM_PATH || undefined;

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 30_000 },
  reporter: [["list"]],
  outputDir: "./test-results",
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:8743",
    locale: "fr-FR",
    video: "on",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    launchOptions: executablePath ? { executablePath } : {},
  },
  projects: [
    { name: "bureau", use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 900 } }, grepInvert: /@mobile/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, grep: /@mobile/ },
  ],
});
