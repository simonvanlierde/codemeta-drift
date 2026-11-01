// Draws the coverage matrix, the route between two formats and the upstream check from data.json.
// Every string goes in through textContent: cells and reasons come from crosswalk files.

// Citation files first, then package manifests; the matrix rows follow this order.
const LABELS = {
  "cff-1.2.0": "CFF 1.2.0", zenodo: "Zenodo", bibtex: "BibTeX", pep621: "pyproject.toml", "pkg-info": "Python PKG-INFO",
  cargo: "Cargo", npm: "npm", "r-description": "R DESCRIPTION", julia: "Julia Project.toml",
};
const label = (fmt) => LABELS[fmt] ?? fmt;
const ORDER = Object.keys(LABELS);
// Shorter names for the crosswalks nobody reviewed, where the crosswalk's own header runs long.
const SHORT = { "ISO_19115-1": "ISO 19115-1", "Perl Module Description (CPAN::Meta)": "Perl (CPAN::Meta)" };
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
function matrix(data, unreviewed, onPick) {
  const table = document.getElementById("matrix");
  const head = el("tr", {}, el("th", { scope: "col" }, "Format"));
  for (const term of data.terms) head.append(el("th", { scope: "col", class: "rot" }, el("span", {}, code(term))));
  head.append(el("th", { scope: "col", class: "rot" }, el("span", {}, "as written")));
  table.append(el("thead", {}, head));
  const body = el("tbody");
  if (unreviewed) {
    body.append(el("tr", { class: "group" }, el("th", { scope: "rowgroup", colspan: String(data.terms.length + 2) },
      el("span", {}, "Reviewed. Every cell is checked, and each change has a reason."))));
  }
  const byKey = new Map(data.cells.map((c) => [`${c.format} ${c.term}`, c]));
  for (const fmt of [...data.formats].sort((a, b) => rank(a) - rank(b))) {
    const row = el("tr", {}, el("th", { scope: "row" }, label(fmt)));
    const own = data.cells.filter((c) => c.format === fmt);
    for (const term of data.terms) {
      const cell = byKey.get(`${fmt} ${term}`);
      const td = el("td");
      if (cell) {
        const { mark } = data.statuses[cell.status];
        const button = el(
          "button",
          { type: "button", class: `cell s-${cell.status.replace(" ", "-")}`, "data-status": cell.status,
            "data-format": fmt, "data-term": term, "data-path": cell.path ?? "",
            "aria-label": `${label(fmt)}, ${term}: ${cell.status}${cell.path ? `, ${cell.path}` : ""}` },
          el("span", { class: "mark", "aria-hidden": "true" }, mark),
        );
        button.addEventListener("click", () => onPick(cell, button));
        td.append(button);
      }
      row.append(td);
    }
    // How many cells of the format's crosswalk that name a field can be used unchanged.
    const needed = own.filter((c) => c.status !== "no field");
    const usable = own[0]?.crosswalk ? `${needed.filter((c) => c.status === "as-is").length} of ${needed.length}` : "–";
    row.append(el("td", { class: "tally", "aria-label": own[0]?.crosswalk ? `${usable} usable as written` : "no CodeMeta crosswalk" }, usable));
    body.append(row);
  }
  table.append(body);
  if (unreviewed) table.append(others(data.terms, unreviewed, onPick));
}

