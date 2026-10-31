# Understand the findings

codemeta-drift checks the files that define CodeMeta and its crosswalks. It compares
terms by name and checks the row order. A renamed term appears as one unexpected term
and one missing term. When several crosswalks share a problem, the report groups them.

## The files it compares

| File | What it is |
| --- | --- |
| `codemeta.jsonld` | The vocabulary: every term and the web address that defines it |
| `codemeta_all.jsonld` | The definitions of CodeMeta's own terms (since 4.0) |
| `properties_description.csv` | The property list, with each term under its parent type |
| `codemeta.json`, `examples/codemeta.json`, `examples/codemeta-software.json` | Examples checked for undefined terms |
| `crosswalks/*.csv` | One translation table per format, listing the same terms in the same order |
| `crosswalk.csv` | All crosswalks combined into one table, which the website shows |

Other example files use a different context or are intentionally invalid, so their terms
are not checked. The vocabulary and property list are required; a missing file exits 2.

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

The checks live in [`checks.py`](../src/codemeta_drift/checks.py). That module uses only
the Python standard library, so another repository can include it in its own CI.

## Read the output

With the [command installed](../README.md#try-it), check the CodeMeta checkout:

```sh
codemeta-drift codemeta
```

Each line contains a finding code, file label, term and explanation:

```text
CROSSWALK_ROWS crosswalks/*.csv (all 46): position: line 44 is not in properties_description.csv; the table has maintainer there
EXAMPLE_NO_TERM examples/codemeta.json: softwareSuggestions: not a term of codemeta.jsonld
```

A file label can name a group of files, as in the first line. A finding tells you where
to investigate. Compare the named files before changing a term or mapping.
These are consistency checks; they do not validate every JSON-LD rule or metadata value.

| Exit code | Meaning |
| --- | --- |
| 0 | No disagreements; optional files may produce `SKIPPED` notices |
| 1 | The checker found disagreements |
| 2 | The check could not run, for example because a required file is missing or unreadable |

A missing optional file produces `SKIPPED`, which does not make the command fail.

## Read JSON output

```sh
codemeta-drift codemeta --json
```

The output is one document with these keys:

```json
{
  "version": 1,
  "tool": {"name": "codemeta-drift", "version": "0.3.0"},
  "findings": [
    {
      "code": "EXAMPLE_NO_TERM",
      "file": "examples/codemeta.json",
      "term": "softwareSuggestions",
      "detail": "not a term of codemeta.jsonld"
    }
  ]
}
```

`code` identifies the check; `term` names the affected property or format. Use these fields
for filtering. `file` is a label that can describe a group; `detail` is text for a person.
A minor release may add keys. Removing a key or changing its type bumps `version`.

The command line, exit codes, finding codes and mapping export form the public interface.
Python modules may change in any 0.x release.
