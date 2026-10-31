# Develop codemeta-drift

You need Git, [uv](https://docs.astral.sh/uv/), [just](https://just.systems) and
[prek](https://github.com/j178/prek).

Clone the repository, then enter its directory:

```sh
git clone https://github.com/simonvanlierde/codemeta-drift.git
cd codemeta-drift
```

From an existing checkout, start here:

```sh
uv sync
uv tool install prek   # once per machine
prek install           # git hooks
just check             # lint, types, tests and the dependency audit (needs network)
just hooks             # the YAML, Markdown, workflow and citation checks CI also runs
```

## Mutation tests

`just mutation` tests modified copies of `checks.py`, `export.py` and `conformance.py`.
It leaves the source files unchanged and fails when the tests miss a changed behaviour.
A mutation that cannot alter behaviour belongs in [`tests/mutation-baseline.txt`](../tests/mutation-baseline.txt), with its reason.
The command also fails when tests catch a listed mutation, so the baseline stays current.
CI does not run this command.

## Update expected findings

The [fixtures](../tests/fixtures/) are unmodified CodeMeta 3.1 and 4.0 files. Each snapshot
has a sibling file, `3.1.expected` or `4.0.expected`, containing the expected findings.

When you intentionally change that output:

1. Inspect the change and confirm the new findings are correct.
2. Regenerate the expected output:

   ```sh
   uv run codemeta-drift tests/fixtures/4.0 > tests/fixtures/4.0.expected
   ```

   This updates the 4.0 fixture; use `3.1` in both paths for the other snapshot.
   Exit code 1 is expected: both snapshots contain disagreements.
3. Review the diff before committing the expected file.

See [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for commit and sign-off rules.
