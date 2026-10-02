// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md
// Message d'état : erreur (role=alert), succès ou information (role=status) (DS §9.7).
import { CircleAlert, CircleCheck, Info } from "lucide-react";
import type { ReactNode } from "react";

export function Alert({ kind, children, id }: { kind: "danger" | "success" | "info"; children: ReactNode; id?: string }) {
  const Icon = kind === "danger" ? CircleAlert : kind === "success" ? CircleCheck : Info;
  return (
    <div id={id} className={`alert alert-${kind}`} role={kind === "danger" ? "alert" : "status"}>
      <Icon size={18} aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}
