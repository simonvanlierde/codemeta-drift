// Reads the page's #fragment. Kept free of the DOM so node --test can import it.
//
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
  const path = parts.slice(1).join("/");
  // codemeta.json is the hub and has no row: its field ids open the term's first cell instead.
  return { kind, format: parts[0], path, hubTerm: parts[0] === "codemeta" ? path.replaceAll("[]", "") : undefined };
}
