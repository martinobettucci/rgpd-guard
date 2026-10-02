// @spec docs/BACKLOG.md#RG-013 | docs/BACKLOG.md#RG-014 | docs/BACKLOG.md#RG-015 | docs/BACKLOG.md#RG-016 | docs/DESIGN_SYSTEM_APP.md
// @verifies docs/BACKLOG.md#RG-012 | docs/BACKLOG.md#RG-013 | docs/BACKLOG.md#RG-014 | docs/BACKLOG.md#RG-015 | docs/BACKLOG.md#RG-016 | docs/BACKLOG.md#RG-017
// Parcours canonique : accueil, connexion au clavier, puis uniquement des clics dans l'interface.
import { expect, test } from "@playwright/test";
import { capture, login, navigate, TOKEN } from "./helpers";

test.describe.configure({ mode: "serial" });

test("accueil : état du moteur, refus d'un jeton faux, connexion", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByText("Moteur en ligne")).toBeVisible();
  await capture(page, "01-accueil", testInfo);
  await page.getByLabel("Jeton du moteur").fill("jeton-faux");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("alert")).toContainText("Jeton incorrect.");
  await capture(page, "02-accueil-refus", testInfo);
  await page.getByLabel("Jeton du moteur").fill(TOKEN);
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Journal" })).toBeVisible();
});

test("journal : synthèse seedée, filtre par décision, pagination", async ({ page }, testInfo) => {
  await login(page);
  const stats = page.getByRole("region", { name: "Synthèse" });
  await expect(stats.getByText("Événements")).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
  await capture(page, "03-journal", testInfo);
  await page.getByLabel("Décision").selectOption({ label: "Bloqué" });
  const rows = page.getByRole("table").locator("tbody tr");
  await expect(rows.first()).toContainText("Bloqué");
  const decisions = await rows.locator("td:nth-child(4)").allInnerTexts();
  expect(decisions.every((text) => text.includes("Bloqué"))).toBe(true);
  await capture(page, "04-journal-filtre-bloque", testInfo);
  await page.getByLabel("Décision").selectOption({ label: "Fuite arrêtée" });
  await expect(rows.first()).toContainText("Fuite arrêtée");
  await page.getByLabel("Décision").selectOption({ label: "Tous" });
  await expect(page.getByText(/Page 1 sur \d+/)).toBeVisible();
});

test("bac à sable : texte annoté, version pseudonymisée, catégories", async ({ page }, testInfo) => {
  await login(page);
  await navigate(page, "Bac à sable");
  const text =
    "Paul Durand (paul.durand@courriel-fictif.fr, 06 39 98 12 34) a été hospitalisé pour une dépression sévère " +
    "et suit un traitement par antidépresseurs. Merci de lui verser son indemnité sur FR76 3000 6000 0112 3456 7890 189.";
  await page.getByLabel("Texte à analyser").fill(text);
  await page.getByLabel("Profil").selectOption({ label: "Équilibré" });
  await page.getByRole("button", { name: "Analyser" }).click();
  const result = page.getByRole("region", { name: "Résultat" });
  await expect(result.getByText("Bloqué").first()).toBeVisible();
  await expect(result.locator("mark", { hasText: "[nom de personne]" })).toBeVisible();
  await expect(result.locator("pre.pseudonymized")).toContainText("⟦EMAIL_");
  await expect(result.locator("pre.pseudonymized")).not.toContainText("paul.durand@");
  await expect(result.getByText("santé")).toBeVisible();
  await capture(page, "05-bac-a-sable", testInfo);
});

