# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `codemeta-drift <checkout> [--ref REF] [--json]` lists where CodeMeta's context,
  definitions, property table, examples, crosswalks and `crosswalk.csv` disagree. Each check
  has a stable code. A malformed input file exits 2, so CI doesn't mistake it for drift.
- `--ref` reads any tag, branch or commit through one `git cat-file` call, about as fast as
  reading the working tree.
- Test fixtures: the files the checks read from CodeMeta 3.1 and 4.0, and the output for each.

[Unreleased]: https://github.com/simonvanlierde/codemeta-drift/commits/HEAD
