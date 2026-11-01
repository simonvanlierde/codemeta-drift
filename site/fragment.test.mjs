import assert from "node:assert/strict";
import { test } from "node:test";
import { parseFragment } from "./fragment.mjs";

test("route and upstream open their tabs", () => {
  assert.deepEqual(parseFragment("#route"), { tab: "route" });
  assert.deepEqual(parseFragment("#upstream"), { tab: "upstream" });
});

test("term and format take one decoded name", () => {
  assert.deepEqual(parseFragment("#term/softwareVersion"), { kind: "term", term: "softwareVersion" });
  assert.deepEqual(parseFragment("#format/cff-1.2.0"), { kind: "format", format: "cff-1.2.0" });
  assert.deepEqual(parseFragment("#term/a%20b"), { kind: "term", term: "a b" });
});

test("field splits the format from the path and decodes brackets", () => {
  assert.deepEqual(parseFragment("#field/cff-1.2.0/authors%5B%5D/name"), {
    kind: "field",
    format: "cff-1.2.0",
    path: "authors[]/name",
    hubTerm: undefined,
  });
});

test("codemeta fields fall back to the term without brackets", () => {
  assert.equal(parseFragment("#field/codemeta/author%5B%5D").hubTerm, "author");
});

test("a malformed escape or an unknown prefix selects nothing", () => {
  assert.equal(parseFragment("#term/%E0"), null);
  assert.equal(parseFragment("#field/cargo/%E0"), null);
  assert.equal(parseFragment("#nope/x"), null);
  assert.equal(parseFragment(""), null);
});
