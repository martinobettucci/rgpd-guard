// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM_APP.md#composants
// Badge de décision issu de la correspondance unique de lib/decisions.ts.
import { decisionStyle } from "../lib/decisions";
import { Badge } from "./ui/Badge";

export function DecisionBadge({ decision }: { decision: string }) {
  const style = decisionStyle(decision);
  return (
    <Badge tone={style.tone} icon={style.icon}>
      {style.label}
    </Badge>
  );
}
