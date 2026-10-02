// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md#12.1
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";

const root = document.getElementById("root");
if (!root) throw new Error("élément #root absent");
createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
