// @spec docs/BACKLOG.md#RG-013 | docs/DESIGN_SYSTEM.md
// Détecte les textes visibles écrits en dur dans le JSX en analysant l'arbre syntaxique TypeScript (DS §11.1) :
// JsxText, chaînes littérales enfants et attributs visibles (title, aria-label, placeholder, alt).
// Les textes sans lettre (ponctuation, nombres) sont admis.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import ts from "typescript";

const VISIBLE_ATTRIBUTES = new Set(["title", "aria-label", "placeholder", "alt"]);
const LETTER = /\p{L}/u;
const problems = [];

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path);
    else if (path.endsWith(".tsx") && !path.endsWith(".test.tsx")) check(path);
  }
}

function report(file, source, node, text) {
  const { line } = source.getLineAndCharacterOfPosition(node.getStart(source));
  problems.push(`${file}:${line + 1} texte en dur : ${JSON.stringify(text.trim())}`);
}

function check(file) {
  const source = ts.createSourceFile(file, readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const visit = (node) => {
    if (ts.isJsxText(node) && LETTER.test(node.text)) report(file, source, node, node.text);
    if (ts.isJsxExpression(node) && node.expression && ts.isStringLiteral(node.expression) && ts.isJsxElement(node.parent)) {
      if (LETTER.test(node.expression.text)) report(file, source, node, node.expression.text);
    }
    if (ts.isJsxAttribute(node) && VISIBLE_ATTRIBUTES.has(node.name.getText(source)) && node.initializer) {
      const init = node.initializer;
      if (ts.isStringLiteral(init) && LETTER.test(init.text)) report(file, source, node, init.text);
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
}

walk(new URL("../src", import.meta.url).pathname);
if (problems.length) {
  console.error(problems.join("\n"));
  console.error(`${problems.length} texte(s) à déplacer dans src/i18n/fr.ts`);
  process.exit(1);
}
console.log("Aucun texte en dur dans le JSX.");
