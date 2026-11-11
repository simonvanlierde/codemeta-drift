# codemeta-drift

[![PyPI](https://img.shields.io/pypi/v/codemeta-drift.svg)](https://pypi.org/project/codemeta-drift/)
[![Python versions](https://img.shields.io/pypi/pyversions/codemeta-drift.svg)](https://pypi.org/project/codemeta-drift/)
[![python](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml/badge.svg)](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/simonvanlierde/codemeta-drift/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23774728.svg)](https://doi.org/10.5281/zenodo.23774728)

Show where CodeMeta's crosswalks to citation and package formats are wrong or missing,
check where its vocabulary, definitions, examples and crosswalks disagree, and export
reviewed field mappings for citation tools such as
[citesync](https://github.com/simonvanlierde/citesync).

## Why this exists

[CodeMeta](https://codemeta.github.io) describes software metadata: authors, licences,
versions and repository URLs. Its **crosswalks** map fields in other formats to CodeMeta
terms. For example, the Citation File Format (CFF) uses `title` where CodeMeta uses `name`.

These files need to agree. In one checked snapshot, the property list replaced `position`
with `maintainer`, while the crosswalks kept `position`. Joining the tables by row number
would attach a field to the wrong term. codemeta-drift compares names and reports the mismatch.

Use it to check the CodeMeta standard's own files. To keep a project's `CITATION.cff`,
`codemeta.json` and package manifests in sync, use citesync.

## How the crosswalks hold up

At CodeMeta 4.0, the 30 crosswalks reviewed here, from CFF, Zenodo and DataCite to Maven, SPDX,
Wikidata and GitLab, have 540 cells for the 18 terms citation tools need. 189 are for terms the format has no field for. Of the other 351, only 120 can be used as written: 140 are wrong,
ambiguous or prose (30 of them fill a term the format has no field for), and 91 are blank although the format
has the field. The 19th term, `resourceType`, has no CodeMeta property, so no crosswalk can have its cell.
CodeMeta has no crosswalk for `pyproject.toml`, `typst.toml`, Quarto extensions, RIS, EndNote, RO-Crate or Croissant at all. The [coverage matrix](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-4.0.md)
shows every cell and the reason for each correction, lists the other 16 crosswalks by the shape
of their cells, and the
[web page](https://simonvanlierde.com/codemeta-drift/) also checks CodeMeta's main branch each week.
The [3.1 matrix](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-3.1.md) preserves the earlier figures.

## Try it

You need Git and [uv](https://docs.astral.sh/uv/). Check a CodeMeta checkout:

```sh
git clone https://github.com/codemeta/codemeta
uvx codemeta-drift codemeta
uvx codemeta-drift codemeta --ref 4.0
```

The first check reads the working tree. `--ref` reads a release, branch or commit.
To install the command for repeated use, run `uv tool install codemeta-drift`.

Each output line names the check, file, term and problem. For example, the 4.0 check reports:

```text
EXAMPLE_NO_TERM examples/codemeta.json: softwareSuggestions: not a term of codemeta.jsonld
```

Exit codes are **0** when the checked files agree, **1** when they disagree, **2** on a usage
error, **3** when the check cannot run and **130** when interrupted. A check with no findings prints nothing; `SKIPPED` notices
for optional files do not make it fail. Add `--json` for structured output.
See [finding codes, compared files and JSON output](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/checks.md).

## Mapping export

Export the reviewed mappings for CodeMeta 4.0 (or `3.1`):

```sh
uvx codemeta-drift export codemeta --tag 4.0 --out mapping-4.0.json
```

The 4.0 export covers 38 formats, from CFF, Zenodo and `pyproject.toml` to DCAT 3, Wikidata, RO-Crate and Croissant; the
[mapping export](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/mapping-export.md) lists them.
It records the field path for each term, with a reason for each curated correction.
It does not convert field values.
The exporter reads the tag's commit and refuses rows it cannot resolve.

Read the [export guide and contract](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/mapping-export.md), or inspect the
[committed example](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/mapping-4.0.json). Only tags with curated mappings can be
exported; currently those are `3.1` and `4.0`.

## Documentation

- [Crosswalk coverage matrix](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-4.0.md) (also [3.1](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-3.1.md)): every term and format, with the reason for each correction.
- [Offline schema recovery](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/schema-recovery.md): preview a synthetic rename and apply an explicit approval.
- [Zenodo path coverage](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/zenodo-schema.md): verified paths, upstream source checks and validation limits.
- [Understand findings and use the JSON interface](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/checks.md).
- [Inspect the dated CodeMeta findings report](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/findings.md).
- [Export mappings and validate paths against schemas](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/mapping-export.md).
- [Set up development and run tests](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/development.md).

## Crosswalk hub

Derive field correspondences between two formats or write SSSOM spokes for every format with
[`codemeta-drift hub`](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/crosswalk-hub.md). Values still need each format's parser and normalization.

## Schema watcher

Compare downloaded schemas and prepare issue drafts with the
[schema watcher](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/schema-watcher.md). The weekly workflow polls public sources and
also checks citesync's mapping pin. Publishing requires a configured token.

## Social card

[`site/og.png`](site/og.png) is the 1200x630 card shown when the link is shared. It is rendered from
[`docs/og-card.html`](docs/og-card.html), which draws the page's coverage matrix for CodeMeta 4.0 at full size: ten
formats by 19 terms, with the wrong crosswalk cells filled and the missing ones outlined. Edit the HTML, then run:

```sh
just og-card
```

`site/build.py` copies the card into the built page; the tags are in `site/index.html`. `just og-card` also writes the PNG's hash into the `og:image` URL (`?v=`), because link previews are cached by image URL; a test fails if they differ.

## Development

From a codemeta-drift checkout, with uv, [just](https://just.systems) and Node (its built-in test runner, no packages) installed:

```sh
uv sync
just check
```

The [development guide](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/development.md) covers hooks, fixture updates and mutation
testing. [CONTRIBUTING.md](https://github.com/simonvanlierde/codemeta-drift/blob/main/.github/CONTRIBUTING.md) gives the commit and sign-off rules.

## License

[Apache-2.0](https://github.com/simonvanlierde/codemeta-drift/blob/main/LICENSE). The CodeMeta test fixtures use the same licence; see [NOTICE](https://github.com/simonvanlierde/codemeta-drift/blob/main/NOTICE).
