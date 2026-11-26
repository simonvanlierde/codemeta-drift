---
description: "Set up a codemeta-drift checkout: tests, git hooks, fixture updates, the coverage page, the docs site and mutation tests."
---

# Develop codemeta-drift

You need Git, [uv](https://docs.astral.sh/uv/), [just](https://just.systems),
[prek](https://github.com/j178/prek) and [Node](https://nodejs.org/) (its built-in test runner, no packages).

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
just check             # lint, types, tests, the site tests and the dependency audit (needs network)
just hooks             # the YAML, Markdown, workflow and citation checks CI also runs
```

The tests run without your GitHub tokens or gh login, and only tests marked `live` reach the
network: `uv run pytest -m live` runs those.

## Coverage matrix and page

`docs/coverage-3.1.md` and `docs/coverage-4.0.md` are generated from each example export and, for the crosswalks nobody has
reviewed, from CodeMeta's files at the export's tag. A test fails while it is stale. After
changing the curated rows or the export, regenerate both tags' exports and pages with a CodeMeta clone
that has the tags:

```sh
for tag in 3.1 4.0; do
  uv run codemeta-drift export ../codemeta --tag $tag --out examples/mapping-$tag.json
  uv run codemeta-drift hub coverage examples/mapping-$tag.json --codemeta ../codemeta --out docs/coverage-$tag.md
done
```

To preview the page, build it with a full CodeMeta clone, since the build reads every tag with an export, and
serve the output:

```sh
uv run site/build.py --out _site --codemeta ../codemeta
just docs && cp -R _docs _site/docs
python3 -m http.server -d _site
```

The docs pages are then at `/docs/`. `just docs-serve` previews the docs alone, rebuilt on each
save, without the coverage page's fonts. The `pages` workflow builds both on every pull request
and deploys from main and every Monday; the `docs` workflow fails a pull request on a broken
link or any other warning.
[`site/DESIGN.md`](https://github.com/simonvanlierde/codemeta-drift/blob/main/site/DESIGN.md) holds the design rules.

## Mutation tests

`just mutation` tests modified copies of `checks.py`, `export.py`, `conformance.py` and `paths.py`.
It leaves the source files unchanged and fails when the tests miss a changed behaviour.
A mutation that cannot alter behaviour belongs in [`tests/mutation-baseline.txt`](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/mutation-baseline.txt), with its reason.
The command also fails when tests catch a listed mutation, so the baseline stays current.
CI does not run this command.

## Update expected findings

The [fixtures](https://github.com/simonvanlierde/codemeta-drift/tree/main/tests/fixtures/) are unmodified CodeMeta 3.1 and 4.0 files. Each snapshot
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

See [CONTRIBUTING.md](https://github.com/simonvanlierde/codemeta-drift/blob/main/.github/CONTRIBUTING.md) for commit and sign-off rules.
