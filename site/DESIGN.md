# Design

A proofreader's pass over the crosswalks: the sheet is paper and ink, and a red pen marks what the crosswalk got wrong or left out. Product context is in [PRODUCT.md](PRODUCT.md); [style.css](style.css) is
the source of truth for values.

- **Paper and ink, one red.** Warm paper `#fbf9f6`, ink `#211f24`, faint `#5c5a60`. Red (`--mark`, `#b3261e`) marks only
  what a crosswalk gets wrong (a strong wash) or leaves out (a light wash). Cells that work stay ink; a format with
  no field is a faint dash. Dark mode keeps the roles on a near-black paper with a lighter red (`#ff948b`).
- **Navy is for links.** `--link` (`#2f4b7c`, `#9fb9ec` in dark mode) colours the text links and the card's dashed rule, and
  nothing else: it never marks a cell, a state or a filter. The tabs, filters and releases stay ink.
- **Contrast.** Every text pair clears AA: ink 15.5:1, faint 6.5:1, red 6.2:1 on paper and 5.0:1 on its strong
  wash, navy 8.3:1 (dark mode: red 8.3:1 and 6.4:1, light navy 8.9:1).
- **Marks and words, not colour alone.** ✓ as-is, ✎ corrected, + added, – no field. The legend doubles as
  the filter, with counts.
- **Type.** Newsreader for prose and JetBrains Mono for every path, term and check code, both OFL and self-hosted as
  latin woff2 in `fonts/` (Newsreader 400 and italic; JetBrains Mono 400 and 700), with the licence texts beside them. The CSP
  allows only the page's own files, so no font host. Fallbacks are the system serif and mono stacks.
- **Flat.** Hairlines and one dashed rule under the slug. No shadows, rounded corners or boxes beyond the
  table's own border. The selected cell gets a 2px ink inset.
- **Releases.** Beside the slug's title sits one link per CodeMeta release with a reviewed export, styled like the
  filters, the shown one tinted with an ink bar. The newest is the bare page; an older one is `?tag=<tag>`, and a
  link keeps the open view's fragment. Upstream is shown with the newest release only.
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
  shape, so prose and unmatched are red text and the rest faint. Their last column counts path cells.
  A "Skip past the matrix" link shows on focus, since every cell is a tab stop.
- **Route.** Three columns: the source path, the CodeMeta term in a box, the target path, joined by short
  rules. A missing end is italic red with a dashed rule. On a phone the three stack.
- **Copy.** Plain and specific. Upstream state names the commit and date it was read from.

Don't add inline script or style, another host, or a mark whose meaning lives only in colour.

The SSSOM export's identifiers resolve on this page: `#term/<term>`, `#field/<format>/<path>` and
`#format/<format>` choose the first matching cell and scroll to it. codemeta.json has no row, so
its field ids open the first cell of their row's term; the Go spoke's one id has no cell. Below 1280px the detail panel
sticks to the foot of the screen. The format column stays put at every width.
