// Fetches the mapping export and renders the crosswalk table. The logic lives in crosswalk.mjs.
import { buildTable, matches, sourceText } from "./crosswalk.mjs";

// pages.yml and `just site` put the export beside this file under its own name.
const EXPORT = "mapping-3.1.json";
const $ = (id) => document.getElementById(id);

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((c) => c != null));
  return node;
}

function showMeta(data) {
  $("tag").textContent = data.codemeta_tag;
  $("schema").textContent = data.schema_version;
  $("generator").textContent = `${data.generator?.name ?? "?"} ${data.generator?.version ?? "?"}`;
  $("export").href = EXPORT;
  $("export").textContent = EXPORT;
}

function renderTable({ columns, rows }) {
  $("head").replaceChildren(
    el(
      "tr",
      {},
      el("th", { scope: "col", textContent: "CodeMeta term" }),
      ...columns.map((c) => el("th", { scope: "col", textContent: c.label })),
    ),
  );
  $("body").replaceChildren(
    ...rows.flatMap((row, i) => {
      const tr = el(
        "tr",
        { id: row.term },
        el("th", { scope: "row" }, el("a", { href: `#${row.term}` }, el("code", { textContent: row.term }))),
      );
      for (const { format } of columns) {
        const cell = row.cells[format];
        const td = el("td");
        if (!cell) td.append(el("span", { className: "none", textContent: "not in export" }));
        else if (cell.path === null) {
          td.append(el("span", { className: "none", textContent: "no field", title: sourceText(cell.source) }));
        } else {
          td.title = sourceText(cell.source);
          // One alternative per line: "a | b" means the first of them that exists.
          // A break opportunity after each dot and before each [ keeps long Zenodo paths from widening the sheet.
          td.append(
            ...cell.path.split(" | ").map((p) => {
              const code = el("code");
              for (const part of p.split(/(?<=\.)|(?=\[)/)) code.append(part, el("wbr"));
              return code;
            }),
          );
        }
        tr.append(td);
      }
      const sources = el(
        "details",
        {},
        el("summary", { textContent: "Sources" }),
        el(
          "dl",
          {},
          ...columns.flatMap(({ format, label }) =>
            row.cells[format]
              ? [el("dt", { textContent: label }), el("dd", { textContent: sourceText(row.cells[format].source) })]
              : [],
          ),
        ),
      );
      const notes = row.notes.length
        ? el(
            "ul",
            {},
            ...row.notes.map((n) =>
              el(
                "li",
                {},
                el("span", { className: "fmt", textContent: `${n.label} ` }),
                n.href ? el("a", { href: n.href, textContent: n.text }) : n.text,
              ),
            ),
          )
        : null;
      // The notes and sources get a full-width line under the row, so the key columns stay narrow.
      const sub = el("tr", { className: "sub" }, el("td", { colSpan: columns.length + 1 }, notes, sources));
      tr.dataset.row = sub.dataset.row = String(i);
      return [tr, sub];
    }),
  );
}

function wireSearch(rows) {
  const input = $("q");
  const update = () => {
    const hits = rows.map((row) => matches(row, input.value));
    for (const tr of $("body").rows) tr.hidden = !hits[Number(tr.dataset.row)];
    const shown = hits.filter(Boolean).length;
    $("count").textContent =
      shown === rows.length ? `${rows.length} terms` : `${shown} of ${rows.length} terms match`;
  };
  input.addEventListener("input", update);
  update();
}

try {
  const res = await fetch(EXPORT);
  if (!res.ok) throw new Error(`Could not load ${EXPORT}: HTTP ${res.status}.`);
  const data = await res.json();
  const table = buildTable(data);
  showMeta(data);
  renderTable(table);
  wireSearch(table.rows);
  $("sheet").hidden = false;
  // The rows exist only now, so the browser could not scroll to a term's anchor on load.
  if (location.hash) $(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
} catch (err) {
  $("error").textContent = err.message;
  $("error").hidden = false;
}