// The crosswalks with no reviewed mapping, below the reviewed ones: each mark says only the cell's shape.
function others(terms, data, onPick) {
  const body = el("tbody", { class: "others" });
  const legend = el("span", {}, "Not reviewed. The mark says only what CodeMeta's cell looks like: ");
  for (const [name, { mark }] of Object.entries(data.statuses)) legend.append(el("span", { class: "mark" }, mark), ` ${name} `);
  body.append(el("tr", { class: "group" }, el("th", { scope: "rowgroup", colspan: String(terms.length + 2) }, legend)));
  const byKey = new Map(data.cells.map((c) => [`${c.format} ${c.term}`, c]));
  const name = (f) => SHORT[f.format] ?? f.label;
  for (const fmt of [...data.formats].sort((a, b) => name(a).localeCompare(name(b), "en", { sensitivity: "base" }))) {
    const row = el("tr", {}, el("th", { scope: "row" }, name(fmt)));
    let paths = 0;
    for (const term of terms) {
      const cell = { ...byKey.get(`${fmt.format} ${term}`), label: name(fmt), crosswalk: fmt.crosswalk, reviewed: false };
      if (cell.status === "path") paths += 1;
      const button = el("button", { type: "button", class: `cell u-${cell.status}`, "data-status": cell.status,
        "data-format": fmt.format, "data-term": term, "aria-label": `${name(fmt)}, ${term}: ${cell.status}, not reviewed` },
        el("span", { class: "mark", "aria-hidden": "true" }, data.statuses[cell.status].mark));
      button.addEventListener("click", () => onPick(cell, button));
      row.append(el("td", {}, button));
    }
    // Not reviewed, so nothing is known to be usable: count the cells that at least read as a path.
    row.append(el("td", { class: "tally", "aria-label": `${paths} cells read as a path` }, `${paths} ${data.statuses.path.mark}`));
    body.append(row);
  }
  return body;
}

function detail(data, unreviewed, upstream) {
  const box = document.getElementById("detail");
  const hint = box.firstElementChild;
  const changes = new Map((upstream?.cells ?? []).map((c) => [`${c.format} ${c.term}`, c]));
  let picked = null;
  return (cell, button) => {
    picked?.removeAttribute("aria-pressed");
    button.setAttribute("aria-pressed", "true");
    picked = button;
    const was = (cell.cell ?? "").trim();
    const { mark, meaning } = cell.reviewed === false ? unreviewed.statuses[cell.status] : data.statuses[cell.status];
    const name = cell.label ?? label(cell.format);
    const rows = [
      ["Status", `${mark} ${cell.status}: ${meaning}`],
      ["CodeMeta's cell", cell.crosswalk ? (was ? code(was) : cell.cell === null ? "can't be joined" : "empty") : "no CodeMeta crosswalk for this format"],
      ["Path used", cell.reviewed === false ? "none yet: nobody has reviewed this crosswalk" : cell.path ? code(cell.path) : "none"],
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
    const count = name === "all" ? data.cells.length : data.cells.filter((c) => c.status === name).length;
    const mark = name === "all" ? null : el("span", { class: "mark", "aria-hidden": "true" }, data.statuses[name].mark);
    const button = el("button", { type: "button", "aria-pressed": String(name === "all") }, mark, ` ${name} `,
      el("span", { class: "n" }, String(count)));
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
  const needed = crosswalk.filter((c) => c.status !== "no field");
  const count = (status) => needed.filter((c) => c.status === status).length;
  const formats = new Set(crosswalk.map((c) => c.format)).size;
  const bar = el("div", { class: "bar", "aria-hidden": "true" });
  for (const status of ["as-is", "corrected", "added"]) {
    const part = el("span", { class: `s-${status}` });
    part.style.flexGrow = String(count(status));
    bar.append(part);
  }
  document.getElementById("score").append(
    el("p", { class: "big" }, String(count("as-is")), el("span", {}, ` of ${needed.length}`)),
    bar,
    el("figcaption", {}, `cells in these ${formats} CodeMeta crosswalks can be used as written. `
      + `${count("corrected")} are wrong, ambiguous or prose, and ${count("added")} are blank although the format has the field. `
      + `The other ${crosswalk.length - needed.length} are for terms the format has no field for.`),
  );
}

async function start() {
  const response = await fetch("data.json", { cache: "no-cache" });
  const { coverage, unreviewed, upstream } = await response.json();
  document.getElementById("tag").textContent = coverage.codemeta_tag;
  document.getElementById("version").textContent = `codemeta-drift ${coverage.generator.version}`;
  score(coverage);
  matrix(coverage, unreviewed, detail(coverage, unreviewed, upstream));
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
