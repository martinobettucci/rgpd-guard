// @spec docs/BACKLOG.md#RG-016 | docs/DESIGN_SYSTEM.md | docs/DESIGN_SYSTEM_APP.md
// @verifies docs/BACKLOG.md#RG-016 | docs/DESIGN_SYSTEM.md | docs/DESIGN_SYSTEM_APP.md
// Formats d'affichage : une durée mesurée n'est jamais rendue par zéro (DS §14.6), latences entières (DS APP §4).
import { describe, expect, it } from "vitest";
import { formatMs, formatScore } from "../lib/format";

describe("durées", () => {
  it("écrit « < 1 » une durée mesurée sous la demi-milliseconde, jamais « 0 »", () => {
    expect(formatMs(0.2)).toBe("<\u00a01");
    expect(formatMs(0)).toBe("<\u00a01");
    expect(formatMs(0.49)).toBe("<\u00a01");
  });

  it("arrondit les autres durées à la milliseconde, avec séparateur de milliers français", () => {
    expect(formatMs(0.5)).toBe("1");
    expect(formatMs(749.4)).toBe("749");
    expect(formatMs(3412.6)).toBe((3413).toLocaleString("fr-FR"));
  });
});

describe("scores", () => {
  it("affiche deux décimales", () => {
    expect(formatScore(0.5)).toBe("0,50");
  });
});
