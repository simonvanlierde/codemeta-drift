# Product

## Platform

web

## Stack

Static HTML, CSS and one JavaScript module. `site/build.py` copies them and writes `data.json` from the
mapping export, plus the HEAD of a CodeMeta clone when given one. GitHub Pages serves it at
<https://simonvanlierde.com/codemeta-drift/>, rebuilt on each push to main and every Monday.

## Users and purpose

Show CodeMeta maintainers and citation-tool authors which crosswalk cells work as written, which are
wrong, and which are missing, for the formats citation tools read. Each cell explains itself: CodeMeta's
text, the reviewed path and the reason. A second tab follows one field between two formats through its
CodeMeta term, and a third, checked weekly, says what changed on CodeMeta's main branch.

## Constraints

Read-only. No uploads, analytics, external hosts or stored state. The page shows the reviewed export
and the checker's findings only; it never proposes a mapping. A path that corresponds is not a value
that converts, and the copy says so.

## Accessibility

Each cell is a labelled button whose name carries its status, so the mark and colour are never the only
signal. Keyboard focus is visible, targets are 44 px, the format column stays visible while the matrix scrolls, filtered-out cells leave the tab order, and
light, dark and forced colours are covered.
