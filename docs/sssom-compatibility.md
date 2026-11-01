# SSSOM validation and CodeMeta compatibility

The hub writes a SSSOM table of field correspondences. It uses local hub identifiers
and `skos:relatedMatch`; it does not assert that field values can be copied unchanged.

## Validate an export

From the repository root:

```sh
uv run codemeta-drift hub sssom examples/mapping-3.1.json --out spokes.sssom.tsv
uvx --python 3.12 --from sssom==0.4.21 sssom validate spokes.sssom.tsv
```

The second command runs the pinned [SSSOM Python reference tool](https://mapping-commons.github.io/sssom-py/cli/commands/#sssom-validate)
in a separate tool environment. It checks the JSON schema, prefix-map completeness and
CURIE syntax. It does not require a runtime dependency in codemeta-drift.

Checked on 2026-11-01 with the bundled mapping for CodeMeta 3.1: validation passed,
and the reference parser retained all 119 rows across eleven formats and the set's title,
version and curator ORCID. The parser rejects
an export whose `field:` and `format:` prefixes have the same URI base. The hub uses
separate `#field/` and `#format/` bases, with a regression test for that requirement.

This check establishes that this reference tool can read the export. It does not validate
the meaning of a mapping or certify conformance with CodeMeta's methodology.

## Compare with CodeMeta's methodology

This comparison uses CodeMeta's experimental `sssom-methodology` branch at
[`5f192575310181535e83ea6259d156723775ad86`](https://github.com/codemeta/codemeta/tree/5f192575310181535e83ea6259d156723775ad86/crosswalks-sssom).
Its [README](https://github.com/codemeta/codemeta/blob/5f192575310181535e83ea6259d156723775ad86/crosswalks-sssom/README.md)
describes the intended relationships and generation steps. Its
[template](https://github.com/codemeta/codemeta/tree/5f192575310181535e83ea6259d156723775ad86/crosswalks-sssom/template)
contains a CSV authoring sheet and separate YAML metadata.

| Aspect | CodeMeta methodology | This hub |
| --- | --- | --- |
| Input | CSV authoring sheet and separate YAML metadata | Validated curated mapping JSON |
| Direction and identifiers | Source vocabulary terms to CodeMeta terms; hierarchy uses `/` | Local hub terms to format paths, including arrays, filters and alternatives |
| Relationships | Curator selects exact, close, broader, narrower or part-of relationships | Every exported relation is `skos:relatedMatch` |
| Combined fields | A formula extension describes how source terms combine | Paths identify fields; parsers and normalization handle values elsewhere |
| Mapping-set metadata | Template includes date, description, provider, license and a proposed w3id | Set id, title, description, version, curator ORCID, provider, Apache-2.0 license and explicit CURIE map; no w3id |

The files serve related purposes, but the hub output cannot be used as a replacement
for the upstream authoring sheet without translation and semantic review. Inverting
a row does not turn its local hub term into an official CodeMeta vocabulary identifier.

## Remaining work before an upstream offer

1. Review a small overlapping crosswalk with maintainers. Agree how local compound terms
   and format paths should map to their identifiers and hierarchy.
2. Agree whether the identifiers move to a w3id namespace. The term, field and format
   identifiers now resolve on the [coverage page](https://simonvanlierde.com/codemeta-drift/),
   so a w3id redirect needs no new targets.
3. Preserve the distinction between field correspondence and value conversion. Any
   stronger relationship or combined-field rule needs evidence for that particular row.

The discussion in [CodeMeta #487](https://github.com/codemeta/codemeta/issues/487)
considers separating crosswalk maintenance. It does not establish adoption of this hub
or agreement to replace the existing methodology. The CSV crosswalk export remains
available for consumers of CodeMeta's existing table layout.
