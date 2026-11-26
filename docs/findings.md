---
description: "A dated report of where CodeMeta's context, definitions, property table, examples and crosswalks disagreed in the checked snapshots."
---

# Findings in the checked CodeMeta snapshots

This is a dated report, not a live status page. The last column is CodeMeta commit
`e62eb75`, checked on 2026-10-13. To see what remains, with the [command installed](https://github.com/simonvanlierde/codemeta-drift/blob/main/README.md#try-it), check a current CodeMeta checkout:

```sh
codemeta-drift codemeta
```

## What the checker found

- The property list has three terms (`encoding`, `fileFormat`, `softwareSuggestions`) that the
  vocabulary file doesn't define, and the vocabulary has three (`archivedAt`,
  `encodingFormat`, `featureList`) that the list leaves out.
- The main example uses `softwareSuggestions`, one of the undefined terms.
- The definitions file has a typo (`contiIntegration` for `contIntegration`) and still defines
  `embargoDate`, which the vocabulary doesn't have. The vocabulary only has `embargoEndDate`.
- `funding` and `maintainer` point to different addresses in the definitions and the
  vocabulary.
- At `e62eb75`, every crosswalk is missing the same 12 terms and still has the old `position` row.
- The combined table that the website shows has no column for the GitLab and code.json
  crosswalks.

## Counts by snapshot

Counts are finding entries, not affected files. A finding shared by several crosswalks
counts once.

| Check | 3.1 | 4.0 | `e62eb75` |
| --- | --- | --- | --- |
| `TABLE_NO_TERM` | 0 | 4 | 3 |
| `TERM_NO_ROW` | 0 | 3 | 3 |
| `TABLE_NAMESPACE` | 0 | 2 | 2 |
| `DEFINITION_NO_TERM` | not checked | 2 | 2 |
| `DEFINITION_IRI` | not checked | 2 | 2 |
| `EXAMPLE_NO_TERM` | 0 | 1 | 1 |
| `CROSSWALK_ROWS` | 3 | 10 | 13 |
| `AGGREGATE_ROWS` | 2 | 12 | 15 |
| `AGGREGATE_FORMAT` | 0 | 2 | 2 |

3.1 has no definitions file, so those checks didn't run. The full output for 3.1 and 4.0 is
in [`tests/fixtures/`](https://github.com/simonvanlierde/codemeta-drift/tree/main/tests/fixtures/).

[Finding reference](checks.md) explains each code. The counts do not say which value is
right: a crosswalk correction belongs upstream in CodeMeta or in a reviewed
[curated mapping](mapping-export.md).
