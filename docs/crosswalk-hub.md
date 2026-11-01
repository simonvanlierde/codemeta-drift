# Find corresponding fields in two formats

The hub joins the curated mapping export by term. It tells you which fields correspond;
it does not convert their values. A Cargo author string and a CFF person object still
need different parsers. A Go module path is not a repository URL.

```sh
codemeta-drift hub pair examples/mapping-3.1.json --from pep621 --to cargo
codemeta-drift hub sssom examples/mapping-3.1.json --out spokes.sssom.tsv
codemeta-drift hub crosswalk examples/mapping-3.1.json ../codemeta --format cargo
codemeta-drift hub coverage examples/mapping-3.1.json --out docs/coverage.md
```

`coverage` writes the [coverage matrix](coverage.md): each term and format with its status
(as-is, corrected, added or no field) and the reason for every curated cell. Add `--json`
for the cells as data; the [coverage page](https://simonvanlierde.com/codemeta-drift/) reads that.

`pair` writes CSV columns `term,source,target`. It skips a term when either format has
`path: null` or no row. Unknown source or target formats are errors. Paths that contain
alternatives retain their order and selectors. These are field correspondences, not
instructions to copy a value unchanged.

`sssom` writes [SSSOM 1.0 TSV](https://mapping-commons.github.io/sssom/1.0/spec-formats-tsv/)
with an embedded metadata block and explicit CURIE prefixes. It covers the six formats
in the JSON export and `gomod`. The Go spoke has only `codeRepository`, corresponding
to the `module` directive; other terms have no Go mapping. The JSON export stays unchanged.

All predicates are `skos:relatedMatch`. The paths describe where values sit, but do not
establish that the fields have identical meanings. This includes name components stored
in one string, SPDX identifiers stored as URLs, and Go module paths.

The `term:` namespace identifies the hub's terms from the JSON export, including compound
person paths and `swhid`. It does not add terms to CodeMeta's vocabulary. The `field:`
namespace identifies a format and its complete path, percent-encoded. `format:` identifies
the format itself; its URI prefix differs from `field:` so SSSOM readers can expand both.

All three resolve on the [coverage page](https://simonvanlierde.com/codemeta-drift/), which
opens the matching cell: `field:cargo/package.name` is
<https://simonvanlierde.com/codemeta-drift/#field/cargo/package.name>. The page has no
codemeta.json column, so `field:codemeta/...` opens the term's row instead (`swhid` shares
`identifier`'s, since codemeta.json holds both there). `format:codemeta` and the Go spoke's
`field:gomod/module` and `format:gomod` have no cell. They are not registered w3id identifiers.

The header names the set (`mapping_set_id`, title, description and version), its curator by
ORCID (`creator_id`) and this repository as `mapping_provider`.

The hub rejects unsupported schema versions, malformed headers and rows, duplicate
(format, term) rows, and unknown terms or formats before writing output. It supports the
six formats and terms in the bundled mapping contract; it does not silently interpret new
terms added by a later producer. Optional fields it does not use are ignored.

`crosswalk` writes CodeMeta's two-column CSV layout, `Property,<format>`. It reads the
selected checkout's `properties_description.csv` to preserve its row order and duplicate
property names. Parent types distinguish software identifiers from person identifiers.
Person rows use the author's paths; CodeMeta has no separate contributor person rows.
Unmapped properties have empty cells. Paths retain this export's absolute selectors and
alternatives rather than CodeMeta's original prose.

The hub does not register persistent w3id identifiers per crosswalk. It does not infer
additional direct mappings where CodeMeta has no term, such as Cargo categories versus
Python classifiers.

## Validate the SSSOM export

The [compatibility guide](sssom-compatibility.md) gives a repeatable reference validation
and compares this export with CodeMeta's experimental SSSOM methodology. Valid SSSOM
serialization does not establish that two fields mean the same thing.
