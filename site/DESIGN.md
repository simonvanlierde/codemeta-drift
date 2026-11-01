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
- **Tabs.** Three views under the headline: Matrix (the default), Follow a field, and Upstream (CodeMeta's main branch)
  with the count of changed cells. One hairline row; the chosen tab is tinted with a 2px ink bar at its
  foot, like the chosen filter. `#route` and `#upstream` open their views; the SSSOM fragments open Matrix.
- **Headline.** Beside the intro from 1000px: the count of crosswalk cells usable as written, a bar of
  as-is, corrected and added in the cells' own colours, and one caption. It stacks below on smaller screens.
- **Matrix.** Formats down, citation files first, then package manifests; terms across, their names
  running up the column. A cell holds only its mark; its path is in the detail panel. The last column
  counts the format's usable cells. The detail panel sits beside the table from 1280px, below it on
  smaller screens.
- **Not reviewed.** The other crosswalks follow the reviewed rows under an italic group label that
  carries their legend: • path, ¶ prose, ○ empty, ? unmatched. No wash: a mark says only the cell's
  shape, so prose and unmatched are ochre text and the rest faint. Their last column counts path cells.
- **Route.** Three columns: the source path, the CodeMeta term in a box, the target path, joined by short
  rules. A missing end is italic ochre with a dashed rule. On a phone the three stack.
- **Copy.** Plain and specific. Upstream state names the commit and date it was read from.

Don't add inline script or style, another host, or a mark whose meaning lives only in colour.

The SSSOM export's identifiers resolve on this page: `#term/<term>`, `#field/<format>/<path>` and
`#format/<format>` choose the first matching cell and scroll to it. codemeta.json has no row, so
its field ids open the term's first cell; the Go spoke's one id has no cell. Below 1280px the detail panel
sticks to the foot of the screen. The format column stays put at every width.
