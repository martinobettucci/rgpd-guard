/// <reference types="vitest/config" />
// @spec docs/BACKLOG.md#RG-013 | docs/DAT.md#dashboard
// Le serveur de développement relaie /api vers le moteur (même origine pour le cookie de session).
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const engine = process.env.RGPD_GUARD_ENGINE_URL ?? "http://127.0.0.1:8742";

export default defineConfig({
  plugins: [react()],
  server: {
    // Hôtes acceptés par le serveur de développement : poste local et réseau Compose (tests E2E).
    allowedHosts: ["localhost", "127.0.0.1", "dashboard"],
    proxy: {
      "/api": {
        target: engine,
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
