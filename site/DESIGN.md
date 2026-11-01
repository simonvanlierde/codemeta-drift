# Design

A surveyor's coverage sheet. Product context is in [PRODUCT.md](PRODUCT.md); [style.css](style.css) is
the source of truth for values.

- **Paper and ink, one ochre.** Ochre marks only what a crosswalk gets wrong (a strong wash) or leaves out
  (a light wash). Cells that work stay ink; a format with no field is a faint dash. No second accent.
- **Marks and words, not colour alone.** ✓ as-is, ✎ corrected, + added, – no field. The legend doubles as
  the filter, with counts.
- **Type.** Serif system stack for prose, mono for every path, term and check code. System fonts only:
  the CSP allows nothing but the page's own files.
- **Flat.** Hairlines and one dashed rule under the slug. No shadows, rounded corners or boxes beyond the
  table's own border. The selected cell gets a 2px ink inset.
- **Matrix.** Terms down, formats across. Paths wrap only after `.`, `]`, `=` or `|`, or before `[`.
  The detail panel sits beside the table from 1000px, below it on smaller screens.
- **Route.** Three columns: the source path, the CodeMeta term in a box, the target path, joined by short
  rules. A missing end is italic ochre with a dashed rule. On a phone the three stack.
- **Copy.** Plain and specific. Upstream state names the commit and date it was read from.

Don't add inline script or style, another host, or a mark whose meaning lives only in colour.

The SSSOM export's identifiers resolve on this page: `#term/<term>`, `#field/<format>/<path>` and
`#format/<format>` choose the first matching cell and scroll to it.
