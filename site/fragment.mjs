// Reads the page's #fragment and ?tag, builds its outside links, and moves focus in the matrix. Kept free of the DOM so node --test can import it.

// The CodeMeta tag that ?tag= names, if data.json lists it; otherwise the newest, the last in tags.
// Only a listed tag picks a file to fetch.
export function chosenTag(search, tags) {
  const tag = new URLSearchParams(search).get("tag");
  return tags.includes(tag) ? tag : tags.at(-1);
}

// A release's link, relative so it stays on this origin even at a doubled-slash path: the newest is the page itself.
export function releaseHref(tag, tags) {
  return tag === tags.at(-1) ? "." : `?tag=${encodeURIComponent(tag)}`;
}

// The header's release links, each carrying the open view's fragment so that switching keeps the view.
export function releaseLinks(tags, shown, hash) {
  return tags.map((tag) => ({ tag, href: `${releaseHref(tag, tags)}${hash}`, current: tag === shown }));
}

export const pageTitle = (title, tag) => `${title} (CodeMeta ${tag})`;

// The SSSOM export's identifiers resolve here: #term/<term>, #field/<format>/<path> and #format/<format>,
// each percent-encoded as the export writes it. #route and #upstream open their tabs.
// Returns null for a fragment that selects nothing, including a malformed escape.
export function parseFragment(hash) {
  const [kind, ...rest] = hash.replace(/^#/, "").split("/");
  if (kind === "route" || kind === "upstream") return { tab: kind };
  let parts;
  try {
    parts = rest.map(decodeURIComponent);
  } catch {
    return null;
  }
  if (kind === "term") return { kind, term: parts[0] };
  if (kind === "format") return { kind, format: parts[0] };
  if (kind !== "field") return null;
  return { kind, format: parts[0], path: parts.slice(1).join("/") };
}

// codemeta.json is the hub and has no cells: a codemeta field id opens the term of its row, from the data file's
// path-to-term map. Undefined for any other target or a path with no row.
export function hubTerm(target, hub) {
  if (target.kind !== "field" || target.format !== "codemeta" || !Object.hasOwn(hub, target.path))
    return undefined;
  return hub[target.path];
}

// A reason split into text and {url} parts; a full stop, comma, colon or semicolon after a URL stays text.
export function linkParts(text) {
  return text.split(/(https?:\/\/[^\s)]+)/).flatMap((part, i) => {
    if (i % 2 === 0) return part ? [part] : [];
    const [, url, tail] = part.match(/^(.*?)([.,;:]?)$/);
    return tail ? [{ url }, tail] : [{ url }];
  });
}

// A crosswalk file at a CodeMeta tag, opened at one 1-based line.
export const sourceHref = (tag, path, line) =>
  `https://github.com/codemeta/codemeta/blob/${tag}/${path.split("/").map(encodeURIComponent).join("/")}?plain=1#L${line}`;

// Where a key moves focus in the matrix. rows holds one array per format row, true where a cell can take focus
// (a button not hidden by a filter); at is [row, column]. Up and down keep the column and pass over rows that
// have no cell there. Returns the new [row, column], or null when the key moves nowhere.
export function nextCell(rows, [r, c], key, ctrl = false) {
  const along = (row, from, step) => {
    for (let i = from; i >= 0 && i < row.length; i += step) if (row[i]) return i;
    return -1;
  };
  const down = (step) => {
    for (let i = r + step; i >= 0 && i < rows.length; i += step) if (rows[i][c]) return [i, c];
    return null;
  };
  const inRow = (i) => (i < 0 ? null : [r, i]);
  if (ctrl && (key === "Home" || key === "End")) {
    const order = key === "Home" ? rows.keys() : [...rows.keys()].reverse();
    for (const i of order) {
      const j = key === "Home" ? along(rows[i], 0, 1) : along(rows[i], rows[i].length - 1, -1);
      if (j >= 0) return [i, j];
    }
    return null;
  }
  if (key === "ArrowRight") return inRow(along(rows[r], c + 1, 1));
  if (key === "ArrowLeft") return inRow(along(rows[r], c - 1, -1));
  if (key === "Home") return inRow(along(rows[r], 0, 1));
  if (key === "End") return inRow(along(rows[r], rows[r].length - 1, -1));
  if (key === "ArrowDown") return down(1);
  if (key === "ArrowUp") return down(-1);
  return null;
}

