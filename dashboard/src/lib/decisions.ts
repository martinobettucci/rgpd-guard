// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md | docs/DESIGN_SYSTEM_APP.md
// Correspondance unique décision -> couleur de donnée, icône et libellé (DS §2.6, §12.5).
import { Ban, CircleCheck, EyeOff, OctagonAlert, RotateCcw, ShieldAlert, TriangleAlert, type LucideIcon } from "lucide-react";
import { tOr } from "../i18n";

export type Tone = "brand" | "success" | "accent" | "danger" | "neutral";

const DECISIONS: Record<string, { tone: Tone; icon: LucideIcon }> = {
  block: { tone: "danger", icon: Ban },
  deny: { tone: "danger", icon: OctagonAlert },
  leak: { tone: "danger", icon: ShieldAlert },
  warn: { tone: "accent", icon: TriangleAlert },
  pseudonymize: { tone: "brand", icon: EyeOff },
  rehydrate: { tone: "brand", icon: RotateCcw },
  allow: { tone: "success", icon: CircleCheck },
};

export function decisionStyle(decision: string): { tone: Tone; icon: LucideIcon; label: string } {
  const known = DECISIONS[decision];
  return {
    tone: known?.tone ?? "neutral",
    icon: known?.icon ?? CircleCheck,
    label: tOr(`decision.${decision}`, "decision.unknown"),
  };
}

export function markClass(action: string): string {
  if (action === "block") return "mark-block";
  if (action === "warn") return "mark-warn";
  return "mark-pseudonymize";
}
