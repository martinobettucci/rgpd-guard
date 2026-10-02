// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md
// @verifies docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md
// Initialisation des tests de composants (jsdom) : nettoyage du DOM entre deux tests.
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
