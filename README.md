# codemeta-drift

[![PyPI](https://img.shields.io/pypi/v/codemeta-drift.svg)](https://pypi.org/project/codemeta-drift/)
[![Python versions](https://img.shields.io/pypi/pyversions/codemeta-drift.svg)](https://pypi.org/project/codemeta-drift/)
[![python](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml/badge.svg)](https://github.com/simonvanlierde/codemeta-drift/actions/workflows/python.yml)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/simonvanlierde/codemeta-drift/blob/main/LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23774728.svg)](https://doi.org/10.5281/zenodo.23774728)

codemeta-drift shows where CodeMeta's crosswalk cells for citation and package formats work as
written and where they don't: [see every cell](https://simonvanlierde.com/codemeta-drift/). It
also checks CodeMeta's own files against each other, and exports a reviewed JSON field mapping for
tools such as
[citesync](https://github.com/simonvanlierde/citesync).

codemeta-drift is not part of the CodeMeta project and proposes no edits to CodeMeta's files. Its
`identifier` column means the software's DOI, a narrower reading than CodeMeta's "any kind of
identifier", so a cell that holds a package id or a UUID counts as scope (right by CodeMeta's
definition, read more narrowly here), not as a CodeMeta error.

## Why this exists

[CodeMeta](https://codemeta.github.io) describes software metadata: authors, licences,
versions and repository URLs. Its **crosswalks** map fields in other formats to CodeMeta
terms. For example, the Citation File Format (CFF) uses `title` where CodeMeta uses `name`.

At CodeMeta commit `e62eb75`, line 46 of the property list changed from `position` to
`maintainer`, while the crosswalks kept `position`. Joining the tables by row number attaches a
field to the wrong term. codemeta-drift compares names and reports the mismatch.

It checks the CodeMeta standard's own files. To keep a project's `CITATION.cff`,
`codemeta.json` and package manifests in sync, use citesync.

## What it found

At CodeMeta 4.0 I reviewed 36 of its 46 crosswalks, from CFF, Zenodo and DataCite to Maven, SPDX,
Wikidata and GitLab, for the 18 terms citation tools need. That gives 648 cells, one per crosswalk
and term:

- 123 can be used as written.
- 79 name the right field in a form a tool can't use as a path, such as another case, no prefix
  or XPath.
- 42 are right by CodeMeta's definition, but codemeta-drift reads the term more narrowly, such as
  `identifier` as the software's DOI and `swhid` as a term of its own, or also reads another
  field, such as a fallback or a newer one. The reviewed mapping gives the path, or says the
  format has none.
- 82 are wrong, ambiguous or prose. 19 of them name a field the format doesn't have.
- 110 are blank although the format has the field.
- 212 are for a term the format has no field for.

The matrix has a 19th column, `resourceType`. It has no CodeMeta property, so no crosswalk has a
cell for it. CodeMeta has no crosswalk at all for `pyproject.toml`, `typst.toml`, Quarto
extensions, RIS, EndNote, RO-Crate or Croissant.

The [coverage page](https://simonvanlierde.com/codemeta-drift/) gives the reason for each
correction and checks CodeMeta's main branch each week. It also lists the 10 crosswalks I haven't
reviewed, and why. The same matrix is in Markdown for
[4.0](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-4.0.md) and
[3.1](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage-3.1.md).

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

A check with no findings prints nothing. The command exits 1 when the files disagree. The
[checks reference](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/checks.md)
lists the finding codes, the other exit codes and the `--json` output.

## Export the mapping

```sh
uvx codemeta-drift export codemeta --tag 4.0 --out mapping-4.0.json
```

The export gives the field path for each term in 44 formats, with the reason for each cell I
corrected by hand. It does not convert values. Only `3.1` and `4.0` have reviewed mappings. The
[mapping export guide](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/mapping-export.md)
holds the contract, and the
[committed example](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/mapping-4.0.json)
shows the output.

## Documentation

The pages below are also a searchable site at <https://simonvanlierde.com/codemeta-drift/docs/>.

- [Checks reference](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/checks.md): finding codes, exit codes and JSON output.
- [Findings](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/findings.md): what the checks found in earlier CodeMeta snapshots.
- [Coverage](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/coverage.md): the crosswalk matrix for each CodeMeta release.
- [Mapping export](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/mapping-export.md): the JSON contract consumers pin.
- [Crosswalk hub](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/crosswalk-hub.md): corresponding fields between two formats, and the SSSOM export.
- [SSSOM compatibility](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/sssom-compatibility.md): validating the SSSOM export and how it compares with CodeMeta's methodology.
- [Schema watcher](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/schema-watcher.md): previewing format schema changes, and [Zenodo path coverage](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/zenodo-schema.md).
- [Schema recovery](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/schema-recovery.md): an offline rename, from the first finding to a reviewed fix.
- [Development](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/development.md): tests, the site, the schema watcher's publishing and the social card.

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
