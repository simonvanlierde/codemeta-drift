---
description: "Validate the hub's SSSOM export with the reference tool, and how it compares with CodeMeta's own SSSOM methodology."
---

# SSSOM validation and CodeMeta compatibility

The [hub](crosswalk-hub.md) writes an SSSOM (Simple Standard for Sharing Ontological Mappings) table
of field correspondences, from format fields to CodeMeta terms. A row takes the relation CodeMeta's own
sheet gives it where the hub reads the same field (29 rows across DataCite, Zenodo, BibTeX and swMATH),
and is `skos:relatedMatch` otherwise.

## Validate an export

From the repository root:

```sh
just sssom-validate
```

The recipe writes each bundled mapping (CodeMeta 3.1 and 4.0) to a temporary file with
`codemeta-drift hub sssom`, then runs the pinned
[SSSOM Python reference tool](https://mapping-commons.github.io/sssom-py/cli/commands/#sssom-validate)
(`uvx --python 3.13 --from sssom==0.4.21 sssom validate`) in a separate tool environment.
It checks the JSON schema, prefix-map completeness and CURIE syntax, and needs network
access for `uvx`.

The reference parser rejects an export whose `field:` and `format:` prefixes share a URI base.
The hub's prefixes expand to `https://w3id.org/codemeta-drift/#field/` and `#format/`. See the [crosswalk hub](crosswalk-hub.md).

A pass means the reference tool can read the export. It says nothing about whether a mapping is right or
whether the export follows CodeMeta's methodology.

## Compare with CodeMeta's methodology

This comparison uses CodeMeta's experimental `sssom-methodology` branch at
[`5f192575310181535e83ea6259d156723775ad86`](https://github.com/codemeta/codemeta/tree/5f192575310181535e83ea6259d156723775ad86/crosswalks-sssom).
Its [README](https://github.com/codemeta/codemeta/blob/5f192575310181535e83ea6259d156723775ad86/crosswalks-sssom/README.md)
describes the intended relationships and generation steps. Its
[template](https://github.com/codemeta/codemeta/tree/5f192575310181535e83ea6259d156723775ad86/crosswalks-sssom/template)
contains a CSV authoring sheet and separate YAML metadata.

| Aspect | CodeMeta methodology | This hub |
| --- | --- | --- |
| Input | CSV authoring sheet and separate YAML metadata | Validated reviewed mapping JSON |
| Direction and identifiers | Source vocabulary terms to CodeMeta terms; hierarchy uses `/` | The same direction: format fields to CodeMeta terms. A person sub-term's object is its own property, with the person in `object_label`. A subject keeps the format's complete path, with arrays, filters and alternatives |
| Relationships | Curator selects exact, close, broader, narrower or part-of relationships | The sheet's relation as a SKOS mapping predicate where the hub reads the same field (see [Relations](#relations)); `skos:relatedMatch` otherwise |
| Combined fields | A formula extension describes how source terms combine | A path joins the fields with ` + `; parsers and normalization handle values elsewhere |
| Mapping-set metadata | Template includes date, description, provider, license and a proposed w3id | Set id, title, description, version, curator ORCID, provider, Apache-2.0 license and explicit CURIE map, all under the w3id base `https://w3id.org/codemeta-drift/` |

The hub output cannot replace the upstream authoring sheet without translation and review. Its
DataCite subjects are the DataCite REST API's JSON keys, such as `creators[].givenName`, where
CodeMeta's DataCite sheet names the elements of the
[kernel 4.6 XML schema](https://schema.datacite.org/meta/kernel-4.6/metadata.xsd), such as `givenName`.
Where CodeMeta has no term (`swhid`, `resourceType`, the person `@id`s), the object stays a hub term.

### Relations

The sheets' `type_relation` values become these predicates, with the field as subject and the CodeMeta
term as object:

| Sheet | Hub |
| --- | --- |
| `exact_match` | `skos:exactMatch` |
| `close_match` | `skos:closeMatch` |
| `more_specific_than` | `skos:broadMatch`: the field is narrower, so the CodeMeta term is its broader match |
| `more_generic_than` | `skos:narrowMatch` |
| `part_of` | `skos:closeMatch`, only where the path joins all the parts (see below) |
| none, or no row for the field | `skos:relatedMatch` |

CodeMeta's generator script writes `skos:narrower` for `more_specific_than` and `skos:broader` for
`more_generic_than`. Those are SKOS's concept-hierarchy properties, not mapping properties, and
`A skos:narrower B` says B is the narrower one, the inverse of what the sheet means. The hub uses SKOS's
mapping properties, which SSSOM expects, in the direction the sheet's README describes.

A `part_of` row with a `combined_mapping` such as `$(year)+$(month)` names the fields that together
make one CodeMeta term. The hub writes the same combination as a path joined with ` + `, such as
`year + month`, and gives it `skos:closeMatch` only when the path is that join. One part alone stays
`skos:relatedMatch`. The hub's BibTeX `datePublished` path is `date | year`, so it stays related.

The Zenodo sheet names keys of a record in Zenodo's REST API, such as `metadata/title`. The hub reads
`.zenodo.json`, which holds that `metadata` object: `title`, `creators[].orcid` and so on. Its
`license` is the id the API nests in `metadata/license/id`.

## Open points

1. Agree with the CodeMeta maintainers how a hierarchical CodeMeta term such as `author/name`
   expands to an IRI, and which identifiers to use for fields with no CodeMeta term.
2. Settle the rows where this hub and CodeMeta's sheets differ, such as DataCite's `publicationYear`
   for `datePublished` and BibTeX's `version` for `softwareVersion`, before giving them a stronger
   relation.
3. Give a stronger relation or a combined-field rule only with evidence for that row.

[CodeMeta #487](https://github.com/codemeta/codemeta/issues/487) discusses separating crosswalk
maintenance. It has not adopted this hub or agreed to replace the existing methodology. The CSV
crosswalk export still follows CodeMeta's existing table layout.
