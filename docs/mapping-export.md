# Mapping export

A mapping export is one JSON file, `mapping-<codemeta-tag>.json`, that says where each CodeMeta
term sits in each metadata format. Tools that keep `CITATION.cff`, `codemeta.json`,
`.zenodo.json` and package manifests in step read it instead of parsing CodeMeta's crosswalk
tables, whose cells are prose and sometimes wrong.

The schema is [`src/codemeta_drift/mapping.schema.json`](../src/codemeta_drift/mapping.schema.json)
(JSON Schema 2020-12). [`examples/mapping-3.1.json`](../examples/mapping-3.1.json) is the
export for CodeMeta 3.1, written by `codemeta-drift export` (see the README).

## Where, not how

A row says where a value sits: CFF `title` is CodeMeta `name`. It doesn't say how the value is
spelled. An SPDX id or SPDX URL, an ORCID URL or bare iD, a DOI with or without `https://doi.org/`,
a person written `"Family, Given"`, a repository URL with `git+` in front: all of that is the
consumer's job, per (format, term). So is any shape a path can't express, such as Cargo's
`.workspace = true` inheritance, or npm's `author` and `repository`, which may be a string or an
object.

## The file

```json
{
  "schema_version": "1.2",
  "codemeta_tag": "3.1",
  "generator": {"name": "codemeta-drift", "version": "0.2.0"},
  "rows": [
    {
      "format": "cargo",
      "term": "keywords",
      "path": "package.keywords",
      "source": "curated:the cell says package.keyword; Cargo's key is package.keywords",
      "see_also": "https://github.com/codemeta/codemeta/issues/...",
      "comment": "free text"
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

- `format` is a stable id: `cff-1.2.0`, `codemeta`, `zenodo`, `pep621`, `cargo` or `npm`. A
  format whose versions differ puts the version in the id.
- `term` is one of the eleven terms `name`, `version`, `author`, `contributor`, `license`,
  `identifier`, `swhid`, `codeRepository`, `description`, `keywords` and `datePublished`, or a person
  sub-term of `author` or `contributor`: `.givenName`, `.familyName` and `.@id` (the ORCID). A
  sub-term names the term it sits under, because `contributor.givenName` sits somewhere else
  than `author.givenName`. `identifier` is the DOI. `swhid` is the
  [Software Heritage identifier](https://www.swhid.org/), such as
  `swh:1:dir:d198bc9d7a6bcf6db04f476d29314f157507d505`. CodeMeta has no term of its own for it:
  codemeta.json holds it in `identifier`, beside the DOI, so both codemeta rows have the path
  `identifier` and the consumer picks each value out by its spelling.
- `path` is where the value sits, in the grammar below, or `null` when the format has no place
  for it (Cargo has no DOI). A `null` row is a real answer, not a missing row.
- `source` says where the row comes from. `crosswalk:<file>@<tag>` means the path is that
  crosswalk's cell, for example `crosswalk:crosswalks/Zenodo.csv@3.1`. Only two things are added
  to the cell: `[]` when the format keeps authors in a list (`authors` becomes `authors[]`), and
  the author or contributor path in place of CFF's `person.` (`person.given-names` becomes
  `authors[].given-names`). `curated:<reason>` means the row departs from the crosswalk, picks
  one path out of a prose cell, or fills a cell it leaves empty, and says why. An empty cell is
  never read as `null`, because the crosswalks also leave cells empty that the format has.
- `see_also` (optional) is the upstream issue or pull request about the cell the row departs from.
- `comment` (optional) is a note for people. Never read it in code.

CFF stores a name particle and a name suffix apart from `family-names`, and CodeMeta has only
`familyName`. A consumer reads the CodeMeta family name from the three joined by spaces:
`name-particle`, `family-names`, `name-suffix`, each only when present. Antonie van Leeuwenhoek
(`name-particle: van`, `family-names: Leeuwenhoek`) has the family name `van Leeuwenhoek`, and
a `Jr.` in `name-suffix` ends it. The `cff-1.2.0` `author.familyName` row says so in its `comment`.

Every row in an export has been checked by a person: `crosswalk:` and `curated:` rows alike.
Rows a tool proposed but nobody checked never go in an export.

A (format, term) pair appears at most once. JSON Schema can't say that, so a consumer checks it.

`codemeta-drift export` writes the rows by format, in the order `cff-1.2.0`, `codemeta`,
`zenodo`, `pep621`, `cargo`, `npm`, and within a format in the order `name`, `version`, `author`,
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
| `key[k=v]` | each element of the list under `key` whose `k` equals `v` | `identifiers[type=doi].value` |
| `a \| b` | `a` if it exists, else `b`; any number, read left to right | `project.urls.Source \| project.urls.Repository \| project.urls.Homepage` |

- A key is letters, digits, `_` and `-`, and may start with `@` (`author[].@id`). It can't
  start with a digit.
- A filter value is letters, digits, `_`, `.` and `-`.
- Alternatives are separated by exactly one space, `|`, one space.
- There are no list indexes (`a[0]`) and no wildcards.

A person sub-term's path is absolute and starts with the path of its term. CFF `author` is
`authors[]`, so `author.givenName` is `authors[].given-names`. When a format keeps the whole
name in one string, both name sub-terms point at it (Zenodo `creators[].name`), and the
consumer splits it.

The schema's `path` pattern accepts exactly this grammar.

## Compatibility

A **minor** version (1.0 to 1.1) only adds: an optional field, a new format id, a new term or
sub-term, or a relaxed pattern. A consumer that knows 1.0 reads a 1.1 file correctly. The schema
allows fields it doesn't define, in the header, `generator` and each row, so a 1.1 file also
passes the 1.0 schema a consumer vendors.

A **major** version (1.x to 2.0) is anything else: a renamed or removed field, a new required
field, a changed meaning, or a change to the path grammar that an old reader would misread.

New rows, and rows that change path because a crosswalk cell was fixed, are not schema changes.
They come with a new codemeta tag or a new codemeta-drift release.

## What a consumer does

1. Read `schema_version` first. A major it doesn't know is an error ([citesync](https://github.com/simonvanlierde/citesync), the first consumer, exits 2).
2. Validate the file against the schema it vendors beside it.
3. Ignore rows for formats and terms it doesn't use, and fields it doesn't know.
4. For each format it reads, a missing row for a term it uses is an error (citesync exits 2).
   A row with `path: null` is not missing: the format has no place for that term.
5. Treat two rows for the same (format, term) as an error.

## Later: SSSOM

The hub will move to [SSSOM](https://mapping-commons.github.io/sssom/) spokes. Each row field
maps onto one SSSOM column, so the move needs no change to what a row holds: `term` becomes
`subject_id` (`codemeta:<term>`), `format` and `path` become `object_source` and `object_id`,
`source` becomes `mapping_justification` (`semapv:ManualMappingCuration`, since both kinds of row
were checked by a person) with its reason in `comment`, and `see_also` keeps its name.
`predicate_id` isn't stored yet. Most rows are `skos:exactMatch`; the name sub-terms that point
at one name string (Zenodo, Cargo, npm, PEP 621) are not, and need their own predicate then.
