// Draws the coverage matrix, the route between two formats and the upstream check from data.json.
// Every string goes in through textContent: cells and reasons come from crosswalk files.

const LABELS = { "cff-1.2.0": "CFF 1.2.0", zenodo: "Zenodo", pep621: "pyproject.toml", cargo: "Cargo", npm: "npm" };
const label = (fmt) => LABELS[fmt] ?? fmt;

// What each upstream state says about a cell on CodeMeta's main branch.
const STATES = {
  missing: "has no crosswalk file on main",
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

// A path may wrap only after a dot, a bracket or an alternative's bar, never inside a key.
function breakable(path) {
  const span = el("span", { class: "path" });
  for (const part of path.split(/(?<=[.\]|=])|(?=\[)/)) span.append(part, el("wbr"));
  return span;
}

function matrix(data, onPick) {
  const table = document.getElementById("matrix");
  const head = el("tr", {}, el("th", { scope: "col" }, "Term"));
  for (const fmt of data.formats) head.append(el("th", { scope: "col" }, label(fmt)));
  table.append(el("thead", {}, head));
  const body = el("tbody");
  const byKey = new Map(data.cells.map((c) => [`${c.format} ${c.term}`, c]));
  for (const term of data.terms) {
    const row = el("tr", {}, el("th", { scope: "row" }, code(term)));
    for (const fmt of data.formats) {
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
          cell.path ? breakable(cell.path) : null,
        );
        button.addEventListener("click", () => onPick(cell, button));
        td.append(button);
      }
      row.append(td);
    }
    body.append(row);
  }
  table.append(body);
}

function detail(data, upstream) {
  const box = document.getElementById("detail");
  const hint = box.firstElementChild;
  const changes = new Map((upstream?.cells ?? []).map((c) => [`${c.format} ${c.term}`, c]));
  let picked = null;
  return (cell, button) => {
    picked?.removeAttribute("aria-pressed");
    button.setAttribute("aria-pressed", "true");
    picked = button;
    const was = (cell.cell ?? "").trim();
    const rows = [
      ["Status", `${data.statuses[cell.status].mark} ${cell.status}: ${data.statuses[cell.status].meaning}`],
      ["CodeMeta's cell", cell.crosswalk ? (was ? code(was) : "empty") : "no CodeMeta crosswalk for this format"],
      ["Path used", cell.path ? code(cell.path) : "none"],
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
      button.focus();
    });
    box.replaceChildren(el("div", { class: "detail-head" }, el("h3", {}, code(cell.term), ` in ${label(cell.format)}`), close), list);
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
      for (const td of table.querySelectorAll("tbody td")) {
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
  for (const select of [from, to]) for (const fmt of data.formats) select.append(el("option", { value: fmt }, label(fmt)));
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
  document.getElementById("upstream").hidden = false;
  const date = upstream.date.slice(0, 10);
  document.getElementById("checked").textContent = `upstream main checked ${date} at ${upstream.commit.slice(0, 7)}`;
  const intro = document.getElementById("upstream-intro");
  intro.append(`Commit `, el("a", { href: `https://github.com/codemeta/codemeta/commit/${upstream.commit}` },
    upstream.commit.slice(0, 7)), ` from ${date}. `,
    upstream.cells.length ? `${upstream.cells.length} of the cells above read differently there than at ${tag}:`
      : `Every cell above reads the same there as at ${tag}.`);
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

// The SSSOM export's identifiers resolve here: #term/<term>, #field/<format>/<path> and #format/<format>,
// each percent-encoded as the export writes it. The first matching cell is chosen and scrolled to.
function follow() {
  const [kind, ...rest] = location.hash.slice(1).split("/");
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
  // codemeta.json is the hub and has no column: its field ids open the term's row instead.
  const hub = kind === "field" && parts[0] === "codemeta" && ((b) => b.dataset.term === parts.slice(1).join("/").replaceAll("[]", ""));
  const button = cells.find(match) ?? (hub ? cells.find(hub) : undefined);
  if (!button) return;
  button.click();
  button.scrollIntoView({ block: "center" });
  button.focus({ preventScroll: true });
}

async function start() {
  const response = await fetch("data.json", { cache: "no-cache" });
  const { coverage, upstream } = await response.json();
  document.getElementById("tag").textContent = coverage.codemeta_tag;
  document.getElementById("version").textContent = `codemeta-drift ${coverage.generator.version}`;
  const crosswalk = coverage.cells.filter((c) => c.crosswalk);
  const needed = crosswalk.filter((c) => c.status !== "no field");
  const asIs = needed.filter((c) => c.status === "as-is").length;
  document.getElementById("lede").append(" ", el("strong", {},
    `Of the ${crosswalk.length} cells in CodeMeta's own crosswalks, ${crosswalk.length - needed.length} are rightly empty; only ${asIs} of the other ${needed.length} can be used as written.`));
  matrix(coverage, detail(coverage, upstream));
  filters(coverage);
  route(coverage);
  upstreamSection(upstream, coverage.codemeta_tag);
  follow();
  window.addEventListener("hashchange", follow);
}

start().catch((err) => {
  document.getElementById("detail").replaceChildren(el("p", { class: "note" }, `Could not load data.json: ${err.message}`));
});
