---
description: "Compare downloaded format schemas with the mapping, draft review issues, and check that citesync's mapping pin is current."
---

# Preview schema changes and mapping pin updates

`watch` compares two downloaded schema directories and prints issue drafts as a
[JSON report](checks.md#read-json-output). It sends no requests and opens no issues.

```sh
codemeta-drift watch ../codemeta --tag 4.0 \
  --before previous-schemas --after new-schemas \
  --citesync-source ../citesync/src/citesync/MAPPING_SOURCE \
  --latest v0.9.0 --existing issue-titles.json
```

Only five of the export's formats have a schema check. Each directory needs their files, named in
[`SCHEMA_FILES`](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/conformance.py): CFF, pyproject, package.json and
Cargo, plus the [verified Zenodo structural subset](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/fixtures/schemas/zenodo.json). Both snapshots must come from the same sources. The command reads the reviewed
mapping from the selected CodeMeta tag, then checks its paths against the new schemas.
It lists broken mapped paths and new declared properties that have no row. New tables under pyproject's `tool`
need no row: they configure tools and hold no metadata. Local refs (including numeric array indices),
combined schemas and array item properties are followed; recursive schemas stop at the
first repeated node. Tuple arrays use both draft-07 `items` and modern `prefixItems`.
Mapped array containers and filter keys count as covered fields. Pattern properties and
external refs give no finite list of field names, so the preview does not enumerate them.

`issue-titles.json` is a JSON list of titles from both destination repositories, including
closed issues, or `-` for standard input. Supply `[]` for the first preview. Each draft has `repo`, `title` and `body`.
Schema findings get a stable fingerprint in the title. A second preview with the same
findings and existing titles emits no duplicate, and a closed title suppresses a draft too.

The pin check reads the `tag` line in citesync's `MAPPING_SOURCE`. It drafts a citesync
issue when that stable release tag is older than `--latest`. Equal and newer pins get
no issue. Release tags must use `vMAJOR.MINOR.PATCH` or `MAJOR.MINOR.PATCH`. Other refs and
prereleases are errors: their release order is unknown.

The poll also compares each `sha256` line of `MAPPING_SOURCE` with the hash of that file as
published in codemeta-drift at the pinned tag. A mismatch drafts a citesync issue titled
"Update mapping pin hash for <file> at <tag>" that names the file. A malformed line drafts
"Malformed MAPPING_SOURCE line in citesync: <line>", and a pinned file that the tag does not contain drafts
"Pinned <file> is not in codemeta-drift <tag>". The poll's `--root` option names a codemeta-drift checkout
(default `.`).

The weekly [schema watcher workflow](https://github.com/simonvanlierde/codemeta-drift/blob/main/.github/workflows/schema-watch.yml) polls the
existing public schema sources, the latest CFF and Composer releases, CodeMeta's tags, the latest stable
codemeta-drift release and citesync's pin. When publishing is set up, it opens the drafts as issues.
[Development](development.md#schema-watcher-workflow) covers running the poll locally and
publishing.

Only the latest numeric CodeMeta tag gets a missing-export draft. The five bundled schema files
stay the baseline until refreshed, and draft fingerprints suppress repeat reports against it.

Zenodo has no complete public JSON Schema, so the watcher uses [verified structural path coverage](zenodo-schema.md).
A change to the importer source produces a review draft; it does not modify the subset or the mapping.

The [offline change-and-recovery example](schema-recovery.md) induces a rename, deduplicates its review
and applies a synthetic approval. It changes no real pin.
