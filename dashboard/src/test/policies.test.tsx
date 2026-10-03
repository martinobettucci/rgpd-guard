// @spec docs/BACKLOG.md#RG-015 | docs/DESIGN_SYSTEM.md#6.27 | docs/DESIGN_SYSTEM.md#6.22 | docs/DESIGN_SYSTEM_APP.md#composants
// @verifies docs/BACKLOG.md#RG-015 | docs/DESIGN_SYSTEM.md#6.27 | docs/DESIGN_SYSTEM.md#6.22 | docs/DESIGN_SYSTEM_APP.md#composants
// Page Politiques : modale limitée à une section, enregistrement validé par le moteur, refus affiché dans la
// modale sans perte de saisie, rétablissement confirmé dans le flux.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import type { Policy, PolicyResponse } from "../lib/api";
import { Policies } from "../pages/Policies";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const policy: Policy = {
  version: 1,
  labels: { IBAN: { prompt: "block", tool_output: "pseudonymize", min_score: 0.5 } },
  categories: { SANTE: { threshold: 0.5, action: "block_if_identifier" } },
  allowlist: { values: [], patterns: [] },
  secret_files: [".env"],
  secret_files_exceptions: [],
  bypass_excluded: ["SECRET"],
} as unknown as Policy;

function response(source: "default" | "custom", current: Policy = policy): PolicyResponse {
  return { policy: current, source, labels: { IBAN: "IBAN" }, categories: { SANTE: "santé" } };
}

type Handler = (method: string, url: string, body: unknown) => Response | undefined;

function renderPolicies(source: "default" | "custom", handler: Handler) {
  const calls: { method: string; url: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      calls.push({ method, url, body });
      const answer = handler(method, url, body);
      if (answer) return answer;
      if (url.endsWith("/v1/policies") && method === "GET") return jsonResponse(200, response(source));
      return jsonResponse(200, { authenticated: true });
    }),
  );
  render(
    <AuthProvider>
      <MemoryRouter>
        <Policies />
      </MemoryRouter>
    </AuthProvider>,
  );
  return calls;
}

beforeAll(() => {
  // jsdom n'implémente pas la modale native : ouverture et fermeture réduites à l'attribut `open`.
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute("open");
  };
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Politiques", () => {
  it("modifie une section dans sa propre modale et n'annonce l'enregistrement qu'après la réponse du moteur", async () => {
    const calls = renderPolicies("default", (method, url, body) =>
      method === "PUT" && url.endsWith("/v1/policies") ? jsonResponse(200, response("custom", body as Policy)) : undefined,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Modifier : Types de données" }));
    const dialog = screen.getByRole("dialog", { name: "Types de données" });
    await userEvent.selectOptions(within(dialog).getByLabelText("Sur un prompt : IBAN"), "warn");
    await userEvent.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    expect((await screen.findByRole("status")).textContent).toContain("Enregistré.");
    const put = calls.find((call) => call.method === "PUT");
    expect((put?.body as Policy).labels.IBAN.prompt).toBe("warn");
    expect(screen.getByText("Politique personnalisée")).toBeTruthy();
  });

  it("affiche le refus du moteur dans la modale, avec le champ fautif, sans effacer la saisie", async () => {
    renderPolicies("default", (method) =>
      method === "PUT"
        ? jsonResponse(422, {
            detail: "Politique invalide.",
            erreurs: [{ champ: "allowlist.patterns", message: "expression régulière invalide « (x »" }],
          })
        : undefined,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Modifier : Liste blanche" }));
    const dialog = screen.getByRole("dialog", { name: "Liste blanche" });
    const patterns = within(dialog).getByLabelText("Expressions régulières");
    await userEvent.type(patterns, "(x");
    await userEvent.click(within(dialog).getByRole("button", { name: "Enregistrer" }));
    const alert = await within(dialog).findByRole("alert");
    expect(alert.textContent).toContain("Politique refusée par le moteur.");
    expect(alert.textContent).toContain("allowlist.patterns");
    expect((patterns as HTMLTextAreaElement).value).toBe("(x");
    expect(screen.getByRole("dialog", { name: "Liste blanche" })).toBeTruthy();
  });

  it("demande une confirmation dans le flux avant de rétablir la politique par défaut", async () => {
    const calls = renderPolicies("custom", (method, url) =>
      method === "POST" && url.endsWith("/v1/policies/reset") ? jsonResponse(200, response("default")) : undefined,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Rétablir la politique par défaut" }));
    expect(screen.getByText(/La politique personnalisée sera remplacée/)).toBeTruthy();
    expect(calls.some((call) => call.method === "POST")).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Rétablir" }));
    expect((await screen.findByRole("status")).textContent).toContain("Politique par défaut rétablie.");
    expect(calls.filter((call) => call.method === "POST")).toHaveLength(1);
  });

  it("garde le rétablissement visible mais indisponible, avec sa raison, quand la politique par défaut est active", async () => {
    renderPolicies("default", () => undefined);
    const button = await screen.findByRole("button", { name: "Rétablir la politique par défaut" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("La politique par défaut est déjà active.")).toBeTruthy();
  });
});
