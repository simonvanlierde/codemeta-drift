// Reads the page's #fragment and ?tag. Kept free of the DOM so node --test can import it.

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
