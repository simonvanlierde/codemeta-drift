---
description: "Links to the crosswalk coverage matrix for each CodeMeta release, and to the web page that also checks CodeMeta's main branch."
---

# Crosswalk coverage

The coverage matrix has one page per CodeMeta tag:

- [CodeMeta 4.0](coverage-4.0.md)
- [CodeMeta 3.1](coverage-3.1.md)

The [web page](https://simonvanlierde.com/codemeta-drift/) shows the newest tag; `?tag=3.1` shows 3.1.

## What the counts cover

At CodeMeta 4.0:

- **Columns:** 13 terms plus 6 person sub-terms (`.givenName`, `.familyName` and `.@id` of
  `author` and `contributor`) make 19 columns. 18 have a CodeMeta property: `swhid` shares
  `identifier`'s row, and `resourceType` has none.
- **Crosswalks:** CodeMeta has 46. I reviewed 36. The page lists the other 10, with the reason.
- **Formats:** the export has 44. The page shows 43, because `codemeta.json` has no row. 7 of the
  43 have no CodeMeta crosswalk.
- **Cells:** the README's 648 are the 36 reviewed crosswalks times the 18 columns with a property.
  The page's status counts take in all 43 formats and 19 columns, 817 cells.
