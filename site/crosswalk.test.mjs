import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { buildTable, matches } from "./crosswalk.mjs";

const data = JSON.parse(readFileSync(new URL("../examples/mapping-3.1.json", import.meta.url), "utf8"));
const table = buildTable(data);
const search = (q) => table.rows.filter((r) => matches(r, q)).map((r) => r.term);

test("every term in the export gets one row", () => {
  const terms = [...new Set(data.rows.map((r) => r.term))];
  assert.deepEqual(table.rows.map((r) => r.term), terms);
});

test("columns follow the format order, codemeta kept because its paths differ from the terms", () => {
  assert.deepEqual(
    table.columns.map((c) => c.format),
    ["cff-1.2.0", "codemeta", "zenodo", "pep621", "cargo", "npm"],
  );
});

test("the codemeta column is dropped when every path equals its term", () => {
  const echo = { ...data, rows: [{ format: "codemeta", term: "name", path: "name", source: "curated:x" }] };
  assert.deepEqual(buildTable(echo).columns, []);
});

test("search finds a term by any format's key", () => {
  assert.deepEqual(search("given-names"), ["author.givenName"]);
  assert.deepEqual(search("PACKAGE.KEYWORDS"), ["keywords"]);
  assert.deepEqual(search("swhid"), ["swhid"]);
  assert.equal(search("").length, table.rows.length);
  assert.deepEqual(search("no-such-key"), []);
});

test("a missing field carries its reason as a visible note", () => {
  const row = table.rows.find((r) => r.term === "contributor");
  assert.equal(row.cells["cff-1.2.0"].path, null);
  assert.ok(row.notes.some((n) => n.label === "CITATION.cff" && n.text.includes("CFF 1.2.0 has no contributor list")));
});

test("an unknown schema_version is refused, so the page shows an error, not a table", () => {
  for (const v of ["2.0", "1", "", undefined]) {
    assert.throws(() => buildTable({ ...data, schema_version: v }), /schema_version/);
  }
  assert.throws(() => buildTable({ schema_version: "1.2" }), /no rows/);
  assert.doesNotThrow(() => buildTable({ ...data, schema_version: "1.9" }));
});
