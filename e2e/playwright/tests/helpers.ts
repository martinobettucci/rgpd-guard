// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md#9.1 | docs/DESIGN_SYSTEM_APP.md#captures
// @verifies docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md#9.1 | docs/DESIGN_SYSTEM_APP.md#captures
// Gestes partagés du parcours canonique : arriver par l'accueil, se connecter au clavier, naviguer par la barre latérale.
import { expect, type Page, type TestInfo } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

export const TOKEN = process.env.RGPD_GUARD_TOKEN ?? "dev-token-rgpd-guard";
const OUTPUT = process.env.PW_OUTPUT ?? ".";

// Pleine page sur bureau ; fenêtre visible sur mobile et pour les modales, car les éléments fixes
// (barre de navigation inférieure, voile d'une modale) ne couvrent que la fenêtre et fausseraient l'image.
export async function capture(page: Page, name: string, testInfo: TestInfo, options: { viewport?: boolean } = {}): Promise<void> {
  const dir = join(OUTPUT, "captures");
  mkdirSync(dir, { recursive: true });
  const fullPage = !options.viewport && testInfo.project.name !== "mobile";
  await page.screenshot({ path: join(dir, `${testInfo.project.name}-${name}.jpg`), type: "jpeg", quality: 85, fullPage });
}

export async function login(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Tableau de bord RGPD Guard" })).toBeVisible();
  await expect(page.getByText("Moteur en ligne")).toBeVisible();
  await page.getByLabel("Jeton du moteur").fill(TOKEN);
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Journal" })).toBeVisible();
}

export async function navigate(page: Page, name: string): Promise<void> {
  await page.getByRole("navigation", { name: "Navigation principale" }).getByRole("link", { name }).click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
}
