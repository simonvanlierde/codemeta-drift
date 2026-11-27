---
description: "Validate the hub's SSSOM export with the reference tool, and how it compares with CodeMeta's own SSSOM methodology."
---

# SSSOM validation and CodeMeta compatibility

The [hub](crosswalk-hub.md) writes an SSSOM (Simple Standard for Sharing Ontological Mappings) table
of field correspondences, from format fields to CodeMeta terms. A relation is `skos:exactMatch`
where CodeMeta's own sheet marks it `exact_match` and the hub reads the same field (10 of 14 DataCite
rows), and `skos:relatedMatch` otherwise.

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
| Relationships | Curator selects exact, close, broader, narrower or part-of relationships | `skos:exactMatch` where CodeMeta's sheet marks it `exact_match` and the hub reads the same field (10 of 14 DataCite rows); `skos:relatedMatch` otherwise |
| Combined fields | A formula extension describes how source terms combine | Paths identify fields; parsers and normalization handle values elsewhere |
| Mapping-set metadata | Template includes date, description, provider, license and a proposed w3id | Set id, title, description, version, curator ORCID, provider, Apache-2.0 license and explicit CURIE map, all under the w3id base `https://w3id.org/codemeta-drift/` |

The hub output cannot replace the upstream authoring sheet without translation and review. Its
DataCite subjects are the DataCite REST API's JSON keys, such as `creators[].givenName`, where
CodeMeta's DataCite sheet names the elements of the
[kernel 4.6 XML schema](https://schema.datacite.org/meta/kernel-4.6/metadata.xsd), such as `givenName`.
Where CodeMeta has no term (`swhid`, `resourceType`, the person `@id`s), the object stays a hub term.

## Open points

1. Agree with the CodeMeta maintainers how a hierarchical CodeMeta term such as `author/name`
   expands to an IRI, and which identifiers to use for fields with no CodeMeta term.
2. Check the DataCite rows where this hub and CodeMeta's sheet differ, such as `publicationYear` for
   `datePublished`, and the Zenodo and BibTeX sheets, before giving those rows a stronger relation.
3. Give a stronger relation or a combined-field rule only with evidence for that row.

[CodeMeta #487](https://github.com/codemeta/codemeta/issues/487) discusses separating crosswalk
maintenance. It has not adopted this hub or agreed to replace the existing methodology. The CSV
crosswalk export still follows CodeMeta's existing table layout.
