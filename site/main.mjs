// Draws the coverage matrix, the route between two formats and the upstream check from data.json.
// Every string goes in through textContent: cells and reasons come from crosswalk files.

// Citation files first, then package manifests; the matrix rows follow this order.
const LABELS = {
  "cff-1.2.0": "CFF 1.2.0", zenodo: "Zenodo", bibtex: "BibTeX", pep621: "pyproject.toml", "pkg-info": "Python PKG-INFO",
  cargo: "Cargo", npm: "npm", "r-description": "R DESCRIPTION", julia: "Julia Project.toml",
};
const label = (fmt) => LABELS[fmt] ?? fmt;
const ORDER = Object.keys(LABELS);
const rank = (fmt) => (ORDER.includes(fmt) ? ORDER.indexOf(fmt) : ORDER.length);

// What each upstream state says about a cell on CodeMeta's main branch.
const STATES = {
  missing: "has no crosswalk file or property table on main",
  unmatched: "can't be joined: the crosswalk and the property table list this property a different number of times",
  fixed: "now says what the reviewed mapping says, so the correction can go",
  changed: "has new text",
};

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  node.append(...children.filter((c) => c !== null && c !== undefined));
  return node;
}

const code = (text) => el("code", {}, text);

// One row per format, one column per term: each cell is a status mark, and its path is in the detail.
// The reviewed formats come first; the crosswalks nobody reviewed follow in their own group.
function matrix(data, unreviewed, onPick) {
  const table = document.getElementById("matrix");
  const head = el("tr", {}, el("th", { scope: "col" }, "Format"));
  for (const term of data.terms) head.append(el("th", { scope: "col", class: "rot" }, el("span", {}, code(term))));
  head.append(el("th", { scope: "col", class: "rot" }, el("span", {}, "as written")));
  table.append(el("thead", {}, head));
  const formats = [...data.formats].sort((a, b) => rank(a) - rank(b)).map((format) => ({ format, label: label(format) }));
  const legend = unreviewed && el("span", {}, "Reviewed. Every cell is checked, and each change has a reason.");
  table.append(group(data.terms, formats, data, onPick, { legend, tally: usableTally }));
  if (!unreviewed) return;
  const shapes = el("span", {}, "Not reviewed. The mark says only what CodeMeta's cell looks like: ");
  for (const [name, { mark }] of Object.entries(unreviewed.statuses)) shapes.append(el("span", { class: "mark" }, mark), ` ${name} `);
  shapes.append(". The last column counts the cells that read as a path.");
  table.append(group(data.terms, unreviewed.formats, unreviewed, onPick, { legend: shapes, tally: pathTally, note: ", not reviewed" }));
}

// One tbody: an optional group label row, then a row per format with a button per term and a tally.
function group(terms, formats, data, onPick, { legend, tally, note = "" }) {
  const body = el("tbody");
  if (legend) body.append(el("tr", { class: "group" }, el("th", { scope: "rowgroup", colspan: String(terms.length + 2) }, legend)));
  const byKey = new Map(data.cells.map((c) => [`${c.format} ${c.term}`, c]));
  for (const { format, label: name } of formats) {
    const row = el("tr", {}, el("th", { scope: "row" }, name));
    const own = [];
    for (const term of terms) {
      const cell = byKey.get(`${format} ${term}`);
      const td = el("td");
      if (cell) {
        own.push(cell);
        const button = el(
          "button",
          { type: "button", class: `cell s-${cell.status.replace(" ", "-")}`, "data-status": cell.status,
            "data-format": format, "data-term": term, "data-path": cell.path ?? "",
            "aria-label": `${name}, ${term}: ${cell.status}${cell.path ? `, ${cell.path}` : ""}${note}` },
          el("span", { class: "mark", "aria-hidden": "true" }, data.statuses[cell.status].mark),
        );
        button.addEventListener("click", () => onPick(cell, button));
        td.append(button);
      }
      row.append(td);
    }
    row.append(el("td", { class: "tally" }, ...tally(own, data.statuses)));
    body.append(row);
  }
  return body;
}

