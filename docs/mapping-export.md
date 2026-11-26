---
description: "The JSON mapping export: how to write it, the contract and schema, how to pin it, and what a consumer checks."
---

# Mapping export

A mapping export is one JSON file, `mapping-<codemeta-tag>.json`, that says where each CodeMeta
term sits in each metadata format. citesync reads it to keep `CITATION.cff`, `codemeta.json`,
`.zenodo.json` and package manifests in step. CodeMeta's own crosswalk cells are often prose, and
sometimes wrong, so tools can't read them directly.

The schema is [`src/codemeta_drift/mapping.schema.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/mapping.schema.json)
(JSON Schema 2020-12). [`examples/mapping-3.1.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/mapping-3.1.json) and
[`examples/mapping-4.0.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/mapping-4.0.json) are the exports for CodeMeta 3.1 and 4.0,
written by `codemeta-drift export`.

## Export a mapping

Install the command with `uv tool install codemeta-drift`. The examples use a CodeMeta
checkout at `codemeta`, as in the [quick start](https://github.com/simonvanlierde/codemeta-drift/blob/main/README.md#try-it). It must contain
the selected tag:

```sh
codemeta-drift export codemeta --tag 4.0 --out mapping-4.0.json
```

The exporter reads the tag's commit, not the working tree. Only tags with a bundled
curated file can be exported: `3.1` and `4.0`. To pass a directory named `export`, write
`./export` so the CLI does not read it as the subcommand.

A path-shaped crosswalk cell, such as `package.version`, supplies the mapping directly.
Other rows come from `curated-<tag>.json` ([3.1](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/curated-3.1.json),
[4.0](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/curated-4.0.json)), a hand-reviewed file with each replacement path and its reason.

The exporter exits 0 on success. A finding, such as an unresolved cell, makes it exit 1 and write no
mapping. It prints the findings on standard error, or with `--json` as a
[JSON report](checks.md#read-json-output) on standard output. Invalid arguments, such as a tag with no
curated file, exit 2, and unreadable inputs exit 3. The mapping goes to `--out`, or to standard
output without it. With `--json`, the report holding the mapping goes there instead.

| Finding | What to check |
| --- | --- |
| `CELL_PROSE`, `CELL_EMPTY`, `CELL_MISSING` | The cell cannot supply a path and has no usable curated row |
| `CELL_NO_AUTHOR` | A person sub-term has no author or contributor path to extend, or that path has alternatives (`\|` or `+`) |
| `CURATED_STALE` | The cell changed since its curated correction was written |
| `CURATED_DUPLICATE`, `CURATED_UNUSED` | A curated row is repeated or matches no exported format/term pair |
| `CURATED_PATH`, `CURATED_REPEATS` | A curated path is invalid or repeats a cell that already supplies it |
| `PATH_SHARED` | Two terms use equal or nested paths unexpectedly |
| `CELL_PATH` | Expanding the cell produces an invalid path, such as `authors[][]` |

Cells join to property-table rows by name. When a name occurs under several types,
such as `identifier` under Thing and Person, the join uses its occurrence order.

## Check paths against JSON Schemas

The bundled schema snapshots are in a codemeta-drift source checkout. From its root,
use `../codemeta` for a CodeMeta checkout beside it:

```sh
uv run codemeta-drift export ../codemeta --tag 4.0 \
  --schemas tests/fixtures/schemas --out mapping-4.0.json
```

`--schemas DIR` adds `PATH_NOT_IN_SCHEMA` findings for paths absent from the format's
schema. The bundled [schema snapshots and sources](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/fixtures/schemas/SOURCES)
cover CFF 1.2.0, pyproject.toml, package.json and Cargo.toml. Zenodo uses a
[verified structural subset](zenodo-schema.md), not a complete deposit validator.

A schema can catch a missing key, such as Cargo's `package.keyword`. It cannot tell
that an existing key means the wrong thing, such as Zenodo's `id` used for a DOI.

## Field paths and value conversion

A row identifies the field for a term: CFF `title` corresponds to CodeMeta `name`.
The consumer handles differences such as SPDX IDs versus URLs, bare versus URL forms of
ORCIDs and DOIs, person-name strings, and `git+` prefixes on repository URLs. It also
handles shapes a path cannot express: Cargo workspace inheritance and npm's `author`
and `repository`, which may be strings or objects.

Some formats are not trees, such as PKG-INFO, XML and RDF records, and line formats. Read
[each format's paths](reading-formats.md) for how to read them into one, and for the values to
convert after.

## Pin the export

Pin two things: the codemeta-drift version and the sha256 of the file it writes.

```sh
sha256sum mapping-4.0.json
```

The same inputs give the same bytes, so the hash is stable. `generator.version` is one of those
inputs, so a new codemeta-drift release changes the hash even when no row changes. A release can
also change a row's path without a schema change ([compatibility](#compatibility)). So when the
hash changes, run your tests against the new file and read the release's entry in the
[CHANGELOG](https://github.com/simonvanlierde/codemeta-drift/blob/main/CHANGELOG.md) before you move
the pin.

Export the file yourself, as above, or take `examples/mapping-<tag>.json` from the release tag you
pin.

## The file

```json
{
  "schema_version": "1.9",
  "codemeta_tag": "4.0",
  "generator": {"name": "codemeta-drift", "version": "0.9.0"},
  "context_terms": ["address", "affiliation", "alternateName", "..."],
  "rows": [
    {
      "format": "cargo",
      "term": "keywords",
      "path": "package.keywords",
      "crosswalk_cell": "package.keyword",
      "source": "curated:the cell says package.keyword; Cargo's key is package.keywords"
    }
  ]
}
```

The header:

- `schema_version` is a `"MAJOR.MINOR"` string, so `1.10` is not parsed as the number `1.1`.
- `codemeta_tag` is the codemeta/codemeta tag the crosswalk rows were read from.
- `generator` names the tool and version that wrote the file. A hand-written file marks itself
  with a local version label, such as `0.1.0+hand`.
- `context_terms` (since schema 1.7) lists every property term of the tag's `codemeta.jsonld`,
  sorted. These are the keys a codemeta.json written to that context may use, besides JSON-LD
  keywords such as `@type` and the aliases `type` and `id`. A consumer flags any other key as
  unknown. It is not the `term` of a row, which names a mapping term such as `swhid`. The 3.1 list
  has `softwareSuggestions`; the 4.0 list does not, because the 4.0 context dropped it.

Each row:

- `format` is a stable format id from the [format table](#format-ids).
- `term` is a term from the [term table](#terms), or a person sub-term.
- `path` is where the value sits, in the [path grammar](#path-grammar), or `null` when the format
  has no place for it (Cargo has no DOI). A `null` row is not a missing row.
- `source` says where the row comes from:
  - `crosswalk:<file>@<tag>` means the path is that crosswalk's cell, for example
    `crosswalk:crosswalks/Zenodo.csv@3.1`. The exporter expands list and person paths: `authors`
    becomes `authors[]`, and CFF's `person.given-names` becomes `authors[].given-names`.
  - `curated:<reason>` means the row departs from the crosswalk, and says why. It either replaces
    a wrong cell, picks one path out of a prose cell, or fills a cell the crosswalk leaves empty.
    An empty cell is never read as `null`: the crosswalks also leave cells empty that the format has.
- `crosswalk_cell` (optional, since schema 1.3) is the original crosswalk cell, before trimming
  whitespace or expanding a relative path. `""` means the joined cell was empty. `null` means no
  cell could be joined, including formats without an upstream crosswalk. New exports emit it on
  every row. An older export without this field does not supply the original cell; a consumer must
  not infer it from `path` or `source`.
- `see_also` (optional) is the upstream issue or pull request about the cell the row departs from.
- `comment` (optional) is a note for people. Never read it in code.

A (format, term) pair appears at most once. The schema cannot enforce that, so the consumer checks it.

`codemeta-drift export` writes the rows by format, in the order `cff-1.2.0`, `codemeta`, `zenodo`,
`pep621`, `cargo`, `npm`, `pkg-info`, `r-description`, `julia`, `bibtex`, `datacite`, `setup-py`,
`ruby-gem`, `maven`, `cpan-meta-2`, `nuget`, `pubspec`, `cabal`, `typst`, `quarto`, `github`,
`figshare`, `bio-tools`, `leiningen`, `octave`, `publiccode-0.8`, `swmath`, `spdx-2.3`,
`codemeta-2`, `dcat-3`, `doap`, `wikidata`, `ris`, `endnote`, `gitlab`, `code-json-2.0`, `ro-crate`,
`croissant`, `dublin-core`, `debian`, `mods`, `vivo-1.8`, `spase-2.6.1`, `iso-19115-1-2014`, and
within a format in the order of the term table, each person term followed by its sub-terms. A
consumer must not depend on the row order.

### Format ids

A format whose versions differ puts the version in the id. `gitlab` and `code-json-2.0` have rows
from the 4.0 export on, because their crosswalks first came with CodeMeta 4.0.

| Id | What it is |
| --- | --- |
| `cff-1.2.0` | `CITATION.cff`, Citation File Format 1.2.0 |
| `codemeta` | codemeta.json |
| `zenodo` | `.zenodo.json`, Zenodo deposit metadata |
| `pep621` | pyproject.toml's `[project]` table |
| `cargo` | Cargo.toml |
| `npm` | package.json |
| `pkg-info` | Python core metadata (PKG-INFO) |
| `r-description` | R's DESCRIPTION |
| `julia` | Julia's Project.toml |
| `bibtex` | a biblatex-software entry |
| `datacite` | the DataCite REST API's JSON |
| `setup-py` | setup.py's `setup()` arguments |
| `ruby-gem` | a Gem::Specification |
| `maven` | pom.xml |
| `cpan-meta-2` | META.json |
| `nuget` | .nuspec |
| `pubspec` | pubspec.yaml |
| `cabal` | a .cabal file |
| `typst` | typst.toml |
| `quarto` | a Quarto extension's _extension.yml |
| `github` | the GitHub REST API's repository JSON |
| `figshare` | a Figshare article's JSON |
| `bio-tools` | a bio.tools entry |
| `leiningen` | project.clj |
| `octave` | an Octave package's DESCRIPTION |
| `publiccode-0.8` | publiccode.yml |
| `swmath` | a zbMATH Open software record |
| `spdx-2.3` | an SPDX 2.3 package in JSON |
| `codemeta-2` | a codemeta.json written to the 2.0 context |
| `dcat-3` | a DCAT 3 dataset |
| `doap` | a DOAP project |
| `wikidata` | a Wikidata item |
| `ris` | a RIS record with `TY - COMP` |
| `endnote` | an EndNote tagged record with `%0 Computer Program` |
| `gitlab` | the GitLab REST API's project JSON |
| `code-json-2.0` | a code.json 2.0 file, the US federal source code metadata |
| `ro-crate` | an RO-Crate 1.1 to 1.3 `ro-crate-metadata.json` |
| `croissant` | a Croissant 1.0 or 1.1 `croissant.json` |
| `dublin-core` | an OAI-PMH `oai_dc` record or a DCMI Terms RDF record |
| `debian` | a Debian source tree's `debian/` directory |
| `mods` | a MODS 3 record |
| `vivo-1.8` | a VIVO 1.8 software individual |
| `spase-2.6.1` | a SPASE 2.6.1 Software resource |
| `iso-19115-1-2014` | an ISO 19115-1:2014 record in ISO 19115-3 XML |

### Terms

The export has thirteen terms. `author` and `contributor` also have three person sub-terms each,
written with their parent: `.givenName`, `.familyName` and `.@id` (the ORCID), as in
`contributor.givenName`.

| Term | Meaning | Note |
| --- | --- | --- |
| `name` | the software's name | |
| `version` | its version | The `codemeta` path is `version \| softwareVersion` |
| `author` | its authors | Has person sub-terms |
| `contributor` | its other contributors | Has person sub-terms |
| `license` | its licence | |
| `identifier` | its DOI | codemeta-drift's narrower reading for citation tools |
| `swhid` | its [Software Heritage identifier](https://www.swhid.org/) | Not a CodeMeta term |
| `codeRepository` | its source code repository | |
| `description` | its description | |
| `keywords` | its keywords | |
| `datePublished` | its publication date | |
| `publisher` | its publisher, as schema.org defines it | Since schema 1.7 |
| `resourceType` | the kind of resource, such as software | Since schema 1.7; not in CodeMeta's property table |

`identifier` means the DOI only in this export. CodeMeta's own definition, in
`properties_description.csv`, covers any kind of identifier, such as an ISBN or a UUID.

`swhid` is the Software Heritage identifier, such as
`swh:1:dir:d198bc9d7a6bcf6db04f476d29314f157507d505`. CodeMeta has no term of its own for it:
codemeta.json holds it in `identifier`, beside the DOI. So both rows of `codemeta` and of
`codemeta-2` have the path `identifier`, and the consumer tells them apart by their syntax.

The `codemeta` `version` path is `version | softwareVersion`. schema.org's `softwareVersion` is a
CodeMeta term too, so a codemeta.json that holds only it still has a version.

A `publisher` path such as `publisher.name | publisher` falls through to the whole object when the
publisher is given only by reference (`{"@id": "https://ror.org/..."}`). That object is not a
name, so the consumer takes its `@id` or leaves the name empty.

CodeMeta states the kind of resource in `@type`, and its property table has no row for it, so
every `resourceType` row is curated. A row says where the kind sits, never its value. For software
a consumer writes `Software` into DataCite's `types.resourceTypeGeneral`, and `software` into
Zenodo's `upload_type` and CFF's `type`.

## Path grammar

A path is a list of steps joined by `.`. A step is a key, optionally followed by one selector:

| Form | Means | Example |
| --- | --- | --- |
| `key` | the value under `key` | `package.name` |
| `key[]` | each element of the list under `key` | `authors[]` |
| `key[k=v]` | each element of the list under `key` whose `k` equals `v`, or is a list that holds `v` | `identifiers[type=doi].value` |
| `a + b` | the values of `a`, then those of `b` | `Author[] + Author-email[]` |
| `a \| b` | `a` if it has any value, else `b`; any number, read left to right | `project.urls.Source \| project.urls.Repository \| project.urls.Homepage` |

- A key starts with an ASCII letter or `_`, optionally preceded by `@` (`author[].@id`).
  Later characters can be ASCII letters, digits, `_`, `-` or `@` (R's `Authors@R`, since schema 1.4).
  A key may carry one prefix, `prefix:local`, for RDF formats (`dcterms:title`, since schema 1.6).
- A filter value contains ASCII letters, digits, `_`, `.`, `-` or `/` (RO-Crate's `./`, since schema 1.8).
- Alternatives are separated by exactly one space, `|`, one space, and parts by one space, `+`,
  one space. `+` binds tighter, so `a + b | c` reads `c` only when `a` and `b` both have no value.
- A filter matches only an element that has the key.
- There are no list indexes (`a[0]`) and no wildcards.
- A writer updates the alternative the document already has a value in, else it writes the first one. So the
  `codemeta` `version` row writes `version` into a new file and keeps an existing `softwareVersion` where it is.

A person sub-term's path is absolute and starts with the path of its term. CFF `author` is
`authors[]`, so `author.givenName` is `authors[].given-names`. When a format keeps the whole
name in one string, both name sub-terms point at it (Zenodo `creators[].name`), and the
consumer splits it.

When a term has alternatives, each of its sub-terms has the same alternatives in the same order,
each starting with its term's. A consumer reads a sub-term from the alternative its term resolved
through, not by first match: a DOAP file with a developer and a maintainer reads `author.@id` from
`developer[].@id` even when only the maintainer has one.

The schema's `path` pattern accepts exactly this grammar.

## Test vectors

`mapping-vectors.json` lists cases of `path`, `document` and `expected`. It ships in the
`codemeta_drift` package directory, beside `mapping.schema.json`. `expected` is the list of values
the path resolves to in `document`, in document order, from the first alternative that yields any
value. Copy the file into your project with the schema, and run every case through your own
resolver. Its `schema_version` is the mapping schema whose grammar the cases need.

Cases with `raw_input` also test parsing. Its `format` names the parser (`pkg-info`, `ro-crate`,
`croissant`, `oai_dc`, `debian-control`, `mods`, `vivo`, `spase` or `iso-19115-3`), and its `text`
is the source file content. Parse that text and compare the resulting tree to `document` before
resolving `path`. A consumer that does not read that format skips the parse and still resolves
`path` in `document`. A release can add parser names, so skip the parse for a name you don't know.

The `vivo` case gives Turtle as `raw_input` and the framed tree as `document`. This package's own
tests resolve that tree but do not frame the Turtle. The PKG-INFO cases cover comma separation,
quoted names, company suffixes and `et al.`.

## Compatibility

A **minor** version (1.0 to 1.1) only adds: an optional field, a new format id, a new term or
sub-term, or a relaxed path pattern. A consumer that knows 1.0 reads a 1.1 file correctly.

A 1.1 file that only adds fields, format ids or terms also passes the 1.0 schema. The schema allows
fields it doesn't define, in the header, `generator` and each row, and checks format ids and terms
by pattern. A relaxed path pattern is the exception: the file then fails the older schema, so copy
in the new schema with it. For example, 1.4's `Authors@R` paths fail the 1.3 schema.

A **major** version (1.x to 2.0) is anything else: a renamed or removed field, a new required
field, a changed meaning, or a change to the path grammar that an old reader would misread.

New rows, and rows that change path because a crosswalk cell was fixed, are not schema changes.
They come with a new codemeta tag or a new codemeta-drift release, which is why you [pin the
export](#pin-the-export).

## What a consumer does

1. Read `schema_version` first. A major it doesn't know is an error ([citesync](https://github.com/simonvanlierde/citesync), the first consumer, exits 3).
2. Validate the file against the schema copy kept beside it, and update the two together. After
   a minor version that relaxes a pattern, update the resolver too and run `mapping-vectors.json`
   through it. The [CHANGELOG](https://github.com/simonvanlierde/codemeta-drift/blob/main/CHANGELOG.md)
   says what each schema version adds and which ones relax a pattern.
3. Ignore rows for formats and terms it doesn't use, and fields it doesn't know.
4. For each format it reads, a missing row for a term it uses is an error (citesync exits 3). A
   format that starts at a later tag, such as `gitlab` from 4.0, has no rows in an older tag's
   file: read it from a file for that tag or later. A row with `path: null` is not missing: the
   format has no place for that term.
5. Treat two rows for the same (format, term) as an error.

The [crosswalk hub](crosswalk-hub.md) builds SSSOM spokes and CodeMeta crosswalk CSVs from this file.
In its SSSOM spokes, crosswalk and curated rows both carry `semapv:ManualMappingCuration`, with
the row's source reason in `comment`.