export const crosswalkFormats = (cells) => new Set(cells.filter((c) => c.crosswalk).map((c) => c.format));

// The matrix's two format groups: those with a CodeMeta crosswalk, and those the reviewed mapping adds.
export function splitByCrosswalk(formats, cells) {
  const has = crosswalkFormats(cells);
  return { own: formats.filter((f) => has.has(f.format)), added: formats.filter((f) => !has.has(f.format)) };
}

// The upstream list: a line per cell with new text, then one per state and term for the cells with none,
// such as a property CodeMeta added to the table but not to the crosswalks.
export function upstreamLines(cells) {
  const lines = cells.filter((c) => c.now !== null).map(({ term, state, now, format }) => ({ term, state, now, formats: [format] }));
  const groups = new Map();
  for (const c of cells.filter((c) => c.now === null)) {
    const key = `${c.state} ${c.term}`;
    if (!groups.has(key)) groups.set(key, { term: c.term, state: c.state, now: null, formats: [] });
    groups.get(key).formats.push(c.format);
  }
  return [...lines, ...groups.values()];
}

// A key on a matrix cell. Arrows, Home and End move focus (see nextCell) and are taken from the browser;
// Alt+Arrow is its Back and Forward and Shift extends a selection, so those pass, and with Ctrl or Meta only
// Home and End act. cells holds one array per format row, each entry null or {open, focus()}, open false for a
// cell a filter hides; at is the [row, column] the key was pressed on.
export function matrixKey(event, cells, at) {
  if (!/^(Arrow(Up|Down|Left|Right)|Home|End)$/.test(event.key)) return;
  const ctrl = event.ctrlKey || event.metaKey;
  if (event.altKey || event.shiftKey || (ctrl && !/^(Home|End)$/.test(event.key))) return;
  event.preventDefault();
  const to = nextCell(cells.map((row) => row.map((c) => c?.open ?? false)), at, event.key, ctrl);
  if (to) cells[to[0]][to[1]].focus();
}

// The matrix's one tab stop: the current one (an index, -1 for none) while it is shown, else the first shown cell.
export const tabStop = (shown, current) => (current >= 0 && shown[current] ? current : shown.indexOf(true));

// The crosswalk cells a person had to judge: not 'no field', and not 'no term', which no crosswalk can have.
// The tally and the headline count these, for the base terms (a Set) only: citation columns have cells only where
// reviewed, so counting them would make the figures depend on which reviews exist.
export const needed = (cells, base) =>
  cells.filter((c) => base.has(c.term) && c.crosswalk && c.status !== "no field" && c.status !== "no term");

// The headline's figures, and its caption after the figure as [mark, words] pairs; the marks are for the eye only.
export function scoreCaption(cells, base) {
  const fields = needed(cells, base);
  const n = (status) => fields.filter((c) => c.status === status).length;
  return {
    asIs: n("as-is"),
    of: fields.length,
    formats: crosswalkFormats(cells).size,
    parts: [
      ["✎ ", `${n("corrected")} are wrong, ambiguous or prose, `],
      ["≈ ", `${n("notation")} need only a notation change, `],
      ["⊂ ", `${n("scope")} are right by CodeMeta's definition, but codemeta-drift reads the term more narrowly or also reads another field, and `],
      ["+ ", `${n("added")} are blank where the format has a field.`],
    ],
  };
}

// The detail panel's words for CodeMeta's cell, or null when the cell has text to show as code.
export function cellWords(cell) {
  if (!cell.crosswalk) return "no CodeMeta crosswalk for this format";
  if ((cell.cell ?? "").trim()) return null;
  if (cell.status === "no term") return "none: CodeMeta has no property for this term";
  return cell.cell === null ? "can't be matched to its property" : "empty";
}
