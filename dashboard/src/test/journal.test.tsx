// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md#14.5 | docs/DESIGN_SYSTEM.md#6.13 | docs/DESIGN_SYSTEM_APP.md#architecture
// @verifies docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md#14.5 | docs/DESIGN_SYSTEM.md#6.13 | docs/DESIGN_SYSTEM_APP.md#architecture
// Journal vide : l'absence est nommée selon sa cause, journal encore vide ou filtres sans résultat (DS §14.5).
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import { Journal } from "../pages/Journal";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("journal vide", () => {
  it("dit que rien n'est journalisé sans filtre, et que les filtres ne trouvent rien avec un filtre", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/v1/audit/events")) return jsonResponse(200, { events: [], total: 0, limit: 20, offset: 0 });
        if (url.endsWith("/v1/audit/stats")) return jsonResponse(200, { total: 0, by_decision: {}, by_label: {} });
        if (url.endsWith("/v1/policies"))
          return jsonResponse(200, { policy: {}, source: "default", labels: { IBAN: "IBAN" }, categories: {} });
        return jsonResponse(200, { authenticated: true });
      }),
    );
    render(
      <AuthProvider>
        <MemoryRouter>
          <Journal />
        </MemoryRouter>
      </AuthProvider>,
    );
    expect(await screen.findByText("Aucun événement journalisé pour le moment.")).toBeTruthy();
    await userEvent.selectOptions(screen.getByLabelText("Décision"), "block");
    expect(await screen.findByText("Aucun événement ne correspond à ces filtres.")).toBeTruthy();
  });
});
