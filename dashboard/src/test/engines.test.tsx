// @spec docs/BACKLOG.md#RG-016 | docs/DESIGN_SYSTEM.md | docs/DESIGN_SYSTEM_APP.md
// @verifies docs/BACKLOG.md#RG-016 | docs/DESIGN_SYSTEM.md | docs/DESIGN_SYSTEM_APP.md
// Page Moteurs : état et temps de chargement de chaque composant, composant indisponible, banc absent.
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import type { EnginesResponse } from "../lib/api";
import { Engines } from "../pages/Engines";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const engines: EnginesResponse = {
  default_profile: "equilibre",
  profiles: {
    rapide: { detectors: ["rules", "secrets"], classifiers_prompt: [], classifiers_output: [], missing: [] },
  },
  components: [
    { name: "rules", kind: "detecteur", ready: true, load_ms: 0.002, error: null, detail: {} },
    {
      name: "spacy",
      kind: "detecteur",
      ready: true,
      load_ms: 3412.6,
      error: null,
      detail: { fr: "fr_core_news_md (LGPL-LR)", en: "en_core_web_md (MIT)" },
    },
    { name: "gliner", kind: "detecteur", ready: false, load_ms: 0, error: "ModuleNotFoundError: gliner", detail: {} },
  ],
  vault: { sessions: 0, tokens: 0 },
  bench: null,
  labels: {},
  categories: {},
};

function renderEngines() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/v1/engines")) return jsonResponse(200, engines);
      return jsonResponse(200, { authenticated: true });
    }),
  );
  render(
    <AuthProvider>
      <MemoryRouter>
        <Engines />
      </MemoryRouter>
    </AuthProvider>,
  );
}

function componentRow(name: string): HTMLElement {
  const row = screen.getByText(name, { selector: ".mono" }).closest("li");
  if (!row) throw new Error(`ligne du composant ${name} introuvable`);
  return row;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Moteurs", () => {
  it("affiche le temps de chargement de chaque composant prêt, à côté de ses modèles", async () => {
    renderEngines();
    await screen.findByText("rules", { selector: ".mono" });
    expect(within(componentRow("rules")).getByText("Chargement : < 1 ms")).toBeTruthy();
    const spacy = within(componentRow("spacy"));
    expect(spacy.getByText("fr_core_news_md (LGPL-LR) · en_core_web_md (MIT)")).toBeTruthy();
    expect(spacy.getByText(`Chargement : ${(3413).toLocaleString("fr-FR").replace(/\s/g, " ")} ms`)).toBeTruthy();
  });

  it("nomme un composant indisponible et son erreur, sans temps de chargement", async () => {
    renderEngines();
    await screen.findByText("gliner", { selector: ".mono" });
    const gliner = within(componentRow("gliner"));
    expect(gliner.getByText("Indisponible")).toBeTruthy();
    expect(gliner.getByText("ModuleNotFoundError: gliner")).toBeTruthy();
    expect(gliner.queryByText(/Chargement/)).toBeNull();
  });

  it("indique comment mesurer le banc lorsqu'aucun n'est enregistré", async () => {
    renderEngines();
    expect(await screen.findByText(/Aucun banc d'évaluation enregistré dans cet environnement/)).toBeTruthy();
    expect(screen.getByText(/\.\/runDev\.sh bench/)).toBeTruthy();
  });
});
