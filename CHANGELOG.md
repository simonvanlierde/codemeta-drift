# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `codemeta-drift <checkout> [--ref REF] [--json]` reports where CodeMeta's context,
  definitions, property table, examples, crosswalks and `crosswalk.csv` disagree, with a
  stable code per check. It exits 2, not 1, when an input file is malformed.
- The files the checks read from CodeMeta 3.1 and 4.0, with the tool's output for each, as
  test fixtures.

[Unreleased]: https://github.com/simonvanlierde/codemeta-drift/commits/HEAD
