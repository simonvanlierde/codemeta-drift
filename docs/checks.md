---
description: "The finding codes codemeta-drift reports, the CodeMeta files it compares, its exit codes and its JSON output."
---

# Understand the findings

codemeta-drift compares the files that define CodeMeta and its crosswalks. It matches
terms by name and checks row order, so a renamed term appears as one unexpected term and
one missing term. A problem shared by several crosswalks is reported once, as a group.

## The files it compares

| File | What it is |
| --- | --- |
| `codemeta.jsonld` | The vocabulary: every term and the web address that defines it |
| `codemeta_all.jsonld` | The definitions of CodeMeta's own terms (since 4.0) |
| `properties_description.csv` | The property list, with each term under its parent type |
| `codemeta.json`, `examples/codemeta.json`, `examples/codemeta-software.json` | Examples checked for undefined terms |
| `crosswalks/*.csv` | One translation table per format, listing the same terms in the same order |
| `crosswalk.csv` | All crosswalks combined into one table, which the website shows |

Other example files are not checked: they use a different context or are invalid.
The vocabulary and property list are required; a missing one exits 3. Symbolic links, to
a file or to a folder such as `crosswalks/`, are not followed: the target counts as missing.

## Every check

| Code | It reports |
| --- | --- |
| `TABLE_DUPLICATE` | A term listed twice under the same type in the property list |
| `TABLE_NO_TERM` | A term in the property list that the vocabulary doesn't define |
| `TERM_NO_ROW` | A term in the vocabulary that the property list leaves out |
| `TABLE_NAMESPACE` | A term the property list files under `schema:` but the vocabulary under `codemeta:`, or the other way round |
| `DEFINITION_NO_TERM` | A definition for a term the vocabulary doesn't have |
| `DEFINITION_IRI` | A term whose address differs between the definitions and the vocabulary |
| `EXAMPLE_NO_TERM` | An example that uses an undefined term |
| `CROSSWALK_ROWS` | Missing, unexpected or reordered terms in a crosswalk |
| `CROSSWALK_FORMAT` | Two crosswalks for the same format |
| `AGGREGATE_ROWS` | Missing, unexpected or reordered terms in the combined table |
| `AGGREGATE_FORMAT` | A crosswalk missing from the combined table, or a column with no crosswalk |
| `SKIPPED` | A file this version doesn't have; the checks that need it don't run, and it doesn't count as a problem |

The checks are in [`checks.py`](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/checks.py).

## Read the output

With the [command installed](https://github.com/simonvanlierde/codemeta-drift/blob/main/README.md#try-it), check the CodeMeta checkout:

```sh
codemeta-drift codemeta
```

Each line contains a finding code, file label, term and explanation:

```text
CROSSWALK_ROWS crosswalks/*.csv (all 46): position: line 44 is not in properties_description.csv; the table has maintainer there
EXAMPLE_NO_TERM examples/codemeta.json: softwareSuggestions: not a term of codemeta.jsonld
```

A file label can name a group of files, as in the first line.
The checks test consistency between files. They do not validate every JSON-LD rule or metadata value.

| Exit code | Meaning |
| --- | --- |
| 0 | No disagreements; optional files may produce `SKIPPED` notices |
| 1 | The checker found disagreements |
| 2 | Usage error: an unknown option, a missing argument, or an option value the command can't use (a `--tag` with no curated rows, a `--format`, `--from` or `--to` the mapping lacks) |
| 3 | The check could not run, for example because a required file is missing or unreadable, or its output can't be written, including a closed pipe |
| 130 | Interrupted with Ctrl-C. The command ends by SIGINT, so a shell loop around it stops too; on Windows it exits 130 |

Every `codemeta-drift` command uses these codes. For `export` and `watch`, findings are rows they can't make.

## Read JSON output

```sh
codemeta-drift codemeta --json
```

The output is one JSON document:

```json
{
  "schema_version": 1,
  "tool": {"name": "codemeta-drift", "version": "0.9.0"},
  "findings": [
    {
      "code": "EXAMPLE_NO_TERM",
      "file": "examples/codemeta.json",
      "term": "softwareSuggestions",
      "detail": "not a term of codemeta.jsonld"
    }
  ],
  "errors": []
}
```

`code` is the check and `term` the affected property or format; filter on these. `file` is a
label that can describe a group, and `detail` is text for a person.
`errors` holds usage errors (exit 2) or execution errors (exit 3). Then `findings` is empty and each error is an
object with `message` and `help` (the next step, or `null`).
[`report.schema.json`](https://github.com/simonvanlierde/codemeta-drift/blob/main/src/codemeta_drift/report.schema.json) is its JSON Schema.

`export --json`, `watch` and `hub pair|sssom|crosswalk|coverage --json` write the same `schema_version` and
`errors`, and with `--json` an error, a usage error included, is an object in `errors` on standard output
instead of a line on standard error. With `--out`, only a successful report goes to the file. A command line the parser refuses is an error too, with the usage line as
its `help`, whenever `--json` is among the arguments (always for `watch`). Their other keys:

| Command | Keys besides `schema_version` and `errors` |
| --- | --- |
| `export --json` | `mapping` (the export, `null` when findings block it) and `findings` |
| `watch` | `issues` (the drafts) and `findings` |
| `hub pair --json` | `rows`, each `term`, `source`, `target` |
| `hub sssom --json`, `hub crosswalk --json` | `text`, the file's content |

Each `findings` entry has the keys of a `check` finding.

`hub` takes `-` for the mapping and `watch` takes `-` for `--existing` to read standard input.
A release may add keys. Removing a key or changing its type bumps `schema_version`.

The command line, exit codes, finding codes and mapping export form the public interface.
Python modules may change in any 0.x release.
