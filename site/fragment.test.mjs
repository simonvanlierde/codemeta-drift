import assert from "node:assert/strict";
import { test } from "node:test";
import { chosenTag, hubTerm, pageTitle, parseFragment, releaseHref, releaseLinks } from "./fragment.mjs";

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
  });
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

test("release links carry the fragment and mark the shown release", () => {
  assert.deepEqual(releaseLinks(["3.1", "4.0"], "3.1", "#route"), [
    { tag: "3.1", href: "?tag=3.1#route", current: true },
    { tag: "4.0", href: ".#route", current: false },
  ]);
  assert.deepEqual(releaseLinks(["3.1", "4.0"], "4.0", ""), [
    { tag: "3.1", href: "?tag=3.1", current: false },
    { tag: "4.0", href: ".", current: true },
  ]);
  assert.equal(pageTitle("codemeta-drift", "3.1"), "codemeta-drift (CodeMeta 3.1)");
});

test("an RO-Crate field id keeps the encoded slash in its path", () => {
  assert.deepEqual(parseFragment("#field/ro-crate/%40graph%5B%40id%3D.%2F%5D.name"), {
    kind: "field",
    format: "ro-crate",
    path: "@graph[@id=./].name",
  });
});

test("a codemeta field id opens its row's term from the hub map", () => {
  const hub = { "@type": "resourceType", "publisher.name | publisher": "publisher", "author[]": "author", isPartOf: "isPartOf" };
  assert.equal(hubTerm(parseFragment("#field/codemeta/%40type"), hub), "resourceType");
  assert.equal(hubTerm(parseFragment("#field/codemeta/publisher.name%20%7C%20publisher"), hub), "publisher");
  assert.equal(hubTerm(parseFragment("#field/codemeta/author%5B%5D"), hub), "author");
  assert.equal(hubTerm(parseFragment("#field/codemeta/isPartOf"), hub), "isPartOf");
  // Not a row, another format or another kind: nothing.
  assert.equal(hubTerm(parseFragment("#field/codemeta/constructor"), hub), undefined);
  assert.equal(hubTerm(parseFragment("#field/cargo/%40type"), hub), undefined);
  assert.equal(hubTerm(parseFragment("#term/name"), hub), undefined);
  assert.equal(hubTerm(parseFragment("#format/codemeta"), { undefined: "x" }), undefined);
  // A JSON key named __proto__ is the data's own; an inherited one is not.
  assert.equal(hubTerm(parseFragment("#field/codemeta/__proto__"), JSON.parse('{"__proto__": "x"}')), "x");
  assert.equal(hubTerm(parseFragment("#field/codemeta/__proto__"), hub), undefined);
});
