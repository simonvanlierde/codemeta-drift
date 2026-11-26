---
description: "How a consumer reads each metadata format into the tree the mapping export's paths address, and the values it converts after."
---

# Read each format's paths

This page says how to read each non-tree format into the tree a
[path](mapping-export.md#path-grammar) addresses. Formats not listed need nothing more.

After resolving, the consumer converts values a path can't: SPDX ids versus licence URLs, bare
versus URL ORCIDs and DOIs, person-name strings, and `git+` prefixes on repository URLs. It also
handles Cargo workspace inheritance, and npm's `author` and `repository` as strings or objects.

## Tree formats with extra rules

- **CFF.** The CodeMeta family name is `name-particle`, `family-names` and `name-suffix` joined by
  spaces, each only when present. Antonie van Leeuwenhoek (`name-particle: van`) has the family name
  `van Leeuwenhoek`, and a `Jr.` suffix ends it.
- **R DESCRIPTION.** `Authors@R` becomes a list of persons with `given`, `family`, `role` and
  `comment`, where `comment` is a mapping (`c(ORCID = "...")`). `role` is a list, so `[role=aut]`
  matches `c("aut", "cre")`. No path reads the free-text `Author` field.
- **Julia.** An `authors` element is `Name` or `Name <email>`. Both name sub-terms read that string,
  and the consumer splits it.
- **DataCite.** Paths start inside `data.attributes` of the REST API JSON, not the XML, so the DOI
  is `doi`.
- **SPDX.** Paths address the JSON form: a package is an element of `packages`, with keys such as
  `versionInfo`. The crosswalk cells use tag-value names (`PackageName`), which are not JSON keys.
  With several packages, read the one SPDXRef-DOCUMENT's `DESCRIBES` relationship names.
- **Wikidata.** The root is the entity of `Special:EntityData/Q<id>.json`. A statement is an element
  of `claims.P<n>`, with its value under `mainsnak.datavalue.value`: a string, an object with `id`
  for an item, or an object with `time` for a date. Skip deprecated statements.

### Composer

Read the root object of [composer.json](https://getcomposer.org/doc/04-schema.md) as JSON.
The name includes the vendor prefix. An author has one full name, which the consumer splits
if it needs name parts. An array of licences offers alternatives. A string may contain an SPDX
expression. The path reads the field as one string or one array.

The package registry or VCS often supplies the version and source URL. The mapping reads
only the values in the supplied object and uses `source.url` for the repository. The
project homepage and support links are separate. A consumer that needs a date converts the
UTC release time in `time`.

## Line and key-value formats

- **Cabal.** Field names are lower case, and each top-level field is a key holding its text. A
  section is an element of a list named after it, with its first argument as `kind`:
  `source-repository head` is read at `source-repository[kind=head].location`.
- **Octave.** DESCRIPTION has `Name: value` lines. A line starting with a space continues the value,
  and `#` starts a comment. Field names are lower-cased, so `License` is `license`. Only the first
  of a repeated field counts.

### PKG-INFO

Each field is a key, and a repeated field is a list. `Author` and `Author-email` are always lists.
The parser splits `Author` at commas outside double quotes and trims each piece. A company suffix
(`Inc`, `LLC`, `Ltd`, `GmbH`, `PBC` or `Corp`, with or without a dot) stays with the piece before
it, so `Datadog, Inc.` is one name. A piece that is `et al.` is dropped. `Last, First` reads as two
names unless quoted (`"Smith, Jane"`); the parser drops the quotes.

`Author-email` is an RFC 822 address list, split at commas outside quotes and angle brackets:
`"Smith, Jane" <j@example.org>, Ada Lovelace <ada@example.org>` is two addresses. The author rows
read `Author[] + Author-email[]`: each `Author` name, then each address's display name. A display
name that repeats an `Author` name is the same person. An address without one (`ada@example.org`)
adds no author. `Project-URL` becomes elements with `label` and `url`. The label is normalised per
the [well-known project URLs spec](https://packaging.python.org/en/latest/specifications/well-known-project-urls/):
lower case, no punctuation or whitespace, so `Source Code` matches `sourcecode`.

### RIS and EndNote

Each tag is a key: RIS `TI`, EndNote `%T` as `T`, and `%7` as `_7` (a key can't start with a digit).
The value is the text after the tag. RIS `AU`, `A1`, `KW` and `UR`, and EndNote `%A` and `%K`, are
always lists. Any other tag counts once, by its first occurrence. A `%K` tag may hold continuation
lines, one keyword each, as Zotero writes it; the parser splits them into `K[]`.

`ET` and `%7` (edition) carry the version by convention. Older RIS exporters write `A1` for authors
and `Y1` for the date, so the author rows read `AU[] + A1[]` and `datePublished` reads `PY | Y1`.
`PY` is a year, and `Y1` and `DA` are `YYYY/MM/DD/other`: cut an ISO date to its first four digits.
EndNote's tag table calls `%R` the DOI, but Zotero reads it as `type`.

### Debian

Read a source tree's `debian/` directory into one tree:

- `control`: the first stanza of `debian/control`, the source package.
- `packages`: its other stanzas, one per binary package, as a list.
- `changelog`: the stanza `dpkg-parsechangelog` prints for the newest `debian/changelog` entry.
- `copyright`: the header stanza of a copyright-format 1.0 `debian/copyright`.
- `upstream`: the `debian/upstream/metadata` YAML mapping (DEP-12).

A missing file leaves its key out. Field names are case-insensitive (Policy 5.1); the parser
capitalises each hyphen-separated part, so `HomePage` is read at `Homepage`. A line starting with a
space or tab continues the field. The parser keeps its lines without that first space, so a space
and a full stop (an empty line of the value) stays `.`. A `#` line in `debian/control` is a comment
and is dropped.

Read the first line of `License` (the short name) and of `Description` (the synopsis). Map
copyright-format licence names to SPDX ids (`Expat` is `MIT`), and cut an
`[epoch:]upstream[-revision]` version to its upstream part. Never run `debian/rules`.

## XML formats

- **Every XML format.** The namespace is ignored.
- **Maven and NuGet.** The tree starts at `project` (Maven) or `package.metadata` (NuGet). An
  element the schema lets repeat is a list under its wrapper even when it occurs once
  (`developers.developer[]`). An attribute is an `@` key (`repository.@url`), and an element with
  attributes reads its text at its own path. Resolve a Maven `${...}` value first.
- **SPASE.** The tree is the content of `Spase.Software`, so paths start at its children
  (`ResourceHeader.ResourceName`). With several Software resources, read the first.
  `AccessInformation`, `AccessURL`, `Contact` and `Role` are always lists, so
  `Contact[Role=Contributor]` matches a contact whose roles include Contributor. A Contact holds
  only `PersonID`, an id in another document; no path follows it. `PublicationInfo.Authors` is one
  string of `Family, Given` names separated by semicolons: split it. Dates are xsd:dateTime; keep
  the date.

### MODS

Read as xmltodict reads it. The tree starts at `mods`; in a `modsCollection` each `mods` is its own
record. Every element is a list, even when it occurs once. An attribute is an `@` key, `xlink:href`
keeps its prefix (`@xlink:href`), and `xsi:` attributes are dropped. An element with attributes is
an object with its trimmed text under `#text`. A path ending there, such as `identifier[@type=doi]`,
gives the object; take its `#text`. The parser gives each `name` a `roleTerm` key listing the text
of every `role.roleTerm`, so `name[roleTerm=aut]` selects the authors. A filter value can't hold a
space, so the `license` row reads every `accessCondition`: keep one typed `use and reproduction` or
untyped. The `name` row reads every `titleInfo`: keep the first, normally the main title.

### ISO 19115-3

The rows are paths in the ISO 19115-1 model, but the XML puts a class element between each property
and its value (`citation/CI_Citation/title/gco:CharacterString`). Read it into the model's tree,
starting at `MD_Metadata`. Each property is replaced by its one child's content:

- a class element (`CI_Citation`, `CI_Individual`) becomes an object of its properties, with the
  class name under `_class`;
- a codelist element becomes its `codeListValue` (`role` reads `author`);
- a value element (`gco:CharacterString`, `gcx:Anchor`, `gco:Date`) becomes its text, an Anchor's
  `xlink:href` dropped;
- an empty property (`gco:nilReason`) is left out.

A property its class lets repeat (`maxOccurs="unbounded"`) is a list even when it occurs once, so
`CI_Citation.date` is a list and `CI_Date.date` is not. Only the first `identificationInfo` counts.
`_class` tells a person from an organisation, and a licence from other constraints. A licence path
reads every `resourceConstraints`: skip those that aren't licences. ISO 19139 records
(`gmd:MD_Metadata`) are not read. A party has one `name` string, which both name rows read and the
consumer splits. The `@id` rows read `partyIdentifier.code`, the bare id (`0000-0002-1825-0097`).
`codeSpace` says it is an ORCID: add `https://orcid.org/`.

## RDF and JSON-LD formats

**DCAT 3 and DOAP.** Read the RDF record (RDF/XML from Zenodo's OAI-PMH or a `.doap` file) as
JSON-LD rooted at the `dcat:Dataset` or `doap:Project` node. Compact it with a context defining only
the prefixes `dcat`, `dcterms`, `owl`, `foaf` and `doap`, so keys are prefixed names such as
`dcterms:title`. A property holds one value or a list, a link is an object with `@id`, and a typed
date may be an object with `@value`.

### RO-Crate and Croissant

Both are JSON-LD, read as written, not expanded or compacted. An RO-Crate keeps its entities in
`@graph`, so paths start at the root data entity, `@graph[@id=./]`. A crate whose root `@id` (named
by the descriptor's `about.@id`) is not `./` reads no value. A Croissant file holds its people in
place, under `creator`.

Before resolving, replace each reference among the root entity's values and list elements with the
`@graph` entity of that `@id`, one level deep. A reference is an object whose only key is `@id`,
such as `{"@id": "https://orcid.org/0000-0002-1825-0097"}`. A reference with no entity stays. An
entity keeps its `@id`, so `author[].@id` reads the same either way.

Read `author`, `creator`, `contributor`, `identifier`, `license` and `publisher` as lists, since one
value may be written bare. An alternative applies to the whole list: when elements hold the value in
different places, `license[].@id | license[].url | license[]` reads only the elements its first
alternative with a value reaches. Skip an object returned by an identifier or license path. Split a
`keywords` string at commas after resolving. An `@id` that is not an ORCID URL, such as `#author-1`
or a ROR id, is not an ORCID.

### Dublin Core

An OAI-PMH `oai_dc` record is a tree rooted at `oai_dc:dc`. Each child element is a list under its
prefixed name (`dc:title`) holding its trimmed text. An RDF record is read like DCAT, compacted with
a context defining only `dc`, `dcterms` and `foaf`. Every `dc:` key, `dcterms:creator` and
`dcterms:contributor` are lists. Each row reads `dcterms:` first, then `dc:`. A `dcterms` agent's
name parts are at `foaf:givenName` and `foaf:familyName`. An `oai_dc` creator is one string, which
Zenodo writes `Family, Given`: both name sub-terms read it, split at the first comma. `dc:rights`
and `dc:identifier` mix kinds of value: keep the ones you can convert.

### VIVO

VIVO is RDF in a VIVO instance, and one linked-data response doesn't name the authors. Read the
merged graph of the software individual, its `vivo:Authorship` nodes, their agents with their
`vcard:Individual` and `vcard:Name`, its `vivo:DateTimeValue` and its publisher. Fetch each IRI or
run one SPARQL CONSTRUCT. Frame the graph as JSON-LD on `"@type": "obo:ERO_0000071"` with `"@embed":
"@always"`. The frame's context defines:

- the prefixes `vivo` (`http://vivoweb.org/ontology/core#`), `obo`
  (`http://purl.obolibrary.org/obo/`), `bibo` (`http://purl.org/ontology/bibo/`), `vcard`
  (`http://www.w3.org/2006/vcard/ns#`) and `rdfs` (`http://www.w3.org/2000/01/rdf-schema#`);
- the term `Authorship` for `vivo:Authorship`;
- `"@container": "@set"` for `vivo:relatedBy`, `vivo:relates`, `vivo:orcidId` and `obo:ARG_2000028`.

Then drop from each `vivo:relates` the reference back to the root, and sort `vivo:relatedBy` by
`vivo:rank`, unranked last. Without the `Authorship` term the author filter matches nothing, so a
consumer that skips this reads no authors, never wrong ones. An author is a `foaf:Person`, with its
name under `obo:ARG_2000028`, or a bare `vcard:Individual`. The name rows join both with `+`; read
names per author element. Cut `vivo:dateTime` to the precision `vivo:dateTimePrecision` gives.

## Code, not data

- **setup.py and Ruby gems.** Read the literal arguments of `setup()` with a Python parser, or load
  a gemspec with `Gem::Specification.load`, in a throwaway environment, never on the host. Read a
  gem's `version` as a string.
- **Leiningen.** project.clj is Clojure code: never run `lein` or `load-file` on it. Read it with a
  Clojure reader with `*read-eval*` off. Take the first `(defproject NAME VERSION :key value ...)`
  form as a map: `name` and `group` from NAME, `version` from the second element, and each `:key`
  without its colon. Skip a value written as an unquote (`~`).
