// @spec docs/BACKLOG.md#RG-013 | docs/BACKLOG.md#RG-014 | docs/BACKLOG.md#RG-001 | docs/DESIGN_SYSTEM_APP.md#composants | docs/DESIGN_SYSTEM_APP.md#terminologie
// @verifies docs/BACKLOG.md#RG-013 | docs/BACKLOG.md#RG-014 | docs/BACKLOG.md#RG-001 | docs/DESIGN_SYSTEM_APP.md#composants | docs/DESIGN_SYSTEM_APP.md#terminologie
// Composants : correspondance des décisions, texte annoté sans interprétation HTML, connexion refusée.
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import { DecisionBadge } from "../components/DecisionBadge";
import { decisionStyle } from "../lib/decisions";
import type { Analysis } from "../lib/api";
import { Home } from "../pages/Home";
import { t } from "../i18n";
import { AnnotatedText } from "../pages/Sandbox";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("décisions", () => {
  it("associe chaque décision à un ton, une icône et un libellé", () => {
    expect(decisionStyle("block").tone).toBe("danger");
    expect(decisionStyle("pseudonymize").label).toBe("Pseudonymisé");
    expect(decisionStyle("inconnue")).toMatchObject({ tone: "neutral", label: "Décision inconnue" });
  });

  it("affiche un libellé en plus de la couleur", () => {
    render(<DecisionBadge decision="warn" />);
    expect(screen.getByText("Avertissement")).toBeTruthy();
  });
});

describe("texte annoté", () => {
  it("rend les valeurs en texte brut, avec leur type", () => {
    const text = "Écrire à <b>jean@courriel-fictif.fr</b>";
    const start = text.indexOf("jean");
    const analysis = {
      findings: [
        { start, end: start + 25, label: "EMAIL", name: "adresse email", score: 0.99, detector: "rules", validated: true, action: "block", preview: "j***" },
      ],
    } as unknown as Analysis;
    const { container } = render(<AnnotatedText text={text} analysis={analysis} />);
    expect(container.querySelector("b")).toBeNull();
    expect(container.querySelector("mark")?.textContent).toContain("[adresse email]");
    expect(container.textContent).toContain("<b>");
  });
});

describe("accueil", () => {
  it("affiche l'état du moteur et refuse un jeton incorrect", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith("/health")) {
          return jsonResponse(200, { status: "ok", version: "0.1.0", env: "dev", profile: "equilibre", degraded: [], components: {} });
        }
        if (url.endsWith("/v1/auth/session") && init?.method === "POST") {
          return jsonResponse(401, { detail: "Jeton incorrect." });
        }
        return jsonResponse(200, { authenticated: false });
      }),
    );
    render(
      <AuthProvider>
        <MemoryRouter>
          <Home />
        </MemoryRouter>
      </AuthProvider>,
    );
    expect(await screen.findByText("Moteur en ligne")).toBeTruthy();
    await userEvent.type(screen.getByLabelText("Jeton du moteur"), "faux");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Jeton incorrect.");
  });
});

// Commande du plugin, absente du conteneur du tableau de bord (seul dashboard/ y est monté) : test ignoré, jamais faux vert.
const dashboardCommand = resolve(process.cwd(), "../plugins/rgpd-guard/commands/dashboard.md");

describe("accueil, moteur injoignable", () => {
  it("présente l'état injoignable comme l'état en ligne : une paire terme et valeur", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => (url.endsWith("/health") ? jsonResponse(503, {}) : jsonResponse(200, { authenticated: false }))),
    );
    render(
      <AuthProvider>
        <MemoryRouter>
          <Home />
        </MemoryRouter>
      </AuthProvider>,
    );
    const badge = await screen.findByText("Moteur injoignable");
    expect(badge.closest("dd")?.previousElementSibling?.textContent).toBe("État du moteur");
  });
});

describe("jeton de connexion", () => {
  it.skipIf(!existsSync(dashboardCommand))("l'accueil et la commande /rgpd-guard:dashboard nomment les mêmes commandes", () => {
    const tokenCommands = (text: string) => [...text.matchAll(/\.\/run(?:Dev|Staging|Prod)\.sh token/g)].map((m) => m[0]);
    const command = readFileSync(dashboardCommand, "utf-8");
    expect(tokenCommands(t("home.token.help"))).toEqual(["./runProd.sh token", "./runDev.sh token", "./runStaging.sh token"]);
    expect(tokenCommands(command)).toEqual(tokenCommands(t("home.token.help")));
  });
});
