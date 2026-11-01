# Run an offline schema change and recovery example

This example renames PEP 621's `project.name` to a fictional `project.display_name`.
It does not claim that PEP 621 changed. It runs entirely offline and never edits
installed mappings, consumer files or remote issues.

From a development checkout, preview the change in a new output directory:

```sh
uv run python examples/schema-recovery.py /tmp/codemeta-preview
```

The example first validates the original mapping against its pinned schemas. The
rename then produces one `PATH_NOT_IN_SCHEMA` finding and one schema-review draft.
Repeating the draft calculation with that title, open or closed, produces no duplicate.
Without approval, `mapping.json` and its mapping hash retain the original bytes.

Inspect the [synthetic approval record](../examples/schema-recovery-approval.json).
It specifies the format, term, old path, new path and reason. Apply that reviewed
example to a different new directory:

```sh
uv run python examples/schema-recovery.py /tmp/codemeta-repaired \
  --approval examples/schema-recovery-approval.json
```

The repaired mapping passes both its declared JSON Schema and the changed format
schema. It has a curated source reason and an example-only generator label. The old
mapping still passes its original schemas; no installed consumer is forced to upgrade.

Each output directory contains:

- `report.json`: the induced failure, repeated drafts and approval state;
- `drafts.json`: the review that the simulated rename needs;
- `mapping.json`: the original or explicitly repaired mapping;
- `pin.json`: the mapping and contract SHA-256 hashes, CodeMeta tag and generator version.

The example refuses to overwrite an output directory. Use a fresh path for another run.
A missing or malformed approval file produces a CLI error without creating output.
The test runs both modes and checks hashes, deduplication, validation and preservation
of the original mapping. It also rejects an approval for a different change.

These pins are demonstration artifacts. This does not repin citesync, release a package,
verify its actual conversion output or enable live issue publication. A real update
still needs review of the field's meaning, a released artifact and the consumer's tests.
