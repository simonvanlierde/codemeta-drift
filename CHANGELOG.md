# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- A `CELL_NO_AUTHOR` finding now says the author or contributor has no path, not no row, which was
  wrong when its curated row has a null path, as CFF's contributor row does.
- `export` refuses a crosswalk cell that already reads as a list, such as `authors[]`, with a `CELL_PATH` finding, instead of
  writing `authors[][]` and its sub-terms into the export.
- A check of the working tree skips a directory whose name matches an input file, such as `examples/x.json`, as
  `--ref` already did, instead of exiting 2.

## [0.3.0] - 2026-10-30

### Added

- The export maps `swhid`, the Software Heritage identifier: CFF `identifiers` of type `swh`,
  Zenodo `related_identifiers` with scheme `swh` (or no scheme and a `swh:1:` value), and
  codemeta.json `identifier`, which holds the DOI too. See [the term list](docs/mapping-export.md#the-file).
- The CFF `author.familyName` row's comment says to join `name-particle`, `family-names` and
  `name-suffix` into the family name, so a consumer keeps "van" in Antonie van Leeuwenhoek.

### Changed

- The export's `schema_version` is 1.2, since it adds a term. A reader of 1.0 or 1.1 reads it unchanged.

## [0.2.0] - 2026-10-30

### Added

- The export maps `datePublished` and `contributor`, with the same person sub-terms as
  `author`. CFF 1.2.0, Cargo.toml and pyproject.toml have no contributor list, so their rows are
  `null`; Zenodo's need a curated row, because its crosswalk cells are empty.

### Changed

- The export's `schema_version` is 1.1, since it adds terms. A reader of 1.0 reads it unchanged.
- A consumer now needs rows only for the terms it uses, not for every term in the export.

## [0.1.0] - 2026-10-29

### Added

- `codemeta-drift <checkout> [--ref REF] [--json]` lists where CodeMeta's context,
  definitions, property table, examples, crosswalks and `crosswalk.csv` disagree. Each check
  has a stable code. A malformed input file exits 2, so CI doesn't mistake it for drift.
- `--json` prints one versioned document holding the findings, and `--version` prints the installed version.
- `--ref` reads any tag, branch or commit through one `git cat-file` call, about as fast as
  reading the working tree.
- The mapping export format: a JSON Schema for `mapping-<codemeta-tag>.json`, which says where
  each CodeMeta term sits in six metadata formats, and the export for CodeMeta 3.1.
- `codemeta-drift export [checkout] --tag TAG [--out FILE]` writes the export from the tag's
  commit. Rows read the crosswalk cell when it is a path, and come from a curated file with a
  reason when it is prose, empty or wrong. A cell with neither is listed and the command exits 1,
  as is a curated row whose cell has changed, and two terms whose paths overlap.
- `export --schemas DIR` checks every path against the format's own JSON Schema (CFF 1.2.0,
  pyproject.toml, package.json, Cargo.toml) and reports `PATH_NOT_IN_SCHEMA`.
- Test fixtures: the files the checks read from CodeMeta 3.1 and 4.0, and the output for each,
  and the JSON Schemas of four formats. `tests/fixtures/3.1.sha256` ties the 3.1 files to the
  tag's commit.

[Unreleased]: https://github.com/simonvanlierde/codemeta-drift/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/simonvanlierde/codemeta-drift/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/simonvanlierde/codemeta-drift/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/simonvanlierde/codemeta-drift/releases/tag/v0.1.0
