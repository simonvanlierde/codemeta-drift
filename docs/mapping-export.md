---
description: "The JSON mapping export: how to write it, the contract and schema, how to pin it, and what a consumer checks."
---

# Mapping export

A mapping export is one JSON file, `mapping-<codemeta-tag>.json`, that says where each CodeMeta term
sits in each metadata format. [citesync](https://github.com/simonvanlierde/citesync) reads it to
keep `CITATION.cff`, `codemeta.json`, `.zenodo.json` and package manifests in step.

The schema is [`src/codemeta_drift/mapping.schema.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/mapping.schema.json)
(JSON Schema 2020-12). [`examples/mapping-3.1.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/mapping-3.1.json)
and [`examples/mapping-4.0.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/mapping-4.0.json)
are the exports for CodeMeta 3.1 and 4.0.

## Export a mapping

Install with `uv tool install codemeta-drift`. The command needs a CodeMeta checkout that has the
tag, as in the [quick start](https://github.com/simonvanlierde/codemeta-drift/blob/main/README.md#try-it):

```sh
codemeta-drift export codemeta --tag 4.0 --out mapping-4.0.json
```

The exporter reads the tag's commit, not the working tree. Only `3.1` and `4.0` have curated files.
Write a directory named `export` as `./export`, so the CLI does not read it as the subcommand.

A path-shaped crosswalk cell, such as `package.version`, supplies the mapping directly. Other rows
come from `curated-<tag>.json`
([3.1](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/curated-3.1.json),
[4.0](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/curated-4.0.json)).
Citation rows shared by both exports come from
[`citation-crosswalks.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/citation-crosswalks.json).
A row whose cell is not wrong may also set `kind`: `notation` when the cell names the right field
in a form a tool can't use as a path, `scope` when it is right by CodeMeta's definition but the
path reads the term more narrowly or also reads another field. A row without `kind` counts as
corrected. The export copies it onto the row, and only `hub coverage` reads it.

The mapping goes to `--out`, or to standard output. A finding writes no mapping and exits 1, with
the [usual codes](checks.md#read-the-output). The findings go to standard error, or with `--json` as
a [JSON report](checks.md#read-json-output) on standard output.

| Finding | What to check |
| --- | --- |
| `CELL_PROSE`, `CELL_EMPTY`, `CELL_MISSING` | The cell gives no path and has no usable curated row |
| `CELL_NO_AUTHOR` | A person sub-term has no single author or contributor path to extend |
| `CURATED_STALE` | The cell changed since its curated row was written |
| `CURATED_DUPLICATE`, `CURATED_UNUSED` | A curated row repeats or matches no format/term pair |
| `CURATED_PATH`, `CURATED_REPEATS` | A curated path is invalid or repeats its cell |
| `PATH_SHARED` | Two terms use equal or nested paths |
| `CELL_PATH` | The expanded cell is an invalid path, such as `authors[][]` |

`--schemas DIR` adds a `PATH_NOT_IN_SCHEMA` finding for each path absent from the format's schema.
In a codemeta-drift checkout, pass `--schemas tests/fixtures/schemas`. The
[snapshots](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/fixtures/schemas/SOURCES)
cover CFF 1.2.0, pyproject.toml, package.json, Cargo.toml and composer.json, and Zenodo a
[verified subset](zenodo-schema.md). It catches a missing key (Cargo's `package.keyword`), not a
wrong meaning (Zenodo's `id` for a DOI).

## Pin the export

Pin the codemeta-drift version and the file's sha256. Export the file or take
`examples/mapping-<tag>.json` from the tag you pin. The same inputs give the same bytes.
`generator.version` is an input, so each release changes the hash, and a release can change a row's
path without a schema change. When the hash changes, run your tests on the new file and read the
[CHANGELOG](https://github.com/simonvanlierde/codemeta-drift/blob/main/CHANGELOG.md) before you move
the pin.

### Pin a release's export

Each GitHub release carries `mapping-3.1.json`, `mapping-4.0.json` and a `SHA256SUMS` file covering them,
so a consumer can pin an export without a CodeMeta checkout. Check a download against the release,
then record its sha256 and compare later downloads with that value:

```bash
v=0.9.0
curl -fsSLO "https://github.com/simonvanlierde/codemeta-drift/releases/download/v$v/mapping-4.0.json"
curl -fsSLO "https://github.com/simonvanlierde/codemeta-drift/releases/download/v$v/SHA256SUMS"
gh attestation verify mapping-4.0.json --repo simonvanlierde/codemeta-drift
grep ' mapping-4.0.json$' SHA256SUMS | sha256sum -c -
```

On macOS, use `shasum -a 256 -c -` in place of `sha256sum -c -`.

## The file

```json
{
  "schema_version": "1.10",
  "codemeta_tag": "4.0",
  "generator": {"name": "codemeta-drift", "version": "0.9.0"},
  "context_terms": ["address", "affiliation", "alternateName", "..."],
  "rows": [
    {"format": "cargo", "term": "keywords", "path": "package.keywords",
     "crosswalk_cell": "package.keyword",
     "source": "curated:the cell says package.keyword; Cargo's key is package.keywords"}
  ]
}
```

- `schema_version` is a `"MAJOR.MINOR"` string, so `1.10` is not read as `1.1`.
- `codemeta_tag` is the codemeta/codemeta tag the rows were read from.
- `generator` names the tool and version: `0.1.0+hand` marks a hand-written file.
- `context_terms` lists, sorted, the property terms of the tag's `codemeta.jsonld`. A consumer flags
  any other codemeta.json key as unknown, except JSON-LD keywords and the aliases `type` and `id`.

Each row has:

- `format` is an id from the [format table](#format-ids).
- `term` is a term from the [term table](#terms), or a person sub-term.
- `path` is where the value sits, in the [path grammar](#path-grammar). A `null` path means
  there is no usable mapping for that term. The row's `source` gives the reason for a reviewed
  mapping, such as Cargo having no DOI or Crossref supplying several scoped licences.
  A missing citation row means no mapping for that format and term was reviewed.
- `source` is `crosswalk:<file>@<tag>` (`crosswalk:crosswalks/Zenodo.csv@3.1`) when the path is the
  cell, expanded: `authors` becomes `authors[]`, CFF's `person.given-names` `authors[].given-names`.
  It is `curated:<reason>` when the row replaces the cell, picks a path out of prose, or fills
  an empty cell. An empty cell never means `null`.
- `crosswalk_cell` (optional) is the original cell, untrimmed and unexpanded. `""` means it was
  empty, `null` that no cell was joined. If a file lacks it, don't infer it from `path` or `source`.
- `kind` (optional, added in schema 1.9) is `notation` or `scope` on a curated row whose
  crosswalk cell is not wrong, as in the curated file. `hub coverage` reads it; a resolver ignores it.
- `see_also` (optional) is the upstream issue or pull request about the cell.
- `comment` (optional) is for people. Never read it in code.

`codemeta-drift export` writes the rows by format, in the order `cff-1.2.0`, `codemeta`, `crossref`,
`arxiv`, `cff-preferred`, `zenodo`, `pep621`, `cargo`, `npm`, `composer`, `pkg-info`, `r-description`, `julia`, `bibtex`, `datacite`, `setup-py`,
`ruby-gem`, `maven`, `cpan-meta-2`, `nuget`, `pubspec`, `cabal`, `typst`, `quarto`, `github`,
`figshare`, `bio-tools`, `leiningen`, `octave`, `publiccode-0.8`, `swmath`, `spdx-2.3`,
`codemeta-2`, `dcat-3`, `doap`, `wikidata`, `ris`, `endnote`, `gitlab`, `code-json-2.0`, `ro-crate`,
`croissant`, `dublin-core`, `debian`, `mods`, `vivo-1.8`, `spase-2.6.1`, `iso-19115-1-2014`, and
within a format in the order of the term tables, each person term followed by its sub-terms. Look
up a row by format and term. Don't depend on the row order.

Since schema 1.10, the export can also give curated paths for citation fields such as a
container title, full person name, arXiv ID or DOI version relation. These additional rows
appear only where a mapping was reviewed. A CFF preferred citation describes a separate work.
Pass the value at the `cff-1.2.0` `preferredCitation` path, the `preferred-citation` key, to the
`cff-preferred` rows.

### Format ids

`gitlab` and `code-json-2.0` have rows from the 4.0 export on.

| Id | What it is | Id | What it is |
| --- | --- | --- | --- |
| `cff-1.2.0` | `CITATION.cff` | `codemeta` | codemeta.json |
| `crossref` | Crossref REST work `message` | `arxiv` | One Atom entry parsed with local XML names |
| `cff-preferred` | A CFF 1.2.0 `preferred-citation` reference | | |
| `zenodo` | `.zenodo.json` | `pep621` | pyproject.toml `[project]` |
| `cargo` | Cargo.toml | `npm` | package.json |
| `pkg-info` | Python core metadata | `r-description` | R DESCRIPTION |
| `julia` | Julia Project.toml | `bibtex` | biblatex-software entry |
| `datacite` | DataCite REST API JSON | `setup-py` | setup.py `setup()` arguments |
| `ruby-gem` | Gem::Specification | `maven` | pom.xml |
| `cpan-meta-2` | META.json | `nuget` | .nuspec |
| `pubspec` | pubspec.yaml | `cabal` | .cabal file |
| `typst` | typst.toml | `quarto` | Quarto _extension.yml |
| `github` | GitHub REST API repository JSON | `figshare` | Figshare article JSON |
| `bio-tools` | bio.tools entry | `leiningen` | project.clj |
| `octave` | Octave DESCRIPTION | `publiccode-0.8` | publiccode.yml |
| `swmath` | zbMATH Open software record | `spdx-2.3` | SPDX 2.3 package, JSON |
| `codemeta-2` | codemeta.json, 2.0 context | `dcat-3` | DCAT 3 dataset |
| `doap` | DOAP project | `wikidata` | Wikidata item |
| `ris` | RIS record, `TY - COMP` | `endnote` | EndNote record, `%0 Computer Program` |
| `gitlab` | GitLab REST API project JSON | `code-json-2.0` | US federal code.json 2.0 |
| `ro-crate` | RO-Crate 1.1 to 1.3 `ro-crate-metadata.json` | `croissant` | Croissant 1.0 or 1.1 `croissant.json` |
| `dublin-core` | OAI-PMH `oai_dc` or DCMI Terms RDF | `debian` | a source tree's `debian/` |
| `mods` | MODS 3 record | `vivo-1.8` | VIVO 1.8 software individual |
| `spase-2.6.1` | SPASE 2.6.1 Software resource | `iso-19115-1-2014` | ISO 19115-1:2014 in ISO 19115-3 XML |
| `composer` | root composer.json | | |

### Terms

`author` and `contributor` each have the person sub-terms `.givenName`, `.familyName` and `.@id`
(the ORCID), as in `contributor.givenName`.

| Term | Meaning | Term | Meaning |
| --- | --- | --- | --- |
| `name` | the software's name | `version` | its version |
| `author` | its authors | `contributor` | its other contributors |
| `license` | its licence | `identifier` | its DOI |
| `swhid` | its [Software Heritage identifier](https://www.swhid.org/) | `codeRepository` | its source repository |
| `description` | its description | `keywords` | its keywords |
| `datePublished` | its publication date | `publisher` | its publisher, as schema.org defines it |
| `resourceType` | the kind of resource |  |  |

The 1.10 exports also include these curated citation terms where a mapping was reviewed.

| Term | Meaning |
| --- | --- |
| `author.name`, `contributor.name` | a full person or organisation name |
| `author.resourceType`, `contributor.resourceType` | the provider's person or organisation type |
| `url` | the work's landing URL |
| `containerTitle`, `volume`, `issue`, `pagination` | the containing publication and where the work appears in it |
| `preferredCitation` | the CFF reference to cite when preferred |
| `arxivId`, `primaryCategory` | the arXiv entry's identifier and primary subject |
| `relatedDoi` | the DOI of the related publication |
| `isVersionOf`, `hasVersion` | the DOI relations to the version series or a specific version |

Crossref licences apply to a content version from a stated date. The crosswalk leaves the
work-level `license` path empty. Consumers that need a licence must decide which version and
date apply before using an entry.

- `identifier` means only the DOI here, though CodeMeta allows any identifier.
- `swhid` is not a CodeMeta term: codemeta.json holds it in `identifier` beside the DOI, so both
  rows of `codemeta` and `codemeta-2` have the path `identifier`. Tell them apart by syntax.
- `datacite`'s `url` row and the last alternative of its `codeRepository` row are both `url`, the
  DOI's landing page, which holds the repository only for some records. A writer puts only the
  landing page there, never a repository read from another format.
- The `codemeta` `version` path is `version | softwareVersion`, since `softwareVersion` is a
  CodeMeta term too.
- A `publisher` path such as `publisher.name | publisher` falls through to the whole object when the
  publisher is only a reference (`{"@id": "https://ror.org/..."}`). Take its `@id` or leave the name
  empty.
- Every `resourceType` row is curated, since CodeMeta states the kind in `@type`. A row says where
  the kind sits, never its value. For software, write `Software` into DataCite's
  `types.resourceTypeGeneral`, and `software` into Zenodo's `upload_type` and CFF's `type`.

## Path grammar

A path is a list of steps joined by `.`. A step is a key, optionally followed by one selector:

| Form | Means | Example |
| --- | --- | --- |
| `key` | the value under `key` | `package.name` |
| `key[]` | each element of the list under `key` | `authors[]` |
| `key[k=v]` | each element under `key` whose `k` equals `v` or is a list holding `v` | `identifiers[type=doi].value` |
| `a + b` | the values of `a`, then those of `b` | `Author[] + Author-email[]` |
| `a \| b` | `a` if it has any value, else `b`; any number, left to right | `project.urls.Source \| project.urls.Repository \| project.urls.Homepage` |

- A key starts with an ASCII letter or `_`, optionally after `@` (`author[].@id`). Later characters
  are ASCII letters, digits, `_`, `-` or `@` (`Authors@R`). A key may have one prefix,
  `prefix:local`, for RDF (`dcterms:title`).
- A filter value holds ASCII letters, digits, `_`, `.`, `-` or `/` (RO-Crate's `./`).
- `|` and `+` each have exactly one space on both sides. `+` binds tighter, so `a + b | c` reads `c`
  only when `a` and `b` both have no value.
- A filter matches only an element that has the key.
- There are no list indexes (`a[0]`) and no wildcards. The schema's `path` pattern accepts exactly
  this grammar.
- A writer updates the alternative that already has a value, else the first. So `version` goes into
  a new codemeta.json, and an existing `softwareVersion` stays.
- A person sub-term's path starts with its term's path: CFF `author` is `authors[]`, so
  `author.givenName` is `authors[].given-names`. When a format keeps the whole name in one string,
  both name sub-terms point at it (Zenodo `creators[].name`), and the consumer splits it.
- When a term has alternatives, each sub-term has the same ones in the same order. Read a sub-term
  from the alternative its term resolved through, not by first match: a DOAP file with a developer
  and a maintainer reads `author.@id` from `developer[].@id` even when only the maintainer has one.

[Reading formats](reading-formats.md) says how to read non-tree formats and which values to convert.

## Test vectors

`mapping-vectors.json` ships in the `codemeta_drift` package beside `mapping.schema.json`. Each case
has `path`, `document` and `expected`: the values the path resolves to, in document order, from the
first alternative with a value. Run every case through your resolver. Its `schema_version` is the
schema whose grammar the cases need. A case with `raw_input` also tests parsing: its `format` names
the parser (`pkg-info`, `ro-crate`, `croissant`, `oai_dc`, `debian-control`, `mods`, `vivo`, `spase`
or `iso-19115-3`), and its `text` is the source file. Parse the text, compare the tree to
`document`, then resolve `path`. A consumer that doesn't read that format, or doesn't know the name,
skips the parse and still resolves `path`. This package's tests don't frame the `vivo` Turtle.

## Compatibility

A **minor** version (1.0 to 1.1) can add optional fields, format IDs, terms or sub-terms, or relax
a path pattern. A consumer can read a newer minor by skipping rows it does not use. The older
JSON Schema still validates the file unless it uses a relaxed path pattern. The
[hub commands](crosswalk-hub.md) check every term and format ID, so update the hub CLI when
pinning an export with new IDs.

A **major** version (2.0) changes the contract in other ways, such as removing a field, adding a
required field, changing a meaning, or changing how a reader interprets the path grammar.

## What a consumer does

1. Read `schema_version` first. An unknown major is an error (citesync exits 3).
2. Validate against the schema copy kept beside the file, and update the two together. After a minor
   version that relaxes a pattern, update the resolver and run `mapping-vectors.json`. The CHANGELOG
   says which do.
3. Ignore formats, terms and fields it doesn't use.
4. For each format it reads, a missing row for a term it uses is an error (citesync exits 3). A
   `path: null` row is not missing. A citation term from the second term table is the exception:
   it has rows only where a mapping was reviewed, so a missing one means no mapping, not an error. A format that starts at a later tag, such as `gitlab` from 4.0,
   has no rows in an older tag's file: read it from a file for that tag or later.
5. Treat two rows for the same (format, term) as an error. The schema can't check this.

The [crosswalk hub](crosswalk-hub.md) builds SSSOM spokes and crosswalk CSVs from this file. Every
spoke row carries `semapv:ManualMappingCuration`, with the row's source reason in `comment`.
