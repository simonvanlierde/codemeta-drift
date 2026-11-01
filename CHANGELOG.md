# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Ship `mapping-vectors.json` beside the mapping schema: test cases of path, document and the values the path
  resolves to, for a consumer to run through its own resolver. See the [mapping export](docs/mapping-export.md#path-grammar).

### Fixed

- The [schema watcher](docs/schema-watcher.md) now also opens a citesync issue when a hash in `MAPPING_SOURCE` differs from the file published at the pinned tag, and its run prints a notice when it skips publishing for lack of a token. The docs name the token permissions it needs.

## [0.5.0] - 2026-11-01

**Breaking:** SSSOM `term:`, `field:` and `format:` identifiers and the `mapping_set_id` have new URIs.
Regenerate stored SSSOM files with `codemeta-drift hub sssom` rather than joining them with 0.4.0 output.

Upgrade step: a consumer that validates the mapping export against a vendored schema vendors the 1.4 schema
with the new export, since R paths contain `@`. Readers that skip formats they don't use read it unchanged.
The `hub` commands of 0.4.0 and older refuse a 1.4 export, so upgrade codemeta-drift with the file.

### Added

- See every crosswalk cell for nine citation and package formats, and why a reviewed mapping changed it, in the
  [coverage matrix](docs/coverage.md) and on the [coverage page](https://simonvanlierde.com/codemeta-drift/).
  `codemeta-drift hub coverage` writes the matrix as Markdown or JSON. It also lists the CodeMeta crosswalks
  nobody has reviewed, each cell marked as a path, prose, empty or unmatched; `--codemeta <checkout>` adds them.
- The coverage page checks CodeMeta's main branch every Monday and lists the cells that changed since the pinned tag.
- The mapping export covers BibTeX, Python PKG-INFO, R DESCRIPTION and Julia `Project.toml`, each cell reviewed
  against CodeMeta's crosswalk. Its `schema_version` is 1.4, and a path key may now contain `@`, as in R's
  `Authors@R`. See the [mapping export](docs/mapping-export.md).

### Changed

- SSSOM exports carry mapping-set metadata (title, description, version, curator ORCID and provider), and their
  term, field and format identifiers resolve on the coverage page. See the [crosswalk hub](docs/crosswalk-hub.md).

## [0.4.0] - 2026-11-01

**Breaking:** Schema directories passed to `export --schemas` now also need `zenodo.json`.
Copy the [verified structural subset](tests/fixtures/schemas/zenodo.json) into your schema directory.
The new watcher uses the same five-file layout; see [Zenodo coverage and limits](docs/zenodo-schema.md).

### Added

- Run an [offline schema recovery example](docs/schema-recovery.md) with an explicit synthetic approval and reproducible mapping hashes.
- Check Zenodo mapping paths against a [verified structural subset](docs/zenodo-schema.md); importer source changes produce review drafts. This does not validate complete deposits.
- Find corresponding fields in two formats and export seven SSSOM spokes with the
  [crosswalk hub](docs/crosswalk-hub.md). The Go spoke relates a module path to the repository field.
- Preview broken schema paths, new fields and a behind mapping pin with the
  [offline schema watcher](docs/schema-watcher.md). It prints deduplicated issue drafts.
- Mapping exports include each original crosswalk cell alongside the exported path, so readers can show corrections and empty cells.
  See the [mapping export contract](docs/mapping-export.md).

### Changed

- The README now leads with checking and exporting. Finding codes, the dated findings report and contributor instructions have [dedicated guides](README.md#documentation).

### Fixed

- Missing Zenodo importer files produce review drafts instead of aborting unrelated schema and pin checks. See [Zenodo coverage](docs/zenodo-schema.md).
- The [recovery example](docs/schema-recovery.md) reports unreadable approvals and existing output directories as CLI errors without modifying existing files.
- Hub commands reject malformed original crosswalk cells, keeping [mapping validation](docs/mapping-export.md) consistent with the export contract.
- SSSOM exports use distinct field and format URI prefixes so reference readers can load them.
  See the [validation and compatibility guide](docs/sssom-compatibility.md).
- Schema conformance checks recognize [array references and tuple item schemas](docs/schema-watcher.md).
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

[Unreleased]: https://github.com/simonvanlierde/codemeta-drift/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/simonvanlierde/codemeta-drift/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/simonvanlierde/codemeta-drift/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/simonvanlierde/codemeta-drift/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/simonvanlierde/codemeta-drift/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/simonvanlierde/codemeta-drift/releases/tag/v0.1.0
