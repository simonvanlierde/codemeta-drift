import assert from "node:assert/strict";
import { test } from "node:test";
import {
  cellWords, chosenTag, hubTerm, linkParts, matrixKey, needed, nextCell, pageTitle, parseFragment, releaseHref, releaseLinks, scoreCaption,
  sourceHref, splitByCrosswalk, tabStop, upstreamLines,
} from "./fragment.mjs";

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

test("a reason's URLs become links and trailing punctuation stays text", () => {
  assert.deepEqual(linkParts("see https://example.org/a. Or https://example.org/b, then"), [
    "see ",
    { url: "https://example.org/a" },
    ".",
    " Or ",
    { url: "https://example.org/b" },
    ",",
    " then",
  ]);
  assert.deepEqual(linkParts("no link"), ["no link"]);
});

test("a source link encodes each path segment and opens the line", () => {
  assert.equal(
    sourceHref("4.0", "crosswalks/Citation File Format 1.2.0.csv", 46),
    "https://github.com/codemeta/codemeta/blob/4.0/crosswalks/Citation%20File%20Format%201.2.0.csv?plain=1#L46",
  );
});

// Three format rows of four terms; false is an empty or filtered-out cell.
const grid = [
  [false, true, false, true],
  [true, false, false, false],
  [false, true, true, false],
];

test("arrows step over empty cells and stop at the edge", () => {
  assert.deepEqual(nextCell(grid, [0, 1], "ArrowRight"), [0, 3]);
  assert.equal(nextCell(grid, [0, 3], "ArrowRight"), null);
  assert.deepEqual(nextCell(grid, [2, 2], "ArrowLeft"), [2, 1]);
  assert.equal(nextCell(grid, [1, 0], "ArrowLeft"), null);
});

test("up and down keep the column and pass rows with no cell there", () => {
  assert.deepEqual(nextCell(grid, [0, 1], "ArrowDown"), [2, 1]);
  assert.deepEqual(nextCell(grid, [2, 1], "ArrowUp"), [0, 1]);
  assert.equal(nextCell(grid, [1, 0], "ArrowDown"), null);
  assert.equal(nextCell(grid, [0, 1], "ArrowUp"), null);
});

test("Home and End stay in the row; with Ctrl they go to the first and last cell", () => {
  assert.deepEqual(nextCell(grid, [2, 2], "Home"), [2, 1]);
  assert.deepEqual(nextCell(grid, [0, 1], "End"), [0, 3]);
  assert.deepEqual(nextCell(grid, [2, 2], "Home", true), [0, 1]);
  assert.deepEqual(nextCell(grid, [0, 1], "End", true), [2, 2]);
  assert.equal(nextCell([[false]], [0, 0], "End", true), null);
  assert.deepEqual(nextCell(grid, [0, 3], "End"), [0, 3]);
  assert.deepEqual(nextCell([[false, false], [false, true]], [1, 1], "Home", true), [1, 1]);
});

test("other keys move nowhere", () => {
  assert.equal(nextCell(grid, [0, 1], "Enter"), null);
});

test("formats with a crosswalk come first; the rest are the ones the mapping adds", () => {
  const cells = [{ format: "cff", crosswalk: "x" }, { format: "ris", crosswalk: null }];
  assert.deepEqual(splitByCrosswalk([{ format: "cff" }, { format: "ris" }], cells), {
    own: [{ format: "cff" }],
    added: [{ format: "ris" }],
  });
});

test("upstream cells with no new text share a line per state and term", () => {
  const lines = upstreamLines([
    { format: "cff", term: "name", state: "missing", now: null },
    { format: "npm", term: "name", state: "missing", now: null },
    { format: "ris", term: "url", state: "changed", now: "x" },
  ]);
  assert.equal(lines.length, 2);
  assert.deepEqual(lines[0], { term: "url", state: "changed", now: "x", formats: ["ris"] });
  assert.deepEqual(lines[1], { term: "name", state: "missing", now: null, formats: ["cff", "npm"] });
});

