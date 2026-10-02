// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md#6.8 | docs/DESIGN_SYSTEM.md#1.5
// Pilule colorée : fond *-soft, texte *-on-soft, icône et libellé explicite (DS §6.8, §1.5).
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { Tone } from "../../lib/decisions";

export function Badge({ tone, icon: Icon, children }: { tone: Tone; icon?: LucideIcon; children: ReactNode }) {
  return (
    <span className={`badge badge-${tone}`}>
      {Icon ? <Icon size={14} aria-hidden="true" /> : null}
      {children}
    </span>
  );
}
