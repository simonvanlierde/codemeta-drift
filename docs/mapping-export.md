# Mapping export

A mapping export is one JSON file, `mapping-<codemeta-tag>.json`, that says where each CodeMeta
term sits in each metadata format. Tools that keep `CITATION.cff`, `codemeta.json`,
`.zenodo.json` and package manifests in step read it instead of parsing CodeMeta's crosswalk
tables, whose cells are prose and sometimes wrong.

The schema is [`src/codemeta_drift/mapping.schema.json`](../src/codemeta_drift/mapping.schema.json)
(JSON Schema 2020-12). [`examples/mapping-3.1.json`](../examples/mapping-3.1.json) is the
export for CodeMeta 3.1, written by `codemeta-drift export`.

## Export a mapping

Install the command with `uv tool install codemeta-drift`. The examples use a CodeMeta
checkout at `codemeta`, as in the [quick start](../README.md#try-it). It must contain
the selected tag:

```sh
codemeta-drift export codemeta --tag 3.1 --out mapping-3.1.json
```

The exporter reads the tag's commit, not the working tree. Only tags with a bundled
curated file can be exported; currently that is `3.1`. To check a directory named
`export`, write `./export` so the CLI does not treat it as the subcommand.

A path-shaped crosswalk cell, such as `package.version`, supplies the mapping directly.
Other rows use [`curated-3.1.json`](../src/codemeta_drift/curated-3.1.json), which records
the replacement path and reason. The exporter refuses an unresolved cell, prints the
findings on standard error and exits 1 without writing output. A successful export exits 0;
invalid arguments or unreadable inputs exit 2. Without `--out`, JSON goes to standard output.

| Finding | What to check |
| --- | --- |
| `CELL_PROSE`, `CELL_EMPTY`, `CELL_MISSING` | The cell cannot supply a path and has no usable curated row |
| `CELL_NO_AUTHOR` | A person sub-term has no author or contributor path to extend |
| `CURATED_STALE` | The cell changed since its curated correction was written |
| `CURATED_DUPLICATE`, `CURATED_UNUSED` | A curated row is repeated or matches no exported format/term pair |
| `CURATED_PATH`, `CURATED_REPEATS` | A curated path is invalid or repeats a cell that already supplies it |
| `PATH_SHARED` | Two terms use equal or nested paths unexpectedly |
| `CELL_PATH` | Expanding the cell produces an invalid path, such as `authors[][]` |

Cells join to property-table rows by name. When a name occurs under several types,
such as `identifier` under Thing and Person, the join uses its occurrence order.
The DOI and SWHID deliberately share CodeMeta's `identifier` path; consumers distinguish
them by their values.

## Check paths against JSON Schemas

The bundled schema snapshots are in a codemeta-drift source checkout. From its root,
use `../codemeta` for a CodeMeta checkout beside it:

```sh
uv run codemeta-drift export ../codemeta --tag 3.1 \
  --schemas tests/fixtures/schemas --out mapping-3.1.json
```

`--schemas DIR` adds `PATH_NOT_IN_SCHEMA` findings for paths absent from the format's
schema. The bundled [schema snapshots and sources](../tests/fixtures/schemas/SOURCES)
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

## The file

```json
{
  "schema_version": "1.6",
  "codemeta_tag": "3.1",
  "generator": {"name": "codemeta-drift", "version": "0.6.0"},
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

- `schema_version` is `"MAJOR.MINOR"`. It is a string, not a number, so `1.10` can't turn into `1.1`.
- `codemeta_tag` is the codemeta/codemeta tag the crosswalk rows were read from.
  `codemeta-drift export` reads the tag's commit, never a working tree.
- `generator` names the tool and version that wrote the file. A hand-written file marks itself
  with a local version label, such as `0.1.0+hand`.

Each row:

- `format` is a stable id: `cff-1.2.0`, `codemeta`, `zenodo`, `pep621`, `cargo`, `npm`,
  `pkg-info` (Python core metadata), `r-description` (R's DESCRIPTION), `julia` (Julia's
  Project.toml), `bibtex` (a biblatex-software entry), `datacite` (the DataCite REST API's
  JSON), `setup-py` (setup.py's `setup()` arguments), `ruby-gem` (a Gem::Specification), `maven`
  (pom.xml), `cpan-meta-2` (META.json), `nuget` (.nuspec), `pubspec` (pubspec.yaml), `cabal`
  (a .cabal file), `typst` (typst.toml), `quarto` (a Quarto extension's _extension.yml),
  `github` (the GitHub REST API's repository JSON), `figshare` (a Figshare article's JSON),
  `bio-tools` (a bio.tools entry), `leiningen` (project.clj), `octave` (an Octave package's
  DESCRIPTION), `publiccode-0.8` (publiccode.yml), `swmath` (a zbMATH Open software record),
  `spdx-2.3` (an SPDX 2.3 package in JSON), `codemeta-2` (a codemeta.json written to the 2.0
  context), `dcat-3` (a DCAT 3 dataset), `doap` (a DOAP project) or `wikidata` (a Wikidata
  item). A format whose versions differ puts the version in the id. `pkg-info` to `bibtex` were
  added in schema 1.4, and `datacite` to `wikidata` in 1.5.
- `term` is one of the eleven terms `name`, `version`, `author`, `contributor`, `license`,
  `identifier`, `swhid`, `codeRepository`, `description`, `keywords` and `datePublished`, or a person
  sub-term of `author` or `contributor`: `.givenName`, `.familyName` and `.@id` (the ORCID). A
  sub-term names the term it sits under, because `contributor.givenName` sits somewhere else
  than `author.givenName`. `identifier` is the DOI. `swhid` is the
  [Software Heritage identifier](https://www.swhid.org/), such as
  `swh:1:dir:d198bc9d7a6bcf6db04f476d29314f157507d505`. CodeMeta has no term of its own for it:
  codemeta.json holds it in `identifier`, beside the DOI, so both rows of `codemeta` and of
  `codemeta-2` have the path `identifier` and the consumer distinguishes them by their identifier syntax.
- `path` is where the value sits, in the grammar below, or `null` when the format has no place
  for it (Cargo has no DOI). A `null` row is a real answer, not a missing row.
- `source` says where the row comes from. `crosswalk:<file>@<tag>` means the path is that
  crosswalk's cell, for example `crosswalk:crosswalks/Zenodo.csv@3.1`. The exporter expands
  list and person paths: `authors` becomes `authors[]`, and CFF's `person.given-names`
  becomes `authors[].given-names`. `curated:<reason>` means the row departs from the crosswalk, picks
  one path out of a prose cell, or fills a cell it leaves empty, and says why. An empty cell is
  never read as `null`, because the crosswalks also leave cells empty that the format has.
- `crosswalk_cell` (optional, added in schema 1.3) is the original crosswalk cell, before
  trimming whitespace or expanding a relative path. `""` means the joined cell was empty;
  `null` means no cell could be joined, including formats without an upstream crosswalk.
  New exports emit it on every row. An older export without this field does not supply the
  original cell; a consumer must not infer it from `path` or `source`.
- `see_also` (optional) is the upstream issue or pull request about the cell the row departs from.
- `comment` (optional) is a note for people. Never read it in code.

CFF stores a name particle and a name suffix apart from `family-names`, and CodeMeta has only
`familyName`. A consumer reads the CodeMeta family name from the three joined by spaces:
`name-particle`, `family-names`, `name-suffix`, each only when present. Antonie van Leeuwenhoek
(`name-particle: van`, `family-names: Leeuwenhoek`) has the family name `van Leeuwenhoek`, and
a `Jr.` in `name-suffix` ends it. The `cff-1.2.0` `author.familyName` row says so in its `comment`.

PKG-INFO, R's DESCRIPTION and several of the newer formats are not trees, so a consumer reads
them into one first. These cases need more than the grammar below says:

- PKG-INFO: each field is a key, and a field that repeats is a list. `Project-URL` becomes
  elements with `label` and `url`, the label normalised as the
  [well-known project URLs spec](https://packaging.python.org/en/latest/specifications/well-known-project-urls/)
  says: lower case, no punctuation or whitespace, so `Source Code` matches `sourcecode`.
- R DESCRIPTION: `Authors@R` becomes a list of person entries with `given`, `family`, `role`
  and `comment`, where `comment` is a mapping (`c(ORCID = "...")`). `role` is a list, so
  `[role=aut]` matches `c("aut", "cre")`. A package without `Authors@R` has only the free-text `Author` field, which no path reads.
- Julia: an `authors` element may be a plain `Name` or `Name <email>` string. Both name
  sub-terms then come from that string, and the consumer splits it, as for Zenodo.
- DataCite: paths start inside `data.attributes` of the REST API's JSON, so the DOI is `doi`.
  The XML form is not addressed.
- setup.py and Ruby gemspecs are code, not data. A consumer reads the literal arguments of
  `setup()` with a Python parser, or loads a gemspec with `Gem::Specification.load`, in a
  throwaway environment and never on the host. A gem's `version` is read as a string.
- pom.xml and .nuspec are XML. The tree starts at `project` (Maven) or `package.metadata`
  (NuGet), with the namespace ignored. An element the schema lets repeat (a `developer`, a
  `license`) is a list even when it occurs once, under its wrapper (`developers.developer[]`).
  An attribute is an `@` key (`repository.@url`), and an element with attributes reads its text
  at its own path. A Maven value with `${...}` may need resolving first.
- A .cabal file: field names are lower case, and each top-level field is a key holding its text.
  A section is an element of a list named after it, with its first argument as `kind`, so
  `source-repository head` is read at `source-repository[kind=head].location`.
- project.clj is Clojure code: never run `lein` or `load-file` on it. A consumer reads it with a
  Clojure reader with `*read-eval*` off and takes the first `(defproject NAME VERSION :key value ...)`
  form as a map: `name` and `group` from the NAME symbol, `version` from the second element, and
  each `:key` without its colon. A value written as an unquote (`~`) is skipped, not evaluated.
- Octave's DESCRIPTION has `Name: value` lines, a line starting with a space continues the value
  before it, and `#` starts a comment. Field names are lower-cased, as Octave's `pkg` does, so
  `License` is read at `license`, and only the first of a repeated field counts.
- SPDX: the paths address the JSON form, where a package is an element of `packages` with lower
  camel case keys (`versionInfo`). The crosswalk cells use the tag-value names (`PackageName`),
  which are not JSON keys. In a document with several packages, the consumer reads the one that
  SPDXRef-DOCUMENT's `DESCRIBES` relationship names.
- DCAT 3 and DOAP are RDF. A consumer reads the record (RDF/XML from Zenodo's OAI-PMH or a
  project's `.doap` file) as JSON-LD rooted at the `dcat:Dataset` or `doap:Project` node,
  compacted with a context that defines only the prefixes `dcat`, `dcterms`, `owl`, `foaf` and
  `doap`, so each key is a prefixed name such as `dcterms:title`. A property may hold one value or
  a list, a link is an object with `@id`, and a typed date may be an object with `@value`.
- Wikidata: the root is the entity object of `Special:EntityData/Q<id>.json`. A statement is an
  element of `claims.P<n>`, with its value under `mainsnak.datavalue.value`: a string, an object
  with `id` for an item, or an object with `time` for a date. A deprecated statement is skipped.

Every row in an export has been checked by a person: `crosswalk:` and `curated:` rows alike.
Rows a tool proposed but nobody checked never go in an export.

A (format, term) pair appears at most once. The schema cannot enforce uniqueness by
those two fields, so the consumer checks it.

`codemeta-drift export` writes the rows by format, in the order `cff-1.2.0`, `codemeta`,
`zenodo`, `pep621`, `cargo`, `npm`, `pkg-info`, `r-description`, `julia`, `bibtex`, `datacite`, `setup-py`, `ruby-gem`, `maven`, `cpan-meta-2`, `nuget`, `pubspec`, `cabal`, `typst`, `quarto`, `github`, `figshare`, `bio-tools`, `leiningen`, `octave`, `publiccode-0.8`, `swmath`, `spdx-2.3`, `codemeta-2`, `dcat-3`, `doap`, `wikidata`, and within a format in the order `name`, `version`, `author`,
`author.givenName`, `author.familyName`, `author.@id`, `contributor`, `contributor.givenName`,
`contributor.familyName`, `contributor.@id`, `license`, `identifier`, `swhid`, `codeRepository`,
`description`, `keywords`, `datePublished`. The same inputs give the same bytes, so a consumer
can pin the file's sha256. The header's `generator.version` is one of those inputs: a new
codemeta-drift release changes the bytes even when no row changes. A consumer must not depend on the row order.

## Path grammar

A path is a list of steps joined by `.`. A step is a key, optionally followed by one selector:

| Form | Means | Example |
| --- | --- | --- |
| `key` | the value under `key` | `package.name` |
| `key[]` | each element of the list under `key` | `authors[]` |
| `key[k=v]` | each element of the list under `key` whose `k` equals `v`, or is a list that holds `v` | `identifiers[type=doi].value` |
| `a + b` | the values of `a`, then those of `b` | `Author + Author-email` |
| `a \| b` | `a` if it has any value, else `b`; any number, read left to right | `project.urls.Source \| project.urls.Repository \| project.urls.Homepage` |

- A key starts with an ASCII letter or `_`, optionally preceded by `@` (`author[].@id`).
  Later characters can be ASCII letters, digits, `_`, `-` or `@` (R's `Authors@R`, since schema 1.4).
  A key may carry one prefix, `prefix:local`, for RDF formats (`dcterms:title`, since schema 1.6).
- A filter value contains ASCII letters, digits, `_`, `.` or `-`.
- Alternatives are separated by exactly one space, `|`, one space, and parts by one space, `+`,
  one space. `+` binds tighter, so `a + b | c` reads `c` only when `a` and `b` both have no value.
- A filter matches only an element that has the key.
- There are no list indexes (`a[0]`) and no wildcards.

A person sub-term's path is absolute and starts with the path of its term. CFF `author` is
`authors[]`, so `author.givenName` is `authors[].given-names`. When a format keeps the whole
name in one string, both name sub-terms point at it (Zenodo `creators[].name`), and the
consumer splits it.

When a term has alternatives, each of its sub-terms has the same alternatives in the same order,
each starting with its term's. A consumer reads a sub-term from the alternative its term resolved
through, not by first match: a DOAP file with a developer and a maintainer reads `author.@id` from
`developer[].@id` even when only the maintainer has one, so one person's ORCID never lands on another.

The schema's `path` pattern accepts exactly this grammar.

`mapping-vectors.json`, in the package beside `mapping.schema.json`, lists cases of `path`, `document`
and `expected`. `expected` is the list of values the path resolves to in `document`, in document order,
from the first alternative that yields any value. A consumer vendors the file with the schema and runs
every case through its own resolver, so the copies of the grammar stay in step.

## Compatibility

A **minor** version (1.0 to 1.1) only adds: an optional field, a new format id, a new term or
sub-term, or a relaxed pattern. A consumer that knows 1.0 reads a 1.1 file correctly. The schema
allows fields it doesn't define, in the header, `generator` and each row, so a file that only
adds those also passes the older schema a consumer vendors. A relaxed pattern does not: 1.4's
`Authors@R` paths fail the 1.3 schema, so the consumer vendors the new schema with the file.

A **major** version (1.x to 2.0) is anything else: a renamed or removed field, a new required
field, a changed meaning, or a change to the path grammar that an old reader would misread.

New rows, and rows that change path because a crosswalk cell was fixed, are not schema changes.
They come with a new codemeta tag or a new codemeta-drift release.

## What a consumer does

1. Read `schema_version` first. A major it doesn't know is an error ([citesync](https://github.com/simonvanlierde/citesync), the first consumer, exits 2).
2. Validate the file against the schema it vendors beside it, and update the two together:
   a relaxed pattern, such as the `@` keys of schema 1.4, fails an older vendored schema.
   Schema 1.5 only adds format ids, so a 1.5 file passes the 1.4 schema. Schema 1.6 relaxes the
   path pattern for `+` and prefixed keys, so a 1.6 file fails the older schemas. Update the
   resolver too, and run `mapping-vectors.json` through it: since 1.6, `[k=v]` also matches a list
   that holds `v`.
3. Ignore rows for formats and terms it doesn't use, and fields it doesn't know.
4. For each format it reads, a missing row for a term it uses is an error (citesync exits 2).
   A row with `path: null` is not missing: the format has no place for that term.
5. Treat two rows for the same (format, term) as an error.

## SSSOM spokes

The [crosswalk hub](crosswalk-hub.md) exports SSSOM 1.0 TSV spokes from this JSON file.
The JSON contract stays unchanged. The spokes use `skos:relatedMatch`, because these
paths identify corresponding fields without proving that their values or meanings match.

The hub uses its own term namespace for person sub-terms and `swhid`. It does not invent
CodeMeta vocabulary terms for them. Both crosswalk and curated rows retain
`semapv:ManualMappingCuration` with their source reason in `comment`.