// A key event as matrixKey reads it, recording whether the browser's default was taken.
const press = (key, mods = {}) => ({ key, altKey: false, shiftKey: false, ctrlKey: false, metaKey: false, ...mods, taken: false,
  preventDefault() { this.taken = true; } });

// One row of three cells, the middle one at [0, 1]; focus() records which cell got focus.
function row() {
  const focused = [];
  const cells = [[0, 1, 2].map((i) => ({ open: true, focus: () => focused.push(i) }))];
  return { cells, focused };
}

test("an arrow key moves focus and is taken from the browser", () => {
  const { cells, focused } = row();
  const event = press("ArrowRight");
  matrixKey(event, cells, [0, 1]);
  assert.deepEqual([event.taken, focused], [true, [2]]);
});

test("Alt, Shift, and Ctrl or Meta with an arrow are left to the browser", () => {
  for (const mods of [{ altKey: true }, { shiftKey: true }, { ctrlKey: true }, { metaKey: true }]) {
    const { cells, focused } = row();
    const event = press("ArrowLeft", mods);
    matrixKey(event, cells, [0, 1]);
    assert.deepEqual([event.taken, focused], [false, []], JSON.stringify(mods));
  }
});

test("Ctrl+Home and Meta+End move, and other keys are left alone", () => {
  for (const [key, mods, to] of [["Home", { ctrlKey: true }, [0]], ["End", { metaKey: true }, [2]]]) {
    const { cells, focused } = row();
    const event = press(key, mods);
    matrixKey(event, cells, [0, 1]);
    assert.deepEqual([event.taken, focused], [true, to]);
  }
  const { cells, focused } = row();
  const event = press("Enter");
  matrixKey(event, cells, [0, 1]);
  assert.deepEqual([event.taken, focused], [false, []]);
});

test("a key at the edge is still taken, so the page does not scroll", () => {
  const { cells, focused } = row();
  const event = press("ArrowRight");
  matrixKey(event, cells, [0, 2]);
  assert.deepEqual([event.taken, focused], [true, []]);
});

test("the tab stop is the first cell, and moves off a cell a filter hides", () => {
  assert.equal(tabStop([true, true], -1), 0);
  assert.equal(tabStop([false, true, true], 2), 2);
  assert.equal(tabStop([true, false, true], 1), 0);
  assert.equal(tabStop([false, false], 0), -1);
});

test("the headline counts each status it names, crosswalk cells for a base term's field only", () => {
  const base = new Set(["name"]);
  const cells = [
    ...["as-is", "as-is", "corrected", "notation", "notation", "notation", "scope", "scope", "scope", "scope", "added"]
      .map((status, i) => ({ format: i % 2 ? "a" : "b", term: "name", status, crosswalk: "x.csv" })),
    { format: "a", term: "name", status: "no field", crosswalk: "x.csv" },
    { format: "a", term: "name", status: "no term", crosswalk: "x.csv" },
    { format: "c", term: "name", status: "added", crosswalk: null },
    // A citation cell exists only where reviewed, so it would change the figures with each review.
    { format: "a", term: "url", status: "added", crosswalk: "x.csv" },
  ];
  assert.equal(needed(cells, base).length, 11);
  const { asIs, of, formats, parts } = scoreCaption(cells, base);
  assert.deepEqual([asIs, of, formats], [2, 11, 2]);
  assert.deepEqual(parts.map(([mark, words]) => `${mark}${words.split(" ")[0]}`), ["✎ 1", "≈ 3", "⊂ 4", "+ 1"]);
});

test("CodeMeta's cell is code when it has text, else words for why not", () => {
  const cell = { crosswalk: "x.csv", status: "corrected", cell: "a" };
  assert.equal(cellWords(cell), null);
  assert.equal(cellWords({ ...cell, cell: " " }), "empty");
  assert.equal(cellWords({ ...cell, cell: null }), "can't be matched to its property");
  assert.equal(cellWords({ ...cell, status: "no term", cell: null }), "none: CodeMeta has no property for this term");
  assert.equal(cellWords({ ...cell, crosswalk: null }), "no CodeMeta crosswalk for this format");
});
