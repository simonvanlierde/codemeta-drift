# Develop codemeta-drift

You need [uv](https://docs.astral.sh/uv/), [just](https://just.systems) and
[prek](https://github.com/j178/prek).

```sh
uv sync
uv tool install prek   # once per machine
prek install           # git hooks
just check             # lint, types, tests and the dependency audit (needs network)
just hooks             # the YAML, Markdown, workflow and citation checks CI also runs
```

## Mutation tests

`just mutation` changes `checks.py`, `export.py` and `conformance.py` one step at a time.
It fails when the tests miss a changed behaviour. A mutation that cannot alter behaviour
belongs in [`tests/mutation-baseline.txt`](../tests/mutation-baseline.txt), with its reason.
The command also fails when tests catch a listed mutation, so the baseline stays current.
CI does not run this command.

## Update expected findings

The [fixtures](../tests/fixtures/) are unmodified CodeMeta 3.1 and 4.0 files. Each snapshot
has a `.expected` file containing the findings the checker should report.

When you intentionally change that output:

1. Inspect the change and confirm the new findings are correct.
2. Regenerate the expected output:

   ```sh
   uv run codemeta-drift tests/fixtures/<tag> > tests/fixtures/<tag>.expected
   ```

   Exit code 1 is expected: both snapshots contain disagreements.
3. Review the diff before committing the expected file.

See [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for commit and sign-off rules.
