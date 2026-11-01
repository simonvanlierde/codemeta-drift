# codemeta-drift

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

At CodeMeta 3.1, the crosswalks for CFF, Zenodo, BibTeX, Python PKG-INFO, Cargo, npm,
R DESCRIPTION and Julia's Project.toml have 136 cells for the 17 terms citation tools need.
37 are for terms the format has no field for. Of the other 99, only 41 can be used as written:
32 are wrong, ambiguous or prose (7 of them name a field the format doesn't have), and 26 are
blank although the format has the field.
CodeMeta has no crosswalk for `pyproject.toml` at all. The [coverage matrix](docs/coverage.md)
shows every cell and the reason for each correction, lists the other 36 crosswalks by the shape
of their cells, and the
[web page](https://simonvanlierde.com/codemeta-drift/) also checks CodeMeta's main branch each week.

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

Exit codes are **0** when the checked files agree, **1** when they disagree, and **2**
when the check cannot run. A check with no findings prints nothing; `SKIPPED` notices
for optional files do not make it fail. Add `--json` for structured output.
See [finding codes, compared files and JSON output](docs/checks.md).

## Mapping export

Export the reviewed mappings for CodeMeta 3.1:

```sh
uvx codemeta-drift export codemeta --tag 3.1 --out mapping-3.1.json
```

The export covers CFF, CodeMeta, Zenodo, BibTeX, Python (`pyproject.toml` and PKG-INFO), Cargo, npm, R (DESCRIPTION) and Julia (`Project.toml`) metadata.
It records the field path for each term, with a reason for each curated correction.
It does not convert field values.
The exporter reads the tag's commit and refuses rows it cannot resolve.

Read the [export guide and contract](docs/mapping-export.md), or inspect the
[committed example](examples/mapping-3.1.json). Only tags with curated mappings can be
exported; currently that is `3.1`.

## Documentation

- [Crosswalk coverage matrix](docs/coverage.md): every term and format, with the reason for each correction.
- [Offline schema recovery](docs/schema-recovery.md): preview a synthetic rename and apply an explicit approval.
- [Zenodo path coverage](docs/zenodo-schema.md): verified paths, upstream source checks and validation limits.
- [Understand findings and use the JSON interface](docs/checks.md).
- [Inspect the dated CodeMeta findings report](docs/findings.md).
- [Export mappings and validate paths against schemas](docs/mapping-export.md).
- [Set up development and run tests](docs/development.md).

## Crosswalk hub

Derive field correspondences between two formats or write SSSOM spokes for every format with
[`codemeta-drift hub`](docs/crosswalk-hub.md). Values still need each format's parser and normalization.

## Schema watcher

Compare downloaded schemas and prepare issue drafts with the
[schema watcher](docs/schema-watcher.md). The weekly workflow polls public sources and
also checks citesync's mapping pin. Publishing requires a configured token.

## Development

From a codemeta-drift checkout, with uv and [just](https://just.systems) installed:

```sh
uv sync
just check
```

The [development guide](docs/development.md) covers hooks, fixture updates and mutation
testing. [CONTRIBUTING.md](.github/CONTRIBUTING.md) gives the commit and sign-off rules.

## License

[Apache-2.0](LICENSE). The CodeMeta test fixtures use the same licence; see [NOTICE](NOTICE).
