---
description: "Set up a codemeta-drift checkout: tests, git hooks, fixture updates, the coverage page, the docs site and mutation tests."
---

# Develop codemeta-drift

You need Git, [uv](https://docs.astral.sh/uv/), [just](https://just.systems),
[prek](https://github.com/j178/prek) and [Node](https://nodejs.org/) (its built-in test runner, no packages).

Clone the repository:

```sh
git clone https://github.com/simonvanlierde/codemeta-drift.git
cd codemeta-drift
```

Then, from the checkout:

```sh
uv sync
uv tool install prek   # once per machine
prek install           # git hooks
just check             # lint, types, tests, the site tests and the dependency audit (needs network)
just hooks             # the YAML, Markdown, workflow and citation checks CI also runs
```

The tests use no GitHub token or gh login. Only tests marked `live` reach the network:
`uv run pytest -m live` runs them.

## Coverage matrix and page

`docs/coverage-3.1.md` and `docs/coverage-4.0.md` are generated from each example export and, for
the crosswalks nobody has reviewed, from CodeMeta's files at the export's tag. A test fails while
they are stale. After changing the reviewed rows (`curated-<tag>.json`) or the export, regenerate both tags' exports and
pages with a CodeMeta clone that has the tags:

```sh
for tag in 3.1 4.0; do
  uv run codemeta-drift export ../codemeta --tag $tag --out examples/mapping-$tag.json
  uv run codemeta-drift hub coverage examples/mapping-$tag.json --codemeta ../codemeta --out docs/coverage-$tag.md
done
```

To preview the page, build it with a full CodeMeta clone (the build reads every tag with an
export) and serve the output:

```sh
uv run site/build.py --out _site --codemeta ../codemeta
just docs && cp -R _docs _site/docs
python3 -m http.server -d _site
```

The docs pages are then at `/docs/`. `just docs-serve` previews the docs alone, rebuilt on each
save, without the coverage page's fonts. The `pages` workflow builds both on every pull request
and deploys from main and every Monday. The `docs` workflow fails a pull request on a broken
link or any other warning.
[`site/DESIGN.md`](https://github.com/simonvanlierde/codemeta-drift/blob/main/site/DESIGN.md) holds the design rules.

## Social card

[`docs/assets/og.png`](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/assets/og.png) is the 1200x630 card shown when the coverage page or
the docs are shared. It is rendered from [`docs/og-card.html`](https://github.com/simonvanlierde/codemeta-drift/blob/main/docs/og-card.html). Edit the HTML,
then run:

```sh
just og-card
```

`site/build.py` copies the card into the built page and adds the PNG's hash to the `og:image`
URL (`?v=`). `just og-card` writes the hash into `zensical.toml` for the docs; a test fails if
it is stale.

## Schema watcher workflow

The weekly [schema watcher workflow](https://github.com/simonvanlierde/codemeta-drift/blob/main/.github/workflows/schema-watch.yml)
runs the live tests first, and they can fail the run. One poll then uploads the draft JSON as an
artifact and publishes the drafts. The upload happens even when publishing fails. To run the same
read-only poll locally:

```sh
uv run python -m codemeta_drift.poll --out schema-watch.json
```

Publishing is opt-in. The workflow publishes only when the `MAPPING_WATCH_TOKEN` secret is set in
the `schema-watch` environment, which allows deployments from `main` only and has no reviewers.
`just watch-env` sets it up.

- Keep the token in the environment. Every workflow on every branch can read a repository secret.
- Without the token, a manual run prints a notice that publishing was skipped, and a scheduled run
  fails after uploading the drafts.
- A run started on another branch stops at the environment, so test a branch with the local poll.
- Use a fine-grained token limited to simonvanlierde/codemeta-drift and simonvanlierde/citesync,
  with only Issues: read and write. Both repositories are public, so it needs no Contents
  permission.

The poll reads all issue pages, including closed issues, before it creates any missing drafts, and
spaces issue creations one second apart. The workflow's concurrency group serializes runs. A local
`--publish` run uses `gh` credentials and must not run beside another publisher.

## Mutation tests

`just mutation` tests modified copies of `checks.py`, `export.py`, `conformance.py` and `paths.py`.
It fails when the tests miss a changed behaviour.
List a mutation that cannot alter behaviour, with its reason, in [`tests/mutation-baseline.txt`](https://github.com/simonvanlierde/codemeta-drift/blob/main/tests/mutation-baseline.txt).
The command also fails when tests catch a listed mutation.
CI does not run this command.

## Update expected findings

The [fixtures](https://github.com/simonvanlierde/codemeta-drift/tree/main/tests/fixtures/) are unmodified CodeMeta 3.1 and 4.0 files. Each snapshot
has a sibling file, `3.1.expected` or `4.0.expected`, with the expected findings.

When you intentionally change that output:

1. Inspect the change and confirm the new findings are correct.
2. Regenerate the expected output:

   ```sh
   uv run codemeta-drift tests/fixtures/4.0 > tests/fixtures/4.0.expected
   ```

   Use `3.1` in both paths for the other snapshot. Exit code 1 is expected.
3. Review the diff before committing the expected file.

See [CONTRIBUTING.md](https://github.com/simonvanlierde/codemeta-drift/blob/main/.github/CONTRIBUTING.md) for commit and sign-off rules.
