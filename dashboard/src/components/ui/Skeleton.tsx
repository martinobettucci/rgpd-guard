// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md
// Squelette de chargement à la forme du contenu final (DS §6.13).
import { t } from "../../i18n";

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div aria-busy="true" aria-live="polite">
      <span className="sr-only">{t("common.loading")}</span>
      {Array.from({ length: lines }, (_, index) => (
        <div key={index} className="skeleton" style={{ width: `${90 - index * 15}%`, marginBottom: 8 }} />
      ))}
    </div>
  );
}
