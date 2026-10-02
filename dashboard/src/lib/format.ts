// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM_APP.md
// Formats d'affichage : dates locales, scores à deux décimales, latences entières.

const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "medium" });

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : dateFormat.format(date);
}

export function formatScore(value: number): string {
  return value.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatMs(value: number): string {
  return Math.round(value).toLocaleString("fr-FR");
}
