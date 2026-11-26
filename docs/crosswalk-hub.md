---
description: "Find which fields correspond between two metadata formats, write SSSOM spokes or a CodeMeta crosswalk CSV."
---

# Find corresponding fields in two formats

Each CodeMeta term is a hub. Each format's field for that term is a spoke. Two spokes on the same
hub are corresponding fields. `codemeta-drift hub` reads the reviewed mapping export and joins it
by term. It tells you which fields correspond, not how to convert their values. A Cargo author
string and a CFF person object still need different parsers, and a Go module path is not a
repository URL.

```sh
codemeta-drift hub pair examples/mapping-4.0.json --from pep621 --to cargo
codemeta-drift hub sssom examples/mapping-4.0.json --out spokes.sssom.tsv
codemeta-drift hub crosswalk examples/mapping-4.0.json ../codemeta --format cargo
```

`--format`, `--from` and `--to` take a format id from the list `codemeta-drift hub --help` prints, and every
subcommand's `--help` ends with an example and the exit codes. A mapping `-` is read from standard input. Add
`--json` to `pair`, `sssom` or `crosswalk` for a [JSON report](checks.md#read-json-output) in place of the text.

`coverage` writes the [coverage matrix](coverage-4.0.md): each term and format with its status
(as-is, meaning CodeMeta's cell is already the path; corrected; added; no field; or no term) and
the reason for every reviewed cell. Add `--json` for the cells as data, which the
[coverage page](https://simonvanlierde.com/codemeta-drift/) reads: the newest release at its
bare address, an older one at `?tag=3.1`. With `--codemeta <checkout>`,
it also lists the crosswalks nobody has reviewed, read at the export's tag, under `unreviewed` in
the JSON. Each has a `status` (`superseded`, `registry` or `niche`), `reason` and `url`, all three
`null` when no reason is listed yet.

`pair` writes CSV columns `term,source,target`. It skips a term when either format has
`path: null` or no row, and rejects an unknown source or target format. Paths keep their
alternatives, order and selectors.

`sssom` writes an SSSOM (Simple Standard for Sharing Ontological Mappings)
[1.0 TSV](https://mapping-commons.github.io/sssom/1.0/spec-formats-tsv/) table with an embedded
metadata block and explicit CURIE prefixes. It covers the 44 formats in the 4.0 JSON export and
`gomod`. The Go spoke has only `codeRepository`, corresponding to the `module` directive.

All predicates are `skos:relatedMatch`: matching paths do not make the fields mean the same.
Examples are name components stored in one string, SPDX identifiers stored as URLs, and Go module paths.

| Prefix | Holds | Example |
| --- | --- | --- |
| `term:` | The hub's terms from the JSON export, including compound person paths and `swhid`. They are not CodeMeta vocabulary. | `term:author.givenName` |
| `field:` | A format and its complete path, percent-encoded | `field:cargo/package.name` |
| `format:` | The format itself | `format:cargo` |

All three expand under `https://w3id.org/codemeta-drift/`, which redirects to the
[coverage page](https://simonvanlierde.com/codemeta-drift/). The page opens the matching cell:
`field:cargo/package.name` is <https://w3id.org/codemeta-drift/#field/cargo/package.name>.

- The page has no codemeta.json row, so `field:codemeta/...` opens the first cell of its row's
  term instead. `swhid` shares `identifier`'s, since codemeta.json holds both there.
- `format:codemeta`, the Go spoke's `field:gomod/module` and `format:gomod` have no cell.

The header names the set (`mapping_set_id`, title, description and version), its curator by
ORCID (`creator_id`) and this repository as `mapping_provider`.

Before writing output, the hub rejects unsupported schema versions, malformed headers and rows,
duplicate (format, term) rows, and unknown terms or formats. It ignores optional fields it does not
use. `codemeta_tag` must be a numeric version, such as `3.1` or `4.0`. A format added in a later
tag is rejected in an older export: `gitlab` and `code-json-2.0` require 4.0 or later.

`crosswalk` writes CodeMeta's two-column CSV layout, `Property,<format>`. It takes row order and
duplicate property names from the checkout's `properties_description.csv`, and uses the parent type to tell
software identifiers from person identifiers. Person rows use the author's paths, since CodeMeta has no
separate contributor person rows. Unmapped properties have empty cells. Cells hold this export's paths,
with their selectors and alternatives, in place of CodeMeta's prose.

No crosswalk, term or field has its own w3id registration.

## Validate the SSSOM export

The [compatibility guide](sssom-compatibility.md) validates the export with the SSSOM reference
tool and compares it with CodeMeta's experimental SSSOM methodology.