test("politiques : modale par section, effet dans le bac à sable, refus serveur, rétablissement", async ({ page }, testInfo) => {
  await login(page);
  await navigate(page, "Politiques");
  await capture(page, "06-politiques", testInfo);

  await page.getByRole("button", { name: "Modifier : Types de données" }).click();
  const dialog = page.getByRole("dialog", { name: "Types de données" });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("Sur un prompt : IBAN").selectOption({ label: "Avertir" });
  await capture(page, "07-politiques-modale", testInfo, { viewport: true });
  await dialog.getByRole("button", { name: "Enregistrer" }).click();
  await expect(page.getByRole("status")).toContainText("Enregistré.");
  await expect(page.getByText("Politique personnalisée")).toBeVisible();

  await navigate(page, "Bac à sable");
  await page.getByLabel("Texte à analyser").fill("Virement sur FR76 3000 6000 0112 3456 7890 189.");
  await page.getByLabel("Profil").selectOption({ label: "Rapide" });
  await page.getByRole("button", { name: "Analyser" }).click();
  await expect(page.getByRole("region", { name: "Résultat" }).getByText("Avertissement").first()).toBeVisible();

  await navigate(page, "Politiques");
  await page.getByRole("button", { name: "Modifier : Liste blanche" }).click();
  const allowlist = page.getByRole("dialog", { name: "Liste blanche" });
  await allowlist.getByLabel("Expressions régulières").fill("(non fermée");
  await allowlist.getByRole("button", { name: "Enregistrer" }).click();
  await expect(allowlist.getByRole("alert")).toContainText("Politique refusée par le moteur.");
  await expect(allowlist.getByRole("alert")).toContainText("expression régulière invalide « (non fermée » (erreur à la position 0)");
  await capture(page, "08-politiques-refus", testInfo, { viewport: true });
  await allowlist.getByRole("button", { name: "Annuler" }).click();

  await page.getByRole("button", { name: "Rétablir la politique par défaut" }).click();
  await expect(page.getByText("La politique personnalisée sera remplacée")).toBeVisible();
  await page.getByRole("button", { name: "Rétablir", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Politique par défaut rétablie.");
  await expect(page.getByText("Politique par défaut", { exact: true })).toBeVisible();
});

test("moteurs : composants prêts et profils", async ({ page }, testInfo) => {
  await login(page);
  await navigate(page, "Moteurs");
  const components = page.getByRole("region", { name: "Composants" });
  for (const name of ["rules", "secrets", "spacy", "laya", "gliner"]) {
    await expect(components.getByText(name, { exact: true })).toBeVisible();
  }
  await expect(components.getByText("Indisponible")).toHaveCount(0);
  const profiles = page.getByRole("region", { name: "Profils" });
  await expect(profiles.getByText("Catégories sensibles : laya sur les prompts", { exact: true })).toBeVisible();
  await expect(profiles.getByText("Catégories sensibles : laya sur les prompts et les sorties d'outils")).toBeVisible();
  const bench = page.getByRole("region", { name: "Banc d'évaluation" });
  await expect(bench.getByLabel("Détail du profil")).toHaveValue("equilibre");
  await bench.getByLabel("Détail du profil").selectOption({ label: "Rapide" });
  await expect(bench.getByRole("heading", { name: "Par catégorie sensible" })).toHaveCount(0);
  await bench.getByLabel("Détail du profil").selectOption({ label: "Maximal" });
  await expect(bench.getByRole("cell", { name: "nom de personne", exact: true })).toBeVisible();
  await expect(bench.getByRole("cell", { name: "santé", exact: true })).toBeVisible();
  await capture(page, "09-moteurs", testInfo);
});

test("déconnexion : retour à l'accueil, destinations refusées sans session", async ({ page }, testInfo) => {
  await login(page);
  await page.getByRole("button", { name: "Se déconnecter" }).click();
  await expect(page.getByRole("heading", { name: "Tableau de bord RGPD Guard" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "Tableau de bord RGPD Guard" })).toBeVisible();
  await capture(page, "10-deconnexion", testInfo);
});

test("mobile : barre de navigation inférieure libellée @mobile", async ({ page }, testInfo) => {
  await login(page);
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  await expect(nav.getByRole("link", { name: "Bac à sable" })).toBeVisible();
  const navBox = await nav.boundingBox();
  const viewport = page.viewportSize();
  expect(navBox && viewport && navBox.width > viewport.width * 0.9).toBe(true);
  await capture(page, "11-mobile-journal", testInfo);
  await navigate(page, "Bac à sable");
  await capture(page, "12-mobile-bac-a-sable", testInfo);
});
