---
description: "Which .zenodo.json paths Zenodo's GitHub importer reads, checked against its schema code, and the limits of that check."
---

# Zenodo path coverage

Zenodo's GitHub importer reads `.zenodo.json` through `LegacySchema`, then
`MetadataSchema`. We checked this chain at
[zenodo-rdm commit 93fe9f4](https://github.com/zenodo/zenodo-rdm/tree/93fe9f413d7fffc00d8207911c57dad2df9a2392/site/zenodo_rdm).
The [current help example](https://help.zenodo.org/docs/github/describe-software/zenodo-json/)
confirms `version`, creators, typed contributors and related identifiers.

The [bundled structural subset](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/fixtures/schemas/zenodo.json) is locally
authored. It records the field paths the reviewed mapping uses and their array
structure. Its `x-source` names the reviewed commit and the Git blob hashes
of the importer and deserializer files. The [snapshot manifest](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/fixtures/schemas/SOURCES)
records the subset's SHA-256 hash.

This is not an official Zenodo JSON Schema or a deposit validator.
It does not check required deposit fields, ORCID checksums, licences, contributor
vocabularies or every field the service accepts. Read the importer source before
mapping a field outside this subset. The mapping filters related identifiers by `scheme`. Zenodo
ignores that field and infers the scheme from the value.
The poller reads the importer source; it never runs or copies it.

Path checks detect the old crosswalk's uppercase `creators[].ORCID`, bare `id`
and `related_identifiers.isSupplementTo` paths. The reviewed mapping already uses
`creators[].orcid`, `doi` and filtered related-identifier lists.

The poller checks the three upstream blob hashes. A changed file produces a
review draft. A missing file (HTTP 404) also produces a review draft, so a renamed
importer does not stop the other checks. Other HTTP failures still
stop the poll before publication. Existing titles, including closed ones, suppress repeats.
The baseline is not refreshed automatically: inspect the changed
source, update the subset if needed, and record the reviewed hashes.
A changed file does not always mean a mapped field changed.

The reviewed commit does not show which commit the live Zenodo service runs.
