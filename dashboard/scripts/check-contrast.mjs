// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md#9.4 | docs/DESIGN_SYSTEM.md#14.1
// Mesure le contraste WCAG des couples de tokens effectivement utilisés (DS §9.4, §14.1) : objectif AA 4,5:1.
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../src/styles/tokens.css", import.meta.url), "utf8");
const tokens = Object.fromEntries([...css.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map((m) => [m[1], m[2]]));

const channel = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const luminance = (hex) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
};
const ratio = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const PAIRS = [
  ["brand-on-soft", "brand-soft"],
  ["success-on-soft", "success-soft"],
  ["accent-on-soft", "accent-soft"],
  ["danger-on-soft", "danger-soft"],
  ["text-2", "hover"],
  ["surface", "brand"],
  ["ink", "surface"],
  ["text-2", "surface"],
  ["text-2", "bg"],
  ["text-3", "surface"],
  ["text-3", "bg"],
  ["danger-on-soft", "surface"],
  ["brand", "surface"],
];
let failures = 0;
for (const [fg, bg] of PAIRS) {
  const value = ratio(tokens[`color-${fg}`], tokens[`color-${bg}`]);
  const ok = value >= 4.5;
  if (!ok) failures += 1;
  console.log(`${ok ? "OK  " : "ÉCHEC"} --color-${fg} sur --color-${bg} : ${value.toFixed(2)}:1`);
}
process.exit(failures ? 1 : 0);
