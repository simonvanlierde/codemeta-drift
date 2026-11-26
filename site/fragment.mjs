// Reads the page's #fragment and ?tag, and builds its outside links. Kept free of the DOM so node --test can import it.

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
