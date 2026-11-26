# codemeta-drift

[![PyPI](https://img.shields.io/pypi/v/codemeta-drift.svg)](https://pypi.org/project/codemeta-drift/)
[![Python versions](https://img.shields.io/pypi/pyversions/codemeta-drift.svg)](https://pypi.org/project/codemeta-drift/)
[![python](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml/badge.svg)](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/simonvanlierde/codemeta-drift/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23774728.svg)](https://doi.org/10.5281/zenodo.23774728)

Shows where CodeMeta's crosswalk cells for citation and package formats work as written and where they don't,
checks where its vocabulary, definitions, examples and crosswalks disagree, and exports
reviewed field mappings for citation tools such as
[citesync](https://github.com/simonvanlierde/citesync).

## Why this exists

[CodeMeta](https://codemeta.github.io) describes software metadata: authors, licences,
versions and repository URLs. Its **crosswalks** map fields in other formats to CodeMeta
terms. For example, the Citation File Format (CFF) uses `title` where CodeMeta uses `name`.

At CodeMeta commit `e62eb75`, line 46 of the property list changed from `position` to
`maintainer`, while the crosswalks kept `position`. Joining the tables by row number attaches a field to the wrong
term. codemeta-drift compares names and reports the mismatch.

It checks the CodeMeta standard's own files. To keep a project's `CITATION.cff`,
`codemeta.json` and package manifests in sync, use citesync.

## How the crosswalks hold up

At CodeMeta 4.0, the 36 crosswalks reviewed here, from CFF, Zenodo and DataCite to Maven, SPDX,
Wikidata and GitLab, have 648 cells, one for each of the 18 terms citation tools need. 212 are for terms the
format has no field for. Of the other 436, 123 can be used as written. 79 name the right field
in a form a tool can't use as a path, such as another case, no prefix or XPath. 42 are right by
CodeMeta's definition, but codemeta-drift reads the term more narrowly, such as `identifier` as the
software's DOI and `swhid` as a term of its own, or also reads another field, such as a fallback
or a newer one. 82 are wrong, ambiguous or prose (19 of them fill a term the format has no
field for), and 110 are blank although the format has the field. The matrix's 19th column, `resourceType`, has no CodeMeta property, so no
crosswalk has a cell for it. CodeMeta has no crosswalk for `pyproject.toml`, `typst.toml`, Quarto
extensions, RIS, EndNote, RO-Crate or Croissant at all.

The [coverage matrix](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-4.0.md)
shows every cell and the reason for each correction, and lists the other 10 crosswalks by the
shape of their cells, with the reason none is reviewed. The [web page](https://simonvanlierde.com/codemeta-drift/) also checks
CodeMeta's main branch each week. The
[3.1 matrix](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-3.1.md) has the earlier figures.

## Try it

You need Git and [uv](https://docs.astral.sh/uv/). Check a CodeMeta checkout:

```sh
git clone https://github.com/codemeta/codemeta
uvx codemeta-drift codemeta
uvx codemeta-drift codemeta --ref 4.0
```

The first check reads the working tree. `--ref` reads a release, branch or commit.
To install the command, run `uv tool install codemeta-drift`.

Each output line names the check, file, term and problem. The 4.0 check reports, for example:

```text
EXAMPLE_NO_TERM examples/codemeta.json: softwareSuggestions: not a term of codemeta.jsonld
```

Exit codes are **0** when the checked files agree, **1** when they disagree, **2** on a usage
error, **3** when the check cannot run and **130** when interrupted. A check with no findings
prints nothing. `SKIPPED` notices for optional files do not make it fail. Add `--json` for
structured output; the [checks guide](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/checks.md) lists the finding codes.

## Mapping export

Export the reviewed mappings for CodeMeta 4.0 (or `3.1`):

```sh
uvx codemeta-drift export codemeta --tag 4.0 --out mapping-4.0.json
```

The 4.0 export covers 44 formats, from CFF, Zenodo and `pyproject.toml` to DCAT 3, Wikidata,
RO-Crate, MODS and ISO 19115-1. It records the field path for each term, with a reason for each curated
correction. It does not convert field values. Only tags with curated mappings can be exported:
`3.1` and `4.0`.

The [mapping export guide](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/mapping-export.md)
lists the formats and holds the contract. The
[committed example](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/mapping-4.0.json)
shows the output.

## Documentation

The pages below are also a searchable site at <https://simonvanlierde.com/codemeta-drift/docs/>.

- [Crosswalk coverage matrix](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-4.0.md) (also [3.1](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-3.1.md)): every term and format, with the reason for each correction.
- [Offline schema recovery](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/schema-recovery.md): preview a synthetic rename, then approve it.
- [Zenodo path coverage](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/zenodo-schema.md): verified paths, upstream source checks and validation limits.
- [Checks](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/checks.md): findings and the JSON interface.
- [Findings](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/findings.md): the dated CodeMeta findings report.
- [Mapping export](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/mapping-export.md): the export contract and path validation against schemas.
- [Development](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/development.md): set-up and tests.

## Crosswalk hub

[`codemeta-drift hub`](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/crosswalk-hub.md) derives field correspondences between two formats
and writes SSSOM spokes for every format. Values still need each format's parser.

## Schema watcher

Compare downloaded schemas and prepare issue drafts with the
[schema watcher](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/schema-watcher.md). The weekly workflow polls public sources and
checks citesync's mapping pin. Publishing needs a token.

## Social card

[`docs/assets/og.png`](docs/assets/og.png) is the 1200x630 card shown when the coverage page or
the docs are shared. It is rendered from [`docs/og-card.html`](docs/og-card.html). Edit the HTML,
then run:

```sh
just og-card
```

`site/build.py` copies the card into the built page and adds the PNG's hash to the `og:image`
URL (`?v=`). `just og-card` writes the hash into `zensical.toml` for the docs; a test fails if
it is stale.

## Development

From a codemeta-drift checkout, with uv, [just](https://just.systems) and Node (its built-in test runner, no packages) installed:

```sh
uv sync
just check
```

The [development guide](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/development.md) covers hooks, fixture updates and mutation
testing. [CONTRIBUTING.md](https://github.com/simonvanlierde/codemeta-drift/blob/main/.github/CONTRIBUTING.md) has the commit and sign-off rules.

## License

[Apache-2.0](https://github.com/simonvanlierde/codemeta-drift/blob/main/LICENSE). The CodeMeta test fixtures use the same licence; see [NOTICE](https://github.com/simonvanlierde/codemeta-drift/blob/main/NOTICE).
