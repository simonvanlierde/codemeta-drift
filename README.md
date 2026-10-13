# codemeta-drift

[![python](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml/badge.svg)](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Report where [CodeMeta](https://github.com/codemeta/codemeta)'s context, property definitions,
property table, examples and crosswalks disagree.

CodeMeta keeps one vocabulary in several files: `codemeta.jsonld` (the JSON-LD context),
`codemeta_all.jsonld` (the definitions), `properties_description.csv` (the property table),
`examples/`, the 46 per-format files in `crosswalks/`, and the generated `crosswalk.csv`.
CodeMeta's own CI catches some drift (crosswalks whose row count differs from the table, examples that fail a JSON-LD round trip), but
not whether the files name the same terms. This tool lists every place they don't.

## Usage

It is not on PyPI. Install it from GitHub with [uv](https://docs.astral.sh/uv/):

```sh
uv tool install git+https://github.com/simonvanlierde/codemeta-drift
git clone https://github.com/codemeta/codemeta
codemeta-drift codemeta              # the working tree
codemeta-drift codemeta --ref 4.0    # any tag, branch or commit; leaves the working tree alone
codemeta-drift codemeta --json       # one object per finding: code, file, term, detail
```

It prints one line per finding, or nothing (`[]` with `--json`) when the files agree. Line
numbers in a finding are lines of the file it names. It exits with:

- 0 when the files agree,
- 1 when they don't,
- 2 when it can't read the checkout, a file is malformed, or there is no `codemeta.jsonld`
  or `properties_description.csv` to compare.

## What it checks

| Code | Disagreement |
| --- | --- |
| `TABLE_DUPLICATE` | The same parent type and property on two rows of the property table |
| `TABLE_NO_TERM` | A property table row with no term in the context |
| `TERM_NO_ROW` | A context term with no property table row |
| `TABLE_NAMESPACE` | A row's parent type is `schema:` but the context maps the term to `codemeta:`, or the reverse |
| `DEFINITION_NO_TERM` | A definition whose label is not a context term |
| `DEFINITION_IRI` | A definition and the context give one term different IRIs |
| `EXAMPLE_NO_TERM` | A valid example uses a term the context does not define |
| `CROSSWALK_ROWS` | A crosswalk's property column differs from the table's (see below) |
| `CROSSWALK_FORMAT` | Two crosswalk files use one format name |
| `AGGREGATE_ROWS` | The same as `CROSSWALK_ROWS`, for the committed `crosswalk.csv` |
| `AGGREGATE_FORMAT` | A crosswalk file with no column in `crosswalk.csv`, or the reverse |
| `SKIPPED` | A file this release doesn't have, such as `codemeta_all.jsonld` before 4.0. Only the checks that need it skip. It doesn't count as drift |

The crosswalk checks match rows by name, not by position. A renamed row shows up as one stray
row and one missing row, never as a silent remap. When several crosswalks differ from the table
in the same way, the tool reports them once.

All the rules live in [`checks.py`](src/codemeta_drift/checks.py). It uses only the standard
library and imports nothing from this package, so the codemeta repository can copy it as is
and add a short runner for CI. Here, [`cli.py`](src/codemeta_drift/cli.py) is that runner.

## Drift at 3.1, 4.0 and master (2026-10-13)

Findings per check, from `codemeta-drift <clone> --ref <ref>`:

| Code | 3.1 (`9458ead`) | 4.0 (`3657b0f`) | master (`e62eb75`) |
| --- | --- | --- | --- |
| `TABLE_NO_TERM` | 0 | 4 | 3 |
| `TERM_NO_ROW` | 0 | 3 | 3 |
| `TABLE_NAMESPACE` | 0 | 2 | 2 |
| `DEFINITION_NO_TERM` | skipped | 2 | 2 |
| `DEFINITION_IRI` | skipped | 2 | 2 |
| `EXAMPLE_NO_TERM` | 0 | 1 | 1 |
| `CROSSWALK_ROWS` | 3 | 10 | 13 |
| `AGGREGATE_ROWS` | 2 | 12 | 15 |
| `AGGREGATE_FORMAT` | 0 | 2 | 2 |

On master:

- The property table has `encoding`, `fileFormat` and `softwareSuggestions`, which the
  context does not define. The context has `archivedAt`, `encodingFormat` and `featureList`,
  which have no row.
- `examples/codemeta.json` uses `softwareSuggestions`.
- `codemeta_all.jsonld` labels `codemeta:contIntegration` as `contiIntegration`, and still
  defines `embargoDate` next to `embargoEndDate`. The context has only `embargoEndDate`.
- `codemeta_all.jsonld` gives `funding` and `maintainer` `codemeta:` IRIs, but the context maps
  both to `schema:`.
- Every crosswalk misses the same 12 rows, and still has a `position` row where the table now
  has `maintainer`. So padding the crosswalks by row count would quietly map each format's
  `position` term to `maintainer`.
- `crosswalk.csv` has no GitLab or code.json column.

The full output for 3.1 and 4.0 is in [`tests/fixtures/`](tests/fixtures/).

## Development

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems) and
[prek](https://github.com/j178/prek).

```sh
uv sync
uv tool install prek   # once per machine
prek install           # git hooks
just check             # lint, types, tests and the dependency audit (needs network)
just hooks             # the YAML, Markdown, workflow and citation checks CI also runs
```

`tests/fixtures/3.1/` and `tests/fixtures/4.0/` hold the files the checks read, copied byte for
byte from those CodeMeta tags. The `.expected` files next to them pin the tool's output. When
you change the output on purpose, check the difference, then regenerate with
`uv run codemeta-drift tests/fixtures/<tag> > tests/fixtures/<tag>.expected`. It exits 1,
because both releases have drift.

## License

Apache-2.0, see [LICENSE](LICENSE). The fixtures are CodeMeta's own files, also Apache-2.0;
see [NOTICE](NOTICE).
