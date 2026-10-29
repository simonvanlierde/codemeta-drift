# codemeta-drift

[![python](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml/badge.svg)](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/simonvanlierde/codemeta-drift/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23774728.svg)](https://doi.org/10.5281/zenodo.23774728)

A small checker that finds the places where the CodeMeta standard's own files contradict
each other.

## Why this exists

[CodeMeta](https://codemeta.github.io) is a shared vocabulary for describing research
software: who wrote it, its licence, how to cite it, where the code lives. You put a
`codemeta.json` file next to your code, and archives such as Software Heritage can read it.

CodeMeta also publishes **crosswalks**: translation tables that say which field in another
format means the same thing. For example, a crosswalk says which field in a `CITATION.cff`
file, a PyPI package or a GitHub repository matches CodeMeta's `author` or `license`. There
are 46 of them, and tools use them to convert metadata from one format to another.

All of this lives in a handful of files that people edit by hand. When one file changes and
another doesn't, the translations go wrong without anyone noticing. A real example from
CodeMeta's main branch: the property list dropped `position` and put `maintainer` in its
place, but all 46 crosswalks still have a `position` row. If you lined them up by row number,
every format's "position" field would quietly turn into "maintainer".

codemeta-drift reads all those files and lists every place they disagree, so they can be
fixed before anyone converts metadata with them.

## Try it

Install it with [uv](https://docs.astral.sh/uv/) and point it at a copy of the CodeMeta
repository:

```sh
uv tool install codemeta-drift
git clone https://github.com/codemeta/codemeta
codemeta-drift codemeta              # check the files as they are
codemeta-drift codemeta --ref 4.0    # check any release, branch or commit instead
codemeta-drift codemeta --json       # the same, as JSON
```

Each line of output is one problem: what kind it is, the file, the term, and what's wrong.
For example:

```text
CROSSWALK_ROWS crosswalks/*.csv (all 46): position: line 44 is not in properties_description.csv; the table has maintainer there
EXAMPLE_NO_TERM examples/codemeta.json: softwareSuggestions: not a term of codemeta.jsonld
AGGREGATE_FORMAT crosswalk.csv: GitLab: no column for crosswalks/GitLab.csv
```

When everything agrees, it prints nothing. That makes it usable in CI, where the exit code
is what counts:

- 0: the files agree.
- 1: they don't.
- 2: it couldn't check: the vocabulary or the property list is missing, or a file can't be read.

`--json` prints one document: `{"version": 1, "tool": {"name", "version"}, "findings": [...]}`.
Each finding has a `code`, a `file`, a `term` and a `detail`. `code` and `term` are stable; `file`
is a label (it can name a group, such as `crosswalks/*.csv (all 46)`), and `detail` is text for a
person. A minor release may add keys; removing or retyping one bumps `version`. The command line,
the exit codes, the finding codes and the export format are the interface: the Python modules may
change in any 0.x release.

## What it found in CodeMeta (2026-10-13)

On CodeMeta's main branch (`e62eb75`):

- The property list has three terms (`encoding`, `fileFormat`, `softwareSuggestions`) that the
  vocabulary file doesn't define, and the vocabulary has three (`archivedAt`,
  `encodingFormat`, `featureList`) that the list leaves out.
- The main example uses `softwareSuggestions`, one of the undefined terms.
- The definitions file has a typo (`contiIntegration` for `contIntegration`) and still defines
  `embargoDate`, which the vocabulary doesn't have. The vocabulary only has `embargoEndDate`.
- `funding` and `maintainer` point to different addresses in the definitions and the
  vocabulary.
- Every crosswalk is missing the same 12 terms, and still has the old `position` row.
- The combined table that the website shows has no column for the GitLab and code.json
  crosswalks.

Number of problems per check, for the last two releases and the main branch:

| Check | 3.1 | 4.0 | main |
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
in [`tests/fixtures/`](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/fixtures/).

## The files it compares

| File | What it is |
| --- | --- |
| `codemeta.jsonld` | The vocabulary: every term and the web address that defines it |
| `codemeta_all.jsonld` | The definitions of CodeMeta's own terms (since 4.0) |
| `properties_description.csv` | The property list people read, one row per term |
| `codemeta.json`, `examples/*.json` | Example metadata that should only use defined terms |
| `crosswalks/*.csv` | One translation table per format, listing the same terms in the same order |
| `crosswalk.csv` | All crosswalks combined into one table, which the website shows |

## Every check

| Code | It reports |
| --- | --- |
| `TABLE_DUPLICATE` | A term listed twice under the same type in the property list |
| `TABLE_NO_TERM` | A term in the property list that the vocabulary doesn't define |
| `TERM_NO_ROW` | A term in the vocabulary that the property list leaves out |
| `TABLE_NAMESPACE` | A term the property list files under `schema:` but the vocabulary under `codemeta:`, or the other way round |
| `DEFINITION_NO_TERM` | A definition for a term the vocabulary doesn't have |
| `DEFINITION_IRI` | A term whose address differs between the definitions and the vocabulary |
| `EXAMPLE_NO_TERM` | An example that uses an undefined term |
| `CROSSWALK_ROWS` | A crosswalk whose terms don't match the property list |
| `CROSSWALK_FORMAT` | Two crosswalks for the same format |
| `AGGREGATE_ROWS` | The combined table's terms don't match the property list |
| `AGGREGATE_FORMAT` | A crosswalk missing from the combined table, or a column with no crosswalk |
| `SKIPPED` | A file this version doesn't have; the checks that need it don't run, and it doesn't count as a problem |

The crosswalk checks compare terms by name, never by position. A renamed term shows up as one
term that shouldn't be there and one that's missing. When all 46 crosswalks have the same
problem, it's reported once.

All the checks live in one file, [`checks.py`](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/checks.py). It needs
nothing beyond Python itself, so the CodeMeta repository could copy it into its own CI.

## Mapping export

A mapping export is a JSON file that says where each CodeMeta term sits in CFF, codemeta.json,
.zenodo.json, pyproject.toml, Cargo.toml and package.json, with wrong crosswalk cells corrected.
[docs/mapping-export.md](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/mapping-export.md) describes the format, and
[examples/mapping-3.1.json](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/mapping-3.1.json) is the one for CodeMeta 3.1.

```sh
codemeta-drift export codemeta --tag 3.1 --out mapping-3.1.json
```

A row reads its crosswalk cell when the cell is a path, such as `package.version`. Every other
row comes from [`curated-3.1.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/curated-3.1.json), which gives the path and
the reason: the cell is prose (`license / license-url`), empty, or wrong (`package.keyword`), or
the format has no crosswalk (PEP 621). A cell that is none of these is refused, not guessed:

```text
CELL_PROSE crosswalks/Citation File Format 1.2.0.csv: license: prose cell 'license / license-url', and no curated row
```

It then lists them on standard error, exits 1 and writes nothing. The rows are read from the tag's commit, not the working
tree, because each one says which tag it came from. A curated row records the cell it was written
for, and is reported as `CURATED_STALE` when that cell changes. Two terms whose paths are equal or
nested, such as Cargo's `name` cell `package.authors` beside `author`, are `PATH_SHARED`. Cells are matched to the property list by name, and a name
listed twice (`identifier` under Thing and under Person) by its order among the rows with that
name. Only tags with a curated file can be exported; for now that is 3.1. A checkout directory
named `export` needs a `./` in front.

`--schemas DIR` also checks every path against the format's own JSON Schema and reports
`PATH_NOT_IN_SCHEMA` for a key the schema doesn't have. The schemas for CFF 1.2.0, pyproject.toml,
package.json and Cargo.toml are in [`tests/fixtures/schemas/`](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/fixtures/schemas/), with
their sources. Zenodo has no current published schema for `.zenodo.json`, so its paths are not
checked. On the raw 3.1 crosswalk the check finds Cargo's `package.keyword`. It can't find a
path that exists but means something else, such as Zenodo's `identifier` cell `id`.

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

`just mutation`, which CI doesn't run, changes `checks.py`, `export.py` and `conformance.py` one small step at a time and fails if the tests
still pass on a change that `tests/mutation-baseline.txt` does not list. A change that
cannot alter behaviour goes in that file with the reason. It also fails on a listed
change the tests now catch, so the list stays true.

The tests run against real files from CodeMeta 3.1 and 4.0, copied byte for byte into
`tests/fixtures/`. The `.expected` files next to them hold the output the tool should give.
When you change the output on purpose, check the difference, then regenerate with
`uv run codemeta-drift tests/fixtures/<tag> > tests/fixtures/<tag>.expected` (it exits 1,
because both releases have problems).

## License

Apache-2.0, see [LICENSE](https://github.com/simonvanlierde/codemeta-drift/blob/main/LICENSE). The test fixtures are CodeMeta's own files, also
Apache-2.0; see [NOTICE](https://github.com/simonvanlierde/codemeta-drift/blob/main/NOTICE).
