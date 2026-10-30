// Turns a mapping export into the crosswalk table's rows and filters them. No DOM here, so
// crosswalk.test.mjs runs it under `node --test`.

// The export's major version this page reads. A minor only adds fields, formats or terms
// (docs/mapping-export.md), so any 1.x renders; another major must not.
export const SCHEMA_MAJOR = "1";

// Column order and headings. A format a newer minor adds goes after these, under its id.
const FORMATS = [
  ["cff-1.2.0", "CITATION.cff"],
  ["codemeta", "codemeta.json"],
  ["zenodo", ".zenodo.json"],
  ["pep621", "pyproject.toml"],
  ["cargo", "Cargo.toml"],
  ["npm", "package.json"],
];

/** Throws on an export this page can't read, so the caller shows an error instead of a table. */
export function checkExport(data) {
  if (data === null || typeof data !== "object" || !Array.isArray(data.rows)) {
    throw new Error("The mapping file has no rows.");
  }
  const version = String(data.schema_version ?? "");
  if (version.split(".")[0] !== SCHEMA_MAJOR || !/^\d+\.\d+$/.test(version)) {
    throw new Error(
      `The mapping file has schema_version ${JSON.stringify(data.schema_version)}; this page reads ${SCHEMA_MAJOR}.x only.`,
    );
  }
}

/** What a row's source says, for a person: a curated row's reason, or the crosswalk file it reads. */
export function sourceText(source) {
  if (source.startsWith("curated:")) return source.slice("curated:".length);
  const m = /^crosswalk:(.+)@([^@]+)$/.exec(source);
  return m ? `${m[1]} at CodeMeta ${m[2]}` : source;
}

/**
 * The table: `columns` is [{format, label}], `rows` is one entry per term in the export's order,
 * each {term, cells: {format: exportRow}, notes: [{label, text, href?}]}. Notes hold the reason
 * for each missing field, each comment and each upstream report, so they can be shown, not only
 * hovered.
 */
export function buildTable(data) {
  checkExport(data);
  const known = new Map(FORMATS);
  const formats = [...new Set(data.rows.map((r) => r.format))].sort((a, b) => {
    const ia = FORMATS.findIndex(([f]) => f === a);
    const ib = FORMATS.findIndex(([f]) => f === b);
    return (ia < 0 ? FORMATS.length : ia) - (ib < 0 ? FORMATS.length : ib);
  });
  // codemeta.json's column only repeats the term when every path equals it.
  const codemetaEcho = data.rows.every((r) => r.format !== "codemeta" || r.path === r.term);
  const columns = formats
    .filter((f) => !(f === "codemeta" && codemetaEcho))
    .map((format) => ({ format, label: known.get(format) ?? format }));

  const byTerm = new Map();
  for (const r of data.rows) {
    if (!byTerm.has(r.term)) byTerm.set(r.term, { term: r.term, cells: {}, notes: [] });
    byTerm.get(r.term).cells[r.format] = r;
  }
  for (const row of byTerm.values()) {
    for (const { format, label } of columns) {
      const cell = row.cells[format];
      if (!cell) continue;
      if (cell.path === null) row.notes.push({ label, text: `no field: ${sourceText(cell.source)}` });
      if (cell.comment) row.notes.push({ label, text: cell.comment });
      if (cell.see_also) row.notes.push({ label, text: "reported upstream", href: cell.see_also });
    }
  }
  return { columns, rows: [...byTerm.values()] };
}

/** Whether a table row matches the search: the term or any format's path, case-insensitive. */
export function matches(row, query) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  if (row.term.toLowerCase().includes(q)) return true;
  return Object.values(row.cells).some((c) => c.path?.toLowerCase().includes(q));
}