// The crosswalk cells for a term the format has a field for; the tally and the headline count these.
const needed = (cells) => cells.filter((c) => c.crosswalk && c.status !== "no field");

const usableTally = (cells) => {
  if (!cells[0]?.crosswalk) return ["–", el("span", { class: "vh" }, " no CodeMeta crosswalk")];
  const fields = needed(cells);
  return [`${fields.filter((c) => c.status === "as-is").length} of ${fields.length}`, el("span", { class: "vh" }, " usable as written")];
};

// Nothing in a crosswalk nobody reviewed is known to work: count the cells that at least read as a path.
const pathTally = (cells, statuses) => [
  `${cells.filter((c) => c.status === "path").length} `,
  el("span", { "aria-hidden": "true" }, statuses.path.mark),
  el("span", { class: "vh" }, " read as a path"),
];

function detail(statuses, labels, reviewed, upstream) {
  const box = document.getElementById("detail");
  const hint = box.firstElementChild;
  const changes = new Map((upstream?.cells ?? []).map((c) => [`${c.format} ${c.term}`, c]));
  let picked = null;
  return (cell, button) => {
    picked?.removeAttribute("aria-pressed");
    button.setAttribute("aria-pressed", "true");
    picked = button;
    const was = (cell.cell ?? "").trim();
    const { mark, meaning } = statuses[cell.status];
    const name = labels.get(cell.format) ?? cell.format;
    const rows = [
      ["Status", `${mark} ${cell.status}: ${meaning}`],
      ["CodeMeta's cell", cell.crosswalk ? (was ? code(was) : cell.cell === null ? "can't be joined" : "empty") : "no CodeMeta crosswalk for this format"],
      ["Path used", cell.path ? code(cell.path) : cell.status in reviewed ? "none" : "none yet: nobody has reviewed this crosswalk"],
    ];
    if (cell.reason) rows.push(["Why", cell.reason]);
    const now = changes.get(`${cell.format} ${cell.term}`);
    if (now) {
      rows.push(["On main", el("span", {}, `The cell ${STATES[now.state]}`, now.now ? el("span", {}, ": ", code(now.now)) : null, ".")]);
    }
    const list = el("dl");
    for (const [key, value] of rows) list.append(el("dt", {}, key), el("dd", {}, value));
    const close = el("button", { type: "button" }, "Close");
    close.addEventListener("click", () => {
      button.removeAttribute("aria-pressed");
      picked = null;
      box.replaceChildren(hint);
      // A filter may have made the cell inert; focus the filter that hid it instead.
      (button.closest("[inert]") ? document.querySelector('#filters [aria-pressed="true"]') : button).focus();
    });
    document.getElementById("picked").textContent = `${cell.term} in ${name}: ${cell.status}`;
    box.replaceChildren(el("div", { class: "detail-head" }, el("h3", {}, code(cell.term), ` in ${name}`), close), list);
  };
}

function filters(data) {
  const box = document.getElementById("filters");
  const table = document.getElementById("matrix");
  const buttons = [];
  for (const name of ["all", ...Object.keys(data.statuses)]) {
    // "all" also shows the crosswalks nobody reviewed, which no status counts, so it has no number.
    const count = name === "all" ? null : data.cells.filter((c) => c.status === name).length;
    const mark = name === "all" ? null : el("span", { class: "mark", "aria-hidden": "true" }, data.statuses[name].mark);
    const button = el("button", { type: "button", "aria-pressed": String(name === "all") }, mark, ` ${name} `,
      count === null ? null : el("span", { class: "n" }, String(count)));
    button.addEventListener("click", () => {
      for (const b of buttons) b.setAttribute("aria-pressed", String(b === button));
      if (name === "all") delete table.dataset.only;
      else table.dataset.only = name.replace(" ", "-");
      // Dimmed cells leave the tab order and the accessibility tree, not just the eye.
      for (const td of table.querySelectorAll("tbody td:not(.tally)")) {
        const cell = td.querySelector(".cell");
        td.inert = name !== "all" && cell?.dataset.status !== name;
      }
    });
    buttons.push(button);
    box.append(button);
  }
}

