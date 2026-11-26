---
description: "An offline example: a fictional PEP 621 rename gives one deduplicated review draft, and an explicit approval repairs the mapping."
---

# Run an offline schema change and recovery example

This example renames PEP 621's `project.name` to a fictional `project.display_name`. It runs offline
and edits no installed mapping, consumer file or remote issue.

From a development checkout, preview the change in a new output directory:

```sh
uv run python examples/schema-recovery.py /tmp/codemeta-preview
```

The example first validates the original mapping against its pinned schemas. The
rename then produces one `PATH_NOT_IN_SCHEMA` finding and one schema-review draft.
Repeating the draft calculation with that title, open or closed, produces no duplicate.
Without approval, `mapping.json` and its mapping hash retain the original bytes.

Inspect the [synthetic approval record](https://github.com/simonvanlierde/codemeta-drift/blob/main/examples/schema-recovery-approval.json).
It specifies the format, term, old path, new path and reason. Apply that reviewed
example to a different new directory:

```sh
uv run python examples/schema-recovery.py /tmp/codemeta-repaired \
  --approval examples/schema-recovery-approval.json
```

The repaired mapping passes both its declared JSON Schema and the changed format
schema. It has a curated source reason and an example-only generator label. The old
mapping still passes its original schemas.

Each output directory contains:

- `report.json`: the induced failure, repeated drafts and approval state;
- `drafts.json`: the review that the simulated rename needs;
- `mapping.json`: the original or explicitly repaired mapping;
- `pin.json`: the mapping and contract SHA-256 hashes, CodeMeta tag and generator version.

The example refuses to overwrite an output directory, so use a fresh path for each run. A missing or
malformed approval file is a CLI error and creates no output. The test runs both modes and checks hashes,
deduplication, validation and that the original mapping is kept. It also rejects an approval for a
different change.

## Check a pinned consumer

citesync vendors the mapping and pins its hashes in `src/citesync/MAPPING_SOURCE`. To see
what a rename means for it, run its tests in a citesync worktree twice:

1. At its pin, unchanged. The rename touches only the drafts, so every test passes.
2. With `mapping.json` from the repaired run copied over `src/citesync/mapping-local.json`.
   The pin check fails, and so does every test that reads a PEP 621 `name`, because
   citesync's fixtures still use `project.name`.

The second run is the gate before a repin: the consumer's fixtures must change with the
mapping. citesync's `check_mapping` accepts both outputs and refuses a `schema_version`
with a major other than 1.

The pins in these files are demonstrations. Nothing here repins citesync, releases a package or
publishes an issue.
