import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";

// main.mjs touches the DOM on import, so this reads its source instead of running it.
const source = readFileSync(new URL("./main.mjs", import.meta.url), "utf8");

test("no local variable hides a top-level function", () => {
  const functions = [...source.matchAll(/^(?:async )?function (\w+)/gm)].map((m) => m[1]);
  const hidden = functions.filter((name) => new RegExp(`\\b(?:const|let|var) ${name}\\b`).test(source));
  assert.deepEqual(hidden, []);
});

test("main.mjs parses: CI runs it in no browser", () => {
  execFileSync(process.execPath, ["--check", new URL("./main.mjs", import.meta.url).pathname]);
});

test("choosing the Matrix tab keeps ?tag and stays on the site", () => {
  assert.match(source, /name === "matrix" \? location\.search \|\| "\."/);
  assert.doesNotMatch(source, /location\.pathname/);
});

test("the release links are redrawn on every tab choice and fragment change", () => {
  // CI runs no browser: this pins the two call sites that keep the links' fragment current.
  assert.match(source, /history\.replaceState\([^\n]*\n\s*drawReleases\(\);/);
  assert.match(source, /follow\(hub\);\n\s*drawReleases\(\);/);
});

test("codemeta field ids are looked up through hubTerm with the shown release's map", () => {
  assert.match(source, /const term = hubTerm\(target, hub\);\n.*cells\.find\(match\) \?\? \(term === undefined \? undefined : cells\.find\(\(b\) => b\.dataset\.term === term\)\)/);
  assert.match(source, /follow\(hub\);\n\s*window\.addEventListener\("hashchange"/);
  assert.match(source, /const \{ coverage, hub, unreviewed, upstream \} = tag === newest \? latest : \{ \.\.\.\(await load\(`data-\$\{tag\}\.json`\)\)/);
});
