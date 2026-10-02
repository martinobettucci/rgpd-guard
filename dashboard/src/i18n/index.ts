// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md
// Accès aux textes par clé, avec substitution de paramètres {nom}.
import { fr, type MessageKey } from "./fr";

export function t(key: MessageKey, params?: Record<string, string | number>): string {
  let text: string = fr[key];
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}

export function tOr(key: string, fallback: MessageKey): string {
  return key in fr ? fr[key as MessageKey] : fr[fallback];
}

export type { MessageKey };
