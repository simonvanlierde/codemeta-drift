# Mapping export

A mapping export is one JSON file, `mapping-<codemeta-tag>.json`, that says where each CodeMeta
term sits in each metadata format. Tools that keep `CITATION.cff`, `codemeta.json`,
`.zenodo.json` and package manifests in step read it instead of parsing CodeMeta's crosswalk
tables, whose cells are prose and sometimes wrong.

The schema is [`src/codemeta_drift/mapping.schema.json`](../src/codemeta_drift/mapping.schema.json)
(JSON Schema 2020-12). [`examples/mapping-3.1.json`](../examples/mapping-3.1.json) and
[`examples/mapping-4.0.json`](../examples/mapping-4.0.json) are the exports for CodeMeta 3.1 and 4.0,
written by `codemeta-drift export`.

## Export a mapping

Install the command with `uv tool install codemeta-drift`. The examples use a CodeMeta
checkout at `codemeta`, as in the [quick start](../README.md#try-it). It must contain
the selected tag:

```sh
codemeta-drift export codemeta --tag 4.0 --out mapping-4.0.json
```

The exporter reads the tag's commit, not the working tree. Only tags with a bundled
curated file can be exported; currently those are `3.1` and `4.0`. To check a directory named
`export`, write `./export` so the CLI does not treat it as the subcommand.

A path-shaped crosswalk cell, such as `package.version`, supplies the mapping directly.
Other rows use `curated-<tag>.json` ([3.1](../src/codemeta_drift/curated-3.1.json),
[4.0](../src/codemeta_drift/curated-4.0.json)), which records the replacement path and reason. The exporter refuses an unresolved cell, prints the
findings on standard error and exits 1 without writing output. A successful export exits 0;
invalid arguments, such as a tag with no curated file, exit 2, and unreadable inputs exit 3. Without `--out`, JSON goes to standard output.

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
The DOI and SWHID deliberately share CodeMeta's `identifier` path; consumers distinguish
them by their values.

## Check paths against JSON Schemas

The bundled schema snapshots are in a codemeta-drift source checkout. From its root,
use `../codemeta` for a CodeMeta checkout beside it:

```sh
uv run codemeta-drift export ../codemeta --tag 4.0 \
  --schemas tests/fixtures/schemas --out mapping-4.0.json
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
  "schema_version": "1.8",
  "codemeta_tag": "3.1",
  "generator": {"name": "codemeta-drift", "version": "0.7.2"},
  "context_terms": ["address", "affiliation", "applicationCategory", "..."],
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
- `context_terms` lists every property term of the tag's `codemeta.jsonld`, sorted: the keys a codemeta.json
  written to that context may use, besides JSON-LD keywords such as `@type` and the aliases `type` and `id`.
  A consumer flags any other key as unknown. It is not the `term` of a row, which names a mapping term such as `swhid`.
  The 3.1 list has `softwareSuggestions`; the 4.0 list does not, because the 4.0 context dropped it.
  `context_terms` was added in schema 1.7.

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
  context), `dcat-3` (a DCAT 3 dataset), `doap` (a DOAP project), `wikidata` (a Wikidata
  item), `ris` (a RIS record with `TY  - COMP`), `endnote` (an EndNote tagged record with
  `%0 Computer Program`), `gitlab` (the GitLab REST API's project JSON), `code-json-2.0` (a
  code.json 2.0 file, the US federal source code metadata), `ro-crate` (an RO-Crate 1.1 to 1.3
  `ro-crate-metadata.json`) or `croissant` (a Croissant 1.0 or 1.1 `croissant.json`). A format whose versions differ puts the
  version in the id. `pkg-info` to `bibtex` were added in schema 1.4, `datacite` to `wikidata` in
  1.5, `ris` to `code-json-2.0` in 1.7, and `ro-crate` and `croissant` in 1.8. `gitlab` and `code-json-2.0` have rows from the 4.0
  export on, because their crosswalks first came with CodeMeta 4.0.
- `term` is one of the thirteen terms `name`, `version`, `author`, `contributor`, `license`,
  `identifier`, `swhid`, `codeRepository`, `description`, `keywords`, `datePublished`, `publisher` and
  `resourceType`, or a person sub-term of `author` or `contributor`: `.givenName`, `.familyName` and `.@id` (the ORCID). A
  sub-term names the term it sits under, because `contributor.givenName` sits somewhere else
  than `author.givenName`. `identifier` is the DOI. `swhid` is the
  [Software Heritage identifier](https://www.swhid.org/), such as
  `swh:1:dir:d198bc9d7a6bcf6db04f476d29314f157507d505`. CodeMeta has no term of its own for it:
  codemeta.json holds it in `identifier`, beside the DOI, so both rows of `codemeta` and of
  `codemeta-2` have the path `identifier` and the consumer distinguishes them by their identifier syntax.
  `publisher` is schema.org's. `resourceType` is the kind of resource, which CodeMeta states in `@type` and
  has no term for in its property table, so its rows are all curated. A row says where the kind sits, never
  its value: for software a consumer writes `Software` into DataCite's `types.resourceTypeGeneral`,
  `software` into Zenodo's `upload_type` and CFF's `type`. `publisher` and `resourceType` were added in schema 1.7.
  A `publisher` path such as `publisher.name | publisher` falls through to the whole object when the
  publisher is given only by reference (`{"@id": "https://ror.org/..."}`); that object is not a name, so the
  consumer takes its `@id` or leaves the name empty.
  The `codemeta` `version` path is `version | softwareVersion`: schema.org's `softwareVersion` is a CodeMeta term too,
  so a codemeta.json that holds only it still has a version.
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

- PKG-INFO: each field is a key, and a field that repeats is a list. `Author` holds the authors
  who have no email, separated by commas: the
  [pyproject.toml spec](https://packaging.python.org/en/latest/specifications/pyproject-toml/#authors-maintainers)
  says a name must not contain commas and "Multiple values should be separated by commas", and most
  build backends write `Author: A, B`. The parser splits `Author` at commas outside double quotes and
  trims each piece. A company suffix (`Inc`, `LLC`, `Ltd`, `GmbH`, `PBC` or `Corp`, with or without a
  dot) stays with the piece before it, so `Datadog, Inc.` is one name, and a piece that is `et al.` is
  dropped. The split loses names that hold a comma, such as `Last, First` and the core metadata spec's own
  example `C. Schultz, Universal Features Syndicate, Los Angeles, CA`: they read as several names; quote such
  a name (`"Smith, Jane"`) to keep it whole, and the parser drops the quotes. `Author-email` is an RFC 822 address list: the parser
  splits it at commas that are outside double quotes and angle brackets, so
  `"Smith, Jane" <j@example.org>, Ada Lovelace <ada@example.org>` is two addresses. Both fields are
  always lists, even for one. The author rows read `Author[] + Author-email[]`: a consumer takes each
  `Author` name, then the display name of each address. An address whose display name repeats an
  `Author` name is the same person, not a second author. An address with no display name
  (`ada@example.org`) gives no name, so it adds no author. `Project-URL` becomes
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
- RIS and EndNote tagged are line formats. A consumer reads one record into a tree: each tag is a
  key (RIS `TI`, EndNote `%T` as `T`, and `%7` as `_7`, since a key cannot start with a digit), the
  value is the text after the tag. `AU`, `A1`, `KW` and `UR` in RIS, and `%A` and `%K` in EndNote, are always lists,
  even when the tag appears once. Any other tag that repeats counts once, by its first occurrence.
  A `%K` tag may also hold continuation lines, one keyword per line, as Zotero writes it: the parser
  splits them, so `K[]` holds one keyword each. Neither format has a tag for a software version, so
  `ET` and `%7` (edition) carry it by convention; Zotero's RIS translator reads `ET` as `versionNumber` for
  a computer program. Older RIS exporters write `A1` for authors and `Y1` for the date, so the author
  rows read `AU[] + A1[]` and `datePublished` reads `PY | Y1`. RIS `PY` is a year and `Y1` and `DA` are
  `YYYY/MM/DD/other`, so for `datePublished` the consumer cuts an ISO date to its first four digits;
  Zotero writes the full date to EndNote `%D`.
  EndNote's tag table calls `%R` the DOI; Zotero's reader takes it as `type`.
  Neither format has a CodeMeta crosswalk; the rows cite the tag lists they were read from.
- Wikidata: the root is the entity object of `Special:EntityData/Q<id>.json`. A statement is an
  element of `claims.P<n>`, with its value under `mainsnak.datavalue.value`: a string, an object
  with `id` for an item, or an object with `time` for a date. A deprecated statement is skipped.
- RO-Crate and Croissant are JSON-LD, read as written, not expanded or compacted. An RO-Crate keeps
  its entities in `@graph`, so its paths start at the root data entity, `@graph[@id=./]`. A crate
  whose root `@id` is not `./` (the descriptor's `about.@id` names it) reads no value from these rows.
  Before resolving a path, the consumer replaces each reference among the root entity's property
  values and list elements (an object whose only key is `@id`, such as
  `{"@id": "https://orcid.org/0000-0002-1825-0097"}`) with the `@graph` entity of that `@id`, one
  level deep; a reference with no entity stays as it is. An entity keeps its `@id`, so
  `author[].givenName` reads the Person entity, and `author[].@id` and `license[].@id` read the
  same URL either way. A Croissant file holds its people in place, under `creator`. In both, a
  property with one value may be written bare, without a list: the consumer reads `author`,
  `creator`, `contributor`, `identifier`, `license` and `publisher` as lists. On a list that holds
  both strings and objects, a path such as `license[].@id | license[]` reads only the objects. A
  `keywords` value may be one string of keywords separated by commas: the consumer splits it after
  resolving the path, not while reading the file. An `@id` that starts
  with `#`, such as `#author-1`, is a local id, not an ORCID. Neither format has a CodeMeta
  crosswalk; the rows cite the specifications. The rows are for reading: a crate writer puts each
  object it writes into `@graph` as an entity and links it from the root by reference. The `ro-crate` and `croissant` vectors in
  `mapping-vectors.json` give a file as `raw_input` and the tree these rules make from it as
  `document`.

Every row in an export has been checked by a person: `crosswalk:` and `curated:` rows alike.
Rows a tool proposed but nobody checked never go in an export.

A (format, term) pair appears at most once. The schema cannot enforce uniqueness by
those two fields, so the consumer checks it.

`codemeta-drift export` writes the rows by format, in the order `cff-1.2.0`, `codemeta`,
`zenodo`, `pep621`, `cargo`, `npm`, `pkg-info`, `r-description`, `julia`, `bibtex`, `datacite`, `setup-py`, `ruby-gem`, `maven`, `cpan-meta-2`, `nuget`, `pubspec`, `cabal`, `typst`, `quarto`, `github`, `figshare`, `bio-tools`, `leiningen`, `octave`, `publiccode-0.8`, `swmath`, `spdx-2.3`, `codemeta-2`, `dcat-3`, `doap`, `wikidata`, `ris`, `endnote`, `gitlab`, `code-json-2.0`, `ro-crate`, `croissant`, and within a format in the order `name`, `version`, `author`,
`author.givenName`, `author.familyName`, `author.@id`, `contributor`, `contributor.givenName`,
`contributor.familyName`, `contributor.@id`, `license`, `identifier`, `swhid`, `codeRepository`,
`description`, `keywords`, `datePublished`, `publisher`, `resourceType`. The same inputs give the same bytes, so a consumer
can pin the file's sha256. The header's `generator.version` is one of those inputs: a new
codemeta-drift release changes the bytes even when no row changes. A consumer must not depend on the row order.

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
`developer[].@id` even when only the maintainer has one, so one person's ORCID never lands on another.

The schema's `path` pattern accepts exactly this grammar.

`mapping-vectors.json`, in the package beside `mapping.schema.json`, lists cases of `path`, `document`
and `expected`. `expected` is the list of values the path resolves to in `document`, in document order,
from the first alternative that yields any value. A consumer vendors the file with the schema and runs
every case through its own resolver, so the copies of the grammar stay in step.
Its `schema_version` is the mapping schema whose grammar the cases need.
Cases with `raw_input` also test parsing: its `format` names the parser and its `text` is the source
file content. Parse that text and compare the resulting tree to `document` before resolving `path`.
The PKG-INFO cases cover comma separation, quoted names, company suffixes and `et al.`.
The resolver tests alone do not check those parser rules.

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

1. Read `schema_version` first. A major it doesn't know is an error ([citesync](https://github.com/simonvanlierde/citesync), the first consumer, exits 3).
2. Validate the file against the schema it vendors beside it, and update the two together:
   a relaxed pattern, such as the `@` keys of schema 1.4, fails an older vendored schema.
   Schema 1.5 only adds format ids, so a 1.5 file passes the 1.4 schema. Schema 1.6 relaxes the
   path pattern for `+` and prefixed keys, so a 1.6 file fails the older schemas.
   Schema 1.7 adds the `ris`, `endnote`, `gitlab` and `code-json-2.0` format ids, the `publisher` and `resourceType` terms and the `context_terms` list, so a 1.7 file
   passes the 1.6 schema, but the `hub` of 0.6.0 refuses it. Its PKG-INFO author rows read `Author[] + Author-email[]`, so
   the parser must keep both as lists. Schema 1.8 adds the `ro-crate` and `croissant` format ids and
   lets a filter value hold `/`, so a 1.8 file fails the 1.7 schema, and the `hub` of 0.7.2 refuses it. Update the
   resolver too, and run `mapping-vectors.json` through it: since 1.6, `[k=v]` also matches a list
   that holds `v`.
3. Ignore rows for formats and terms it doesn't use, and fields it doesn't know.
4. For each format it reads, a missing row for a term it uses is an error (citesync exits 3). A format
   that starts at a later tag, such as `gitlab` from 4.0, has no rows in an older tag's file: read it from
   a file for that tag or later.
   A row with `path: null` is not missing: the format has no place for that term.
5. Treat two rows for the same (format, term) as an error.

## SSSOM spokes

The [crosswalk hub](crosswalk-hub.md) exports SSSOM 1.0 TSV spokes from this JSON file.
The JSON contract stays unchanged. The spokes use `skos:relatedMatch`, because these
paths identify corresponding fields without proving that their values or meanings match.

The hub uses its own term namespace for person sub-terms and `swhid`. It does not invent
CodeMeta vocabulary terms for them. Both crosswalk and curated rows retain
`semapv:ManualMappingCuration` with their source reason in `comment`.