function route(data) {
  const from = document.getElementById("from");
  const to = document.getElementById("to");
  const list = document.getElementById("route");
  const formats = [...data.formats].sort((a, b) => rank(a) - rank(b));
  for (const select of [from, to]) for (const fmt of formats) select.append(el("option", { value: fmt }, label(fmt)));
  from.value = "pep621";
  to.value = "cargo";
  const paths = new Map(data.cells.map((c) => [`${c.format} ${c.term}`, c.path]));
  const end = (fmt, term) => {
    const path = paths.get(`${fmt} ${term}`);
    return path ? el("span", { class: "stop" }, code(path)) : el("span", { class: "stop gap" }, `no ${label(fmt)} field`);
  };
  const draw = () => {
    list.replaceChildren();
    for (const term of data.terms) {
      const whole = paths.get(`${from.value} ${term}`) && paths.get(`${to.value} ${term}`);
      list.append(el("li", { class: whole ? "whole" : "broken" }, end(from.value, term),
        el("span", { class: "hub" }, code(term)), end(to.value, term)));
    }
  };
  from.addEventListener("change", draw);
  to.addEventListener("change", draw);
  draw();
}

function upstreamSection(upstream, tag) {
  if (!upstream) return;
  const tab = document.getElementById("tab-upstream");
  tab.hidden = false;
  document.getElementById("upstream-count").textContent = String(upstream.cells.length);
  const date = upstream.date.slice(0, 10);
  document.getElementById("checked").textContent = `upstream main checked ${date} at ${upstream.commit.slice(0, 7)}`;
  const intro = document.getElementById("upstream-intro");
  intro.append(`CodeMeta's main branch at commit `, el("a", { href: `https://github.com/codemeta/codemeta/commit/${upstream.commit}` },
    upstream.commit.slice(0, 7)), `, ${date}. `,
    upstream.cells.length ? `${upstream.cells.length} of the matrix's cells read differently there than at ${tag}:`
      : `Every cell in the matrix reads the same there as at ${tag}.`);
  const list = document.getElementById("upstream-cells");
  for (const c of upstream.cells) {
    list.append(el("li", {}, code(c.term), ` in ${label(c.format)} ${STATES[c.state]}`,
      c.now !== null ? el("span", {}, ": ", code(c.now)) : null));
  }
  const counts = new Map();
  for (const f of upstream.drift) counts.set(f.code, (counts.get(f.code) ?? 0) + 1);
  const table = document.getElementById("drift");
  table.append(el("thead", {}, el("tr", {}, el("th", { scope: "col" }, "Check"), el("th", { scope: "col" }, "Findings"))));
  const body = el("tbody");
  for (const [name, n] of [...counts].sort()) body.append(el("tr", {}, el("td", {}, code(name)), el("td", {}, String(n))));
  table.append(body);
}

// Three views as tabs. Arrow keys, Home and End move between them and show the one reached; each
// view except the matrix has a fragment (#route, #upstream) so it can be linked to.
const TABS = ["matrix", "route", "upstream"];

function showTab(name, focus = false) {
  for (const other of TABS) {
    const tab = document.getElementById(`tab-${other}`);
    const on = other === name;
    tab.setAttribute("aria-selected", String(on));
    tab.tabIndex = on ? 0 : -1;
    document.getElementById(`panel-${other}`).hidden = !on;
    if (on && focus) tab.focus();
  }
}

