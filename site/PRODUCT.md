# Product

This file describes the web page in `site/`, not codemeta-drift as a whole. What the mapping
export holds is in [docs/mapping-export.md](../docs/mapping-export.md).

## Platform

web

## Stack

Static HTML, CSS and ES modules, no framework and no runtime dependencies. GitHub Pages serves it
at <https://simonvanlierde.com/codemeta-drift/>. `.github/workflows/pages.yml` builds it every
Monday and on each release: it clones CodeMeta's main, runs `codemeta-drift --json` on it, and
copies that report and the released mapping export beside the page. A failed run leaves the last
page up.

## Core message

CodeMeta's own files disagree with each other, and the page shows where, checked against today's
CodeMeta. Under that, it shows how codemeta-drift corrects the crosswalks in the mapping it
exports.

## Users

- **CodeMeta maintainers and contributors**, and anyone deciding whether to trust a crosswalk.
  They want to see what is out of step, why it matters, and the line to fix on GitHub.
- **citesync users and research software maintainers** who followed a link from citesync's
  docs or playground to "why is this key different from the crosswalk?".

Looking up where a field goes in each metadata file, with editable values, is the citesync
playground's job, not this page's. This page links there.

## Product Purpose

1. **Headline:** "CodeMeta's own files disagree in N places", with the date checked and
   CodeMeta's commit.
2. **Findings:** four or five groups in plain words, such as "a crosswalk skips a property, so
   the rows after it shift" or "a term exists in one file but not the other". Each group has a
   one-line reason it matters, one worked example (the `position` to `maintainer` shift in the
   README), and its full list folded, each line linking to the file on GitHub.
3. **The fixes:** each crosswalk cell codemeta-drift corrects, as "CodeMeta says X, it should be
   Y, because Z", and the gaps it fills.
4. **Reference table:** plain field names down the side, the six files across, one mark on a
   corrected cell, a row anchor per field for citesync to link to, and a link to download the
   JSON.

A visit succeeds when the visitor understands that the crosswalks have drifted, sees one
concrete case, and knows where to fix it or which mapping to trust.

## Positioning

The official crosswalks are CSV files people edit by hand. This page is the only place that
checks them against each other on a schedule and says, in plain words, where they disagree today.

## Operating Context

- On 2026-10-31 the checker found 43 findings on CodeMeta's main: 28 rows out of step (13
  crosswalk, 15 aggregate), 6 terms in one file but not another, and 9 others (namespace, IRI,
  example and format mismatches).
- The 3.1 export: 17 terms, 6 formats, 102 rows. 12 cells correct a wrong crosswalk cell, 13 fill
  a gap, 25 have no field in their format; the rest are codemeta.json's own terms or the
  pyproject.toml rows, which have no crosswalk upstream.
- The export holds the corrected key and the reason, not the crosswalk's original cell; showing
  "CodeMeta says X" from data needs a `crosswalk_cell` field in the export (a schema minor).
- The export's `schema_version` is 1.x; a newer major must show an error, not a wrong table.
- Related tools: [citesync](https://github.com/simonvanlierde/citesync) and
  [credit-matrix](https://github.com/simonvanlierde/credit-matrix). Link them where they help the
  visitor's next step.

## Capabilities and Constraints

- No network access but the page's own files; nothing stored, no cookies.
- The reference table scrolls sideways on a phone, with the field column pinned.

## Brand Commitments

- Name: codemeta-drift, in lower case.
- Voice: plain, short sentences, as in the README.
- Shares jsonvet's general opinions (a quiet tool page where the content carries it, plain
  static files, no invented claims), but has its own look, not jsonvet's stylesheet.

## Evidence on Hand

- The checker's JSON report on CodeMeta's main, and the mapping export with its reasons.
- No testimonials, user counts or quotes exist; none may be invented.

## Product Principles

1. Lead with what is wrong upstream, in plain words.
2. Every finding and every fix links to the line it is about.
3. What the page says is what the checker and the export say.
4. Works from a keyboard, on a phone, in light or dark, and in forced colours.
