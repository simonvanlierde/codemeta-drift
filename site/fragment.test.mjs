import assert from "node:assert/strict";
import { test } from "node:test";
import { chosenTag, parseFragment, releaseHref } from "./fragment.mjs";

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

test("?tag picks a listed release, and anything else the newest", () => {
  const tags = ["3.1", "4.0"];
  assert.equal(chosenTag("?tag=3.1", tags), "3.1");
  assert.equal(chosenTag("", tags), "4.0");
  assert.equal(chosenTag("?tag=../secrets", tags), "4.0");
  assert.equal(chosenTag("?tag=3.0", tags), "4.0");
  assert.equal(chosenTag("?tag=", tags), "4.0");
  assert.equal(chosenTag("?tag=3.1&tag=4.0", tags), "3.1");
});

test("the newest release links to the page itself, an older one to its ?tag, and both stay on the site", () => {
  const tags = ["3.1", "4.0"];
  assert.equal(releaseHref("4.0", tags), ".");
  assert.equal(releaseHref("3.1", tags), "?tag=3.1");
  // Pages also serves the page at //codemeta-drift/, where a pathname href would leave the origin.
  const base = "https://simonvanlierde.com//codemeta-drift/";
  for (const tag of tags) assert.equal(new URL(releaseHref(tag, tags), base).origin, "https://simonvanlierde.com");
});
