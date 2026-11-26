---
description: "How a consumer reads each metadata format into the tree the mapping export's paths address, and the values it converts after."
---

# Read each format's paths

A row's `path` addresses a tree of keys and lists, in the [path grammar](mapping-export.md#path-grammar).
Many formats are not trees, or hold values a path cannot reach alone. This page gives the rules for
those formats: how to read the file into a tree first, and what to convert after resolving the path.
A format with no section here needs nothing beyond the grammar.

The sections follow the export's format order. The `raw_input` cases in `mapping-vectors.json` test
several of these rules: each gives a source file and the tree these rules make from it.

## CFF

CFF stores a name particle and a name suffix apart from `family-names`, and CodeMeta has only
`familyName`. A consumer reads the CodeMeta family name from the three joined by spaces:
`name-particle`, `family-names`, `name-suffix`, each only when present. Antonie van Leeuwenhoek
(`name-particle: van`, `family-names: Leeuwenhoek`) has the family name `van Leeuwenhoek`, and
a `Jr.` in `name-suffix` ends it. The `cff-1.2.0` `author.familyName` row says so in its `comment`.

## PKG-INFO

Each field is a key, and a field that repeats is a list.

`Author` holds the authors who have no email, separated by commas. The
[pyproject.toml spec](https://packaging.python.org/en/latest/specifications/pyproject-toml/#authors-maintainers)
says a name must not contain commas and "Multiple values should be separated by commas", and most
build backends write `Author: A, B`. The parser splits `Author` at commas outside double quotes and
trims each piece. A company suffix (`Inc`, `LLC`, `Ltd`, `GmbH`, `PBC` or `Corp`, with or without a
dot) stays with the piece before it, so `Datadog, Inc.` is one name. A piece that is `et al.` is
dropped. The split loses names that hold a comma, such as `Last, First`: they read as several names.
Quote such a name (`"Smith, Jane"`) to keep it whole, and the parser drops the quotes.

`Author-email` is an RFC 822 address list. The parser splits it at commas outside double quotes and
angle brackets, so `"Smith, Jane" <j@example.org>, Ada Lovelace <ada@example.org>` is two addresses.

Both fields are always lists, even for one. The author rows read `Author[] + Author-email[]`: a
consumer takes each `Author` name, then the display name of each address. An address whose display
name repeats an `Author` name is the same person, not a second author. An address with no display
name (`ada@example.org`) gives no name, so it adds no author.

`Project-URL` becomes elements with `label` and `url`. The label is normalised as the
[well-known project URLs spec](https://packaging.python.org/en/latest/specifications/well-known-project-urls/)
says: lower case, no punctuation or whitespace, so `Source Code` matches `sourcecode`.

## R DESCRIPTION

`Authors@R` becomes a list of person entries with `given`, `family`, `role` and `comment`, where
`comment` is a mapping (`c(ORCID = "...")`). `role` is a list, so `[role=aut]` matches
`c("aut", "cre")`. A package without `Authors@R` has only the free-text `Author` field, which no
path reads.

## Julia

An `authors` element may be a plain `Name` or a `Name <email>` string. Both name sub-terms then come
from that string, and the consumer splits it, as for Zenodo.

## DataCite

Paths start inside `data.attributes` of the REST API's JSON, so the DOI is `doi`. The XML form is
not addressed.

## setup.py and Ruby gems

Both are code, not data. A consumer reads the literal arguments of `setup()` with a Python parser,
or loads a gemspec with `Gem::Specification.load`. Do either in a throwaway environment, never on
the host. A gem's `version` is read as a string.

## Maven and NuGet

pom.xml and .nuspec are XML. The tree starts at `project` (Maven) or `package.metadata` (NuGet),
with the namespace ignored. An element the schema lets repeat (a `developer`, a `license`) is a list
even when it occurs once, under its wrapper (`developers.developer[]`). An attribute is an `@` key
(`repository.@url`), and an element with attributes reads its text at its own path. A Maven value
with `${...}` may need resolving first.

## Cabal

Field names are lower case, and each top-level field is a key holding its text. A section is an
element of a list named after it, with its first argument as `kind`. So `source-repository head` is
read at `source-repository[kind=head].location`.

## Leiningen

project.clj is Clojure code: never run `lein` or `load-file` on it. A consumer reads it with a
Clojure reader with `*read-eval*` off. It takes the first `(defproject NAME VERSION :key value ...)`
form as a map: `name` and `group` from the NAME symbol, `version` from the second element, and each
`:key` without its colon. A value written as an unquote (`~`) is skipped, not evaluated.

## Octave

Octave's DESCRIPTION has `Name: value` lines. A line starting with a space continues the value
before it, and `#` starts a comment. Field names are lower-cased, as Octave's `pkg` does, so
`License` is read at `license`. Only the first of a repeated field counts.

## SPDX

The paths address the JSON form, where a package is an element of `packages` with lower camel case
keys (`versionInfo`). The crosswalk cells use the tag-value names (`PackageName`), which are not JSON
keys. In a document with several packages, the consumer reads the one that SPDXRef-DOCUMENT's
`DESCRIBES` relationship names.

## DCAT 3 and DOAP

Both are RDF. A consumer reads the record (RDF/XML from Zenodo's OAI-PMH or a project's `.doap`
file) as JSON-LD rooted at the `dcat:Dataset` or `doap:Project` node. It compacts it with a context
that defines only the prefixes `dcat`, `dcterms`, `owl`, `foaf` and `doap`, so each key is a prefixed
name such as `dcterms:title`. A property may hold one value or a list, a link is an object with
`@id`, and a typed date may be an object with `@value`.

## Wikidata

The root is the entity object of `Special:EntityData/Q<id>.json`. A statement is an element of
`claims.P<n>`, with its value under `mainsnak.datavalue.value`: a string, an object with `id` for an
item, or an object with `time` for a date. A deprecated statement is skipped.

## RIS and EndNote

Both are line formats. A consumer reads one record into a tree: each tag is a key (RIS `TI`, EndNote
`%T` as `T`, and `%7` as `_7`, since a key cannot start with a digit), and the value is the text
after the tag. `AU`, `A1`, `KW` and `UR` in RIS, and `%A` and `%K` in EndNote, are always lists, even
when the tag appears once. Any other tag that repeats counts once, by its first occurrence. A `%K`
tag may also hold continuation lines, one keyword per line, as Zotero writes it. The parser splits
them, so `K[]` holds one keyword each.

Neither format has a tag for a software version, so `ET` and `%7` (edition) carry it by convention.
Zotero's RIS translator reads `ET` as `versionNumber` for a computer program. Older RIS exporters
write `A1` for authors and `Y1` for the date, so the author rows read `AU[] + A1[]` and
`datePublished` reads `PY | Y1`. RIS `PY` is a year, and `Y1` and `DA` are `YYYY/MM/DD/other`, so for
`datePublished` the consumer cuts an ISO date to its first four digits. Zotero writes the full date
to EndNote `%D`. EndNote's tag table calls `%R` the DOI; Zotero's reader takes it as `type`.

Neither format has a CodeMeta crosswalk; the rows cite the tag lists they were read from.

## RO-Crate and Croissant

Both are JSON-LD, read as written, not expanded or compacted. Neither has a CodeMeta crosswalk; the
rows cite the specifications. An RO-Crate keeps its entities in `@graph`, so its paths start at the
root data entity, `@graph[@id=./]`. A crate whose root `@id` is not `./` (the descriptor's
`about.@id` names it) reads no value from these rows. A Croissant file holds its people in place,
under `creator`.

Before resolving a path, the consumer replaces each reference among the root entity's property
values and list elements with the `@graph` entity of that `@id`, one level deep. A reference is an
object whose only key is `@id`, such as `{"@id": "https://orcid.org/0000-0002-1825-0097"}`. A
reference with no entity stays as it is. An entity keeps its `@id`, so `author[].givenName` reads the
Person entity, and `author[].@id` reads the same `@id` either way. The rows are for reading: a crate
writer puts each object it writes into `@graph` as an entity and links it from the root by reference.

In both formats, a property with one value may be written bare, without a list. The consumer reads
`author`, `creator`, `contributor`, `identifier`, `license` and `publisher` as lists. An alternative
applies to the whole list, not to each element. When the elements hold the value in different places
(strings and objects, or objects with `@id` and objects with only `url`),
`license[].@id | license[].url | license[]` reads only the elements its first alternative with a
value reaches. The identifier and license paths can also return an object itself; the consumer skips
it. A `keywords` value may be one string of keywords separated by commas: the consumer splits it
after resolving the path, not while reading the file. An `@id` that is not an ORCID URL, such as
`#author-1` or a ROR id, is not an ORCID.

## Dublin Core

Dublin Core comes as `oai_dc` XML, which every OAI-PMH repository serves, or as RDF.

An `oai_dc` record is read as a tree rooted at `oai_dc:dc`. Each child element is a key named by its
prefixed name (`dc:title`) holding its trimmed text. Every key is a list, because every element may
repeat.

An RDF record is read like DCAT: JSON-LD rooted at the described resource's node, compacted with a
context that defines only `dc`, `dcterms` and `foaf`. There too every `dc:` key, and
`dcterms:creator` and `dcterms:contributor`, are lists.

Each row reads `dcterms:` first and falls back to `dc:`. DCMI defines no name parts or ORCID for an
agent. A `dcterms` agent's name parts are read at `foaf:givenName` and `foaf:familyName`. An `oai_dc`
creator is one string, which Zenodo writes `Family, Given`, so both name sub-terms point at it and the
consumer splits it at the first comma. `dc:rights` mixes access statements, licence names and licence
URLs, and `dc:identifier` mixes a DOI with other ids: the consumer keeps the values it can convert.

## Debian

The paths address one source tree's `debian/` directory, read into one tree with these keys:

- `control`: the first stanza of `debian/control`, the source package.
- `packages`: its other stanzas, one per binary package, as a list.
- `changelog`: the stanza `dpkg-parsechangelog` prints for the newest entry of `debian/changelog`.
- `copyright`: the header stanza of a copyright-format 1.0 `debian/copyright`.
- `upstream`: the `debian/upstream/metadata` YAML mapping (DEP-12).

A missing file leaves its key out. Field names in these deb822 files are case-insensitive (Policy
5.1). The parser stores each in Policy's spelling, every hyphen-separated part capitalised, so
`HomePage` is read at `Homepage`. A line that starts with a space or tab continues the field before
it. The parser keeps the value's lines, each without that first space, so a line of a space and a
full stop, which stands for an empty line of the value, stays `.`. A line in `debian/control` that
starts with `#` is a comment, which the consumer drops (Policy 5.1).

The consumer reads the first line of `License` (the short name) and of `Description` (the synopsis).
`License` names are copyright-format's own (`Expat`, `GPL-2+`), not SPDX ids, and a version is
`[epoch:]upstream[-revision]`. The consumer maps a licence name to its SPDX id (`Expat` is `MIT`) and
cuts a version to its upstream part. Never run `debian/rules`; a parser of the newest changelog line
gives the same `Version`.

## MODS

MODS is XML, read as xmltodict reads it. The tree starts at `mods`, with the namespace ignored; in a
`modsCollection` each `mods` element is its own record. Every element is a list even when it occurs
once, since nearly every MODS element may repeat. An attribute is an `@` key, and `xlink:href` keeps
its prefix (`@xlink:href`). `xsi:` attributes such as `xsi:schemaLocation` are dropped.

An element with attributes is an object that holds its trimmed text under `#text`. A path that ends
at one, such as `identifier[@type=doi]`, gives that object, and the consumer takes its `#text`.

The parser gives each `name` a `roleTerm` key that lists the text of every `role.roleTerm` in it, so
`name[roleTerm=aut]` selects the authors, as `[role=aut]` does for R. A filter value cannot hold a
space, so the `license` row reads every `accessCondition`: the consumer keeps one typed
`use and reproduction` or untyped. The `name` row reads every `titleInfo`, alternative and translated
titles too, and the consumer keeps the first, which is normally the main title.

## VIVO

VIVO is RDF held in a VIVO instance, not a file. One linked-data response does not name a work's
authors. So a consumer reads the merged graph of the software individual and its `vivo:Authorship`
nodes, their agents with their `vcard:Individual` and `vcard:Name`, its `vivo:DateTimeValue` and its
publisher. It gets that graph by fetching each IRI or by one SPARQL CONSTRUCT.

It frames the graph as JSON-LD on `"@type": "obo:ERO_0000071"` with `"@embed": "@always"`. The
frame's context defines:

- the prefixes `vivo` (`http://vivoweb.org/ontology/core#`), `obo`
  (`http://purl.obolibrary.org/obo/`), `bibo` (`http://purl.org/ontology/bibo/`), `vcard`
  (`http://www.w3.org/2006/vcard/ns#`) and `rdfs` (`http://www.w3.org/2000/01/rdf-schema#`);
- the term `Authorship` for `vivo:Authorship`;
- `"@container": "@set"` for `vivo:relatedBy`, `vivo:relates`, `vivo:orcidId` and
  `obo:ARG_2000028`, so those are always lists.

The parser then drops from each `vivo:relates` the reference back to the root (an object whose only
key is the root's `@id`). It sorts `vivo:relatedBy` by `vivo:rank`, unranked last. Without the
`Authorship` term the author filter matches nothing, so a consumer that skips the rule reads no
authors, never wrong ones.

An author is a `foaf:Person`, whose name sits under `obo:ARG_2000028`, or a bare `vcard:Individual`.
The name rows join both with `+`, so the consumer reads names per author element. `vivo:dateTime` is
a full xsd:dateTime, which the consumer cuts to the precision `vivo:dateTimePrecision` gives.

## SPASE

SPASE is XML. The tree is the content of `Spase.Software`, with the namespace ignored, so paths start
at its children (`ResourceHeader.ResourceName`). A document with several Software resources is read
at the first. Four elements the rows go through are lists even when they occur once:
`AccessInformation`, `AccessURL`, `Contact` and `Role`. So `Contact[Role=Contributor]` matches a
contact whose roles include Contributor.

A Contact holds only `PersonID`, the id of a Person record in another document, where the name and
ORCID are; no path follows it. `PublicationInfo.Authors` is one string, names separated by
semicolons, each `Family, Given`: the consumer splits it. Dates are xsd:dateTime; the consumer keeps
the date.

## ISO 19115-3

CodeMeta's ISO cells are paths in the ISO 19115-1 model. The XML puts a class element between each
property and its value (`citation/CI_Citation/title/gco:CharacterString`), so the consumer reads the
record into the model's tree first.

The tree starts at `MD_Metadata`, with the namespace ignored. Each property is replaced by its one
child's content:

- a class element (`CI_Citation`, `CI_Individual`) becomes an object of its own properties, with the
  class name under `_class`;
- a codelist element becomes its `codeListValue` (`role` reads `author`);
- a value element (`gco:CharacterString`, `gcx:Anchor`, `gco:Date`) becomes its text, an Anchor's
  `xlink:href` dropped;
- an empty property (`gco:nilReason`) is left out.

A property its class lets repeat (`maxOccurs="unbounded"`) is a list even when it occurs once, so
`CI_Citation.date` is a list and `CI_Date.date` is not. Only the first `identificationInfo` counts.
`_class` tells a person from an organisation and a licence from other constraints; no path reads it.
A licence path reads every `resourceConstraints` reference, and the consumer skips those that are
not licences. ISO 19139 records (`gmd:MD_Metadata`) are another tree, which these rows do not read.

A party has one `name` string, so the given and family name rows both read it and the consumer
splits it. The `@id` rows read `partyIdentifier.code`, which is the bare id (`0000-0002-1825-0097`)
once the Anchor's `xlink:href` is dropped. `codeSpace` says it is an ORCID, and the consumer adds
`https://orcid.org/`.
