# Zenodo path coverage

Zenodo's GitHub importer reads `.zenodo.json` through `LegacySchema`, then
`MetadataSchema`. We checked this chain at
[zenodo-rdm commit 93fe9f4](https://github.com/zenodo/zenodo-rdm/tree/93fe9f413d7fffc00d8207911c57dad2df9a2392/site/zenodo_rdm).
The [current help example](https://help.zenodo.org/docs/github/describe-software/zenodo-json/)
confirms `version`, creators, typed contributors and related identifiers.

The [bundled structural subset](../tests/fixtures/schemas/zenodo.json) is locally
authored. It records the field paths used by the curated mapping and their array
structure. Its `x-source` identifies the reviewed commit and the Git blob hashes
of the importer and deserializer files. The [snapshot manifest](../tests/fixtures/schemas/SOURCES)
records the subset's SHA-256 hash.

This is not an official Zenodo JSON Schema or a complete deposit validator.
It does not validate required deposit fields, ORCID checksums, licences, contributor
vocabularies or every field the service accepts. Fields outside this subset need
source review before adding mappings. The related-identifier `scheme` field is
a consumer-side selector; the importer infers the scheme from the identifier value. The importer source is inspected, never executed
or copied into this package.

Path checks now detect the old crosswalk's uppercase `creators[].ORCID`, bare `id`
and `related_identifiers.isSupplementTo` paths. The curated mapping already uses
`creators[].orcid`, `doi` and filtered related-identifier lists.

The poller checks the three upstream blob hashes. A changed file produces a
review draft. Existing titles, including closed ones, suppress repeats. The baseline is not refreshed automatically: inspect the changed
source, update the structural subset if needed, and record the reviewed hashes.
A file change is a review signal, not proof that a mapped field changed.

The source revision is a repository snapshot; it does not prove which commit runs on
the live Zenodo service. No deposit or publication is needed to run these checks.
