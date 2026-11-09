import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

// main.mjs touches the DOM on import, so this reads its source instead of running it.
const source = readFileSync(new URL("./main.mjs", import.meta.url), "utf8");

test("no local variable hides a top-level function", () => {
  const functions = [...source.matchAll(/^(?:async )?function (\w+)/gm)].map((m) => m[1]);
  const hidden = functions.filter((name) => new RegExp(`\\b(?:const|let|var) ${name}\\b`).test(source));
  assert.deepEqual(hidden, []);
});