function tabs() {
  const list = document.getElementById("tabs");
  const visible = () => TABS.filter((name) => !document.getElementById(`tab-${name}`).hidden);
  const choose = (name, focus) => {
    showTab(name, focus);
    history.replaceState(null, "", name === "matrix" ? location.pathname : `#${name}`);
  };
  for (const name of TABS) document.getElementById(`tab-${name}`).addEventListener("click", () => choose(name, false));
  list.addEventListener("keydown", (event) => {
    const names = visible();
    const at = names.indexOf(document.activeElement.id.replace("tab-", ""));
    const next = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: names.length - 1 }[event.key];
    if (at < 0 || next === undefined) return;
    event.preventDefault();
    choose(names[(next + names.length) % names.length], true);
  });
}

// The SSSOM export's identifiers resolve here: #term/<term>, #field/<format>/<path> and #format/<format>,
// each percent-encoded as the export writes it. The first matching cell is chosen and scrolled to.
function follow() {
  const [kind, ...rest] = location.hash.slice(1).split("/");
  if (kind === "route" || (kind === "upstream" && !document.getElementById("tab-upstream").hidden)) {
    showTab(kind);
    return;
  }
  let parts;
  try {
    parts = rest.map(decodeURIComponent);
  } catch {
    return; // a malformed fragment selects nothing
  }
  const match = {
    term: (b) => b.dataset.term === parts[0],
    format: (b) => b.dataset.format === parts[0],
    field: (b) => b.dataset.format === parts[0] && b.dataset.path === parts.slice(1).join("/"),
  }[kind];
  if (!match) return;
  const cells = [...document.querySelectorAll("#matrix .cell")];
  // codemeta.json is the hub and has no row: its field ids open the term's first cell instead.
  const hub = kind === "field" && parts[0] === "codemeta" && ((b) => b.dataset.term === parts.slice(1).join("/").replaceAll("[]", ""));
  const button = cells.find(match) ?? (hub ? cells.find(hub) : undefined);
  if (!button) return;
  showTab("matrix");
  // A filtered-out cell can't take focus: show every cell first.
  if (button.closest("[inert]")) document.querySelector("#filters button").click();
  button.click();
  button.scrollIntoView({ block: "center" });
  button.focus({ preventScroll: true });
}

// The headline: of the crosswalk cells for a field the format has, how many work as written, as a figure and a bar.
function score(data) {
  const crosswalk = data.cells.filter((c) => c.crosswalk);
  const fields = needed(data.cells);
  const count = (status) => fields.filter((c) => c.status === status).length;
  const formats = new Set(crosswalk.map((c) => c.format)).size;
  const bar = el("div", { class: "bar", "aria-hidden": "true" });
  for (const status of ["as-is", "corrected", "added"]) {
    const part = el("span", { class: `s-${status}` });
    part.style.flexGrow = String(count(status));
    bar.append(part);
  }
  document.getElementById("score").append(
    el("p", { class: "big" }, String(count("as-is")), el("span", {}, ` of ${fields.length}`)),
    bar,
    el("figcaption", {}, `cells in these ${formats} CodeMeta crosswalks can be used as written. `
      + `${count("corrected")} are wrong, ambiguous or prose, and ${count("added")} are blank although the format has the field. `
      + `The other ${crosswalk.length - fields.length} are for terms the format has no field for.`),
  );
}

async function start() {
  const response = await fetch("data.json", { cache: "no-cache" });
  const { coverage, unreviewed, upstream } = await response.json();
  document.getElementById("tag").textContent = coverage.codemeta_tag;
  document.getElementById("version").textContent = `codemeta-drift ${coverage.generator.version}`;
  score(coverage);
  const labels = new Map([...coverage.formats.map((f) => [f, label(f)]), ...(unreviewed?.formats ?? []).map((f) => [f.format, f.label])]);
  const statuses = { ...coverage.statuses, ...unreviewed?.statuses };
  matrix(coverage, unreviewed, detail(statuses, labels, coverage.statuses, upstream));
  filters(coverage);
  route(coverage);
  upstreamSection(upstream, coverage.codemeta_tag);
  tabs();
  follow();
  window.addEventListener("hashchange", follow);
}

start().catch((err) => {
  document.getElementById("detail").replaceChildren(el("p", { class: "note" }, `Could not load data.json: ${err.message}`));
});
