# Preview schema changes and mapping pin updates

`watch` compares two downloaded schema directories and prints issue drafts as JSON. It
sends no requests and opens no issues.

```sh
codemeta-drift watch ../codemeta --tag 3.1 \
  --before previous-schemas --after new-schemas \
  --citesync-source ../citesync/src/citesync/MAPPING_SOURCE \
  --latest v0.3.0 --existing issue-titles.json
```

Each directory needs the five files named in
[`SCHEMA_FILES`](../src/codemeta_drift/conformance.py): CFF, pyproject, package.json and
Cargo, plus the [verified Zenodo structural subset](../tests/fixtures/schemas/zenodo.json). Both snapshots must come from the same sources. The command reads the curated
mapping from the selected CodeMeta tag, then checks its paths against the new schemas.
It lists broken mapped paths and new declared properties that have no row. Local refs (including numeric array indices),
combined schemas and array item properties are followed; recursive schemas stop at the
first repeated node. Tuple arrays use both draft-07 `items` and modern `prefixItems`.
Mapped array containers and filter keys count as covered fields. Pattern properties and arbitrary external refs do not yield a
finite list of new field names, so this preview does not enumerate them.

`issue-titles.json` is a JSON list of titles from both destination repositories, including
closed issues. Supply `[]` for the first preview. Each draft has `repo`, `title` and `body`.
Schema findings get a stable fingerprint in the title. A second preview with the same
findings and existing titles emits no duplicate. Closed titles also suppress a draft;
closing an issue must not make the next run reopen it.

The pin check reads the `tag` line in citesync's `MAPPING_SOURCE`. It drafts a citesync
issue when that stable release tag is older than `--latest`. Equal and newer pins get
no issue. Release tags must use `vMAJOR.MINOR.PATCH` or `MAJOR.MINOR.PATCH`; arbitrary refs
and prereleases are errors because this preview cannot infer their release order.

The weekly [schema watcher workflow](../.github/workflows/schema-watch.yml) polls the
existing public schema sources, CFF's latest release, CodeMeta's tags, the latest stable
codemeta-drift release and citesync's pin. It uploads the draft JSON as an artifact. To
run the same read-only poll locally:

```sh
uv run python -m codemeta_drift.poll --out schema-watch.json
```

Publishing is opt-in. The workflow publishes only when the `MAPPING_WATCH_TOKEN` repository
secret is configured with issue access to both codemeta-drift and citesync. It reads all
issue pages, including closed issues, before creating any missing drafts. Calls are spaced
one second apart. The workflow's concurrency group serializes runs. A local
`--publish` run uses `gh` credentials and must not run beside another publisher.

Only the latest numeric CodeMeta tag gets a missing-export draft; older unsupported tags
do not each open an issue. The five bundled schema files remain the baseline until they
are deliberately refreshed. Draft fingerprints suppress repeat reports against that baseline.

Zenodo uses [verified structural path coverage](zenodo-schema.md), not a complete
public JSON Schema. Changes to the importer source produce review drafts; they do
not automatically modify that subset or the mapping.

Run the [offline change-and-recovery example](schema-recovery.md) to induce a rename,
deduplicate its review and apply an explicit synthetic approval without changing a real pin.
