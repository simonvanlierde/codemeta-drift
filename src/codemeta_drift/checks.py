"""Find where CodeMeta's context, definitions, property table, examples and crosswalks disagree.

It uses only the standard library and imports nothing from this package, so the
codemeta repository can copy it as is for a CI check.

Every check reads files from a mapping of repository-relative path to text. When
a check's input file is missing, it reports ``SKIPPED`` instead of failing, so the
same code runs on every CodeMeta release.
"""

import csv
import difflib
import io
import json
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

CONTEXT = "codemeta.jsonld"
DEFINITIONS = "codemeta_all.jsonld"
TABLE = "properties_description.csv"
AGGREGATE = "crosswalk.csv"

VALID_EXAMPLES = ("codemeta.json", "examples/codemeta.json", "examples/codemeta-software.json")
"""Files that should only use terms of the CodeMeta context. The other files in
examples/ use the schema.org context or are invalid on purpose."""

NOT_PROPERTIES = frozenset({"type", "id", "schema", "codemeta"})
"""Context keys that are keyword aliases or prefixes, not properties."""


@dataclass(frozen=True)
class Finding:
    """One disagreement between two CodeMeta files.

    Attributes:
        code: Stable identifier of the rule, such as ``TABLE_NO_TERM``.
        file: The file (or group of crosswalk files) where it shows.
        term: The property or format it is about.
        detail: What disagrees, for a human reader.
    """

    code: str
    file: str
    term: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code} {self.file}: {self.term}: {self.detail}"


type Row = tuple[int, list[str]]
"""A CSV record and the file line it starts on."""


def csv_rows(text: str, key: int = 0) -> list[Row]:
    """Records of a CSV file with a value in column ``key``, each with its first line number."""
    reader = csv.reader(io.StringIO(text))
    rows, line = [], 1
    for row in reader:
        if len(row) > key and row[key]:
            rows.append((line, row))
        line = reader.line_num + 1
    return rows


def context_terms(files: Mapping[str, str]) -> dict[str, str]:
    """Maps each property term of the context to its prefixed IRI."""
    context = json.loads(files[CONTEXT])["@context"]
    terms = {}
    for key, value in context.items():
        iri = value.get("@id") if isinstance(value, dict) else value
        is_class = not key[:1].islower()  # Person, Organization...
        is_prefix = isinstance(iri, str) and iri.endswith(("/", "#"))  # schema, spdx...
        if key in NOT_PROPERTIES or is_class or is_prefix or not isinstance(iri, str):
            continue
        terms[key] = iri
    return terms


def table_rows(files: Mapping[str, str]) -> list[Row]:
    """Property table records with a property name, header dropped."""
    return csv_rows(files[TABLE], key=1)[1:]


def crosswalk_paths(files: Mapping[str, str]) -> list[str]:
    """Paths of the per-format crosswalk files, sorted."""
    return sorted(p for p in files if p.startswith("crosswalks/") and p.endswith(".csv"))


def format_name(crosswalk: str) -> str:
    """The format a crosswalk file maps to: the second cell of its header, as in "Property,Zenodo"."""
    (_, header), *_ = csv_rows(crosswalk)
    return header[1]


def used_terms(node: object, found: set[str]) -> set[str]:
    """Collects every non-keyword key of a JSON document, outside @context."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "@context":
                continue
            if not key.startswith("@"):
                found.add(key)
            used_terms(value, found)
    elif isinstance(node, list):
        for value in node:
            used_terms(value, found)
    return found


def check_table(files: Mapping[str, str]) -> Iterator[Finding]:
    """Property table against itself and against the context."""
    rows = [(row[0], row[1]) for _, row in table_rows(files)]
    for (parent, name), count in sorted(Counter(rows).items()):
        if count > 1:
            yield Finding("TABLE_DUPLICATE", TABLE, name, f"{parent},{name} appears {count} times")
    terms = context_terms(files)
    names = {name for _, name in rows}
    for name in sorted(names - terms.keys()):
        yield Finding("TABLE_NO_TERM", TABLE, name, f"row has no term in {CONTEXT}")
    for name in sorted(terms.keys() - names):
        yield Finding("TERM_NO_ROW", CONTEXT, name, f"term has no row in {TABLE}")
    for parent, name in rows:
        prefix = parent.split(":")[0]
        iri = terms.get(name)
        if iri is not None and not iri.startswith(prefix + ":"):
            yield Finding("TABLE_NAMESPACE", TABLE, name, f"row {parent},{name} but {CONTEXT} maps {name} to {iri}")


def check_definitions(files: Mapping[str, str]) -> Iterator[Finding]:
    """Property definitions against the context."""
    terms = context_terms(files)
    graph = json.loads(files[DEFINITIONS])["@graph"]

    def is_property(node: dict) -> bool:
        kind = node.get("@type")
        return "rdf:Property" in (kind if isinstance(kind, list) else [kind])

    for node in sorted(filter(is_property, graph), key=lambda n: n["@id"]):
        label, iri = node.get("rdfs:label", ""), node["@id"]
        if label not in terms:
            alias = [t for t, i in terms.items() if i == iri]
            hint = f"; {CONTEXT} has {iri} as {alias[0]}" if alias else ""
            yield Finding("DEFINITION_NO_TERM", DEFINITIONS, label, f"defines {iri} but {CONTEXT} has no {label}{hint}")
        elif terms[label] != iri:
            yield Finding(
                "DEFINITION_IRI", DEFINITIONS, label, f"defines {iri} but {CONTEXT} maps it to {terms[label]}"
            )


def check_examples(files: Mapping[str, str]) -> Iterator[Finding]:
    """Valid examples use only context terms."""
    terms = context_terms(files)
    for path in VALID_EXAMPLES:
        if path not in files:
            continue
        keys = used_terms(json.loads(files[path]), set())
        for key in sorted(k for k in keys if ":" not in k and k not in terms and k not in NOT_PROPERTIES):
            yield Finding("EXAMPLE_NO_TERM", path, key, f"not a term of {CONTEXT}")


def column_diff(code: str, label: str, column: list[tuple[int, str]], table: list[Row]) -> Iterator[Finding]:
    """Where a property column departs from the table's, matched by name, not by position.

    ``column`` holds (file line, property) pairs of the checked file.
    """
    names, wanted = [name for _, name in column], [row[1] for _, row in table]
    matcher = difflib.SequenceMatcher(a=names, b=wanted, autojunk=False)
    for op, a1, a2, b1, b2 in matcher.get_opcodes():
        if op in {"delete", "replace"}:
            # Name the table row only for a one-for-one swap, where it is the likely rename.
            instead = f"; the table has {wanted[b1]} there" if op == "replace" and a2 - a1 == b2 - b1 == 1 else ""
            for line, name in column[a1:a2]:
                yield Finding(code, label, name, f"line {line} is not in {TABLE}{instead}")
        if op in {"insert", "replace"}:
            for line, row in table[b1:b2]:
                yield Finding(code, label, row[1], f"no row for {TABLE} line {line}")


def check_crosswalks(files: Mapping[str, str]) -> Iterator[Finding]:
    """Each crosswalk file lists the table's properties in the table's order."""
    table = table_rows(files)
    paths = crosswalk_paths(files)
    # Crosswalks with the same property column share one set of findings.
    groups: dict[tuple[tuple[int, str], ...], list[str]] = {}
    for path in paths:
        column = tuple((line, row[0]) for line, row in csv_rows(files[path])[1:])
        groups.setdefault(column, []).append(path)
    for column, members in groups.items():
        label = f"crosswalks/*.csv (all {len(paths)})" if len(members) == len(paths) > 1 else ", ".join(members)
        yield from column_diff("CROSSWALK_ROWS", label, list(column), table)


AGGREGATE_FIXED_COLUMNS = 4
"""crosswalk.csv starts with Parent Type, Property, Type and Description; formats follow."""


def check_aggregate(files: Mapping[str, str]) -> Iterator[Finding]:
    """The committed crosswalk.csv has every format and the table's properties."""
    (_, header), *rows = csv_rows(files[AGGREGATE], key=1)
    yield from column_diff("AGGREGATE_ROWS", AGGREGATE, [(line, row[1]) for line, row in rows], table_rows(files))
    paths = crosswalk_paths(files)
    if not paths:
        return
    formats: dict[str, list[str]] = {}
    for path in paths:
        formats.setdefault(format_name(files[path]), []).append(path)
    columns = set(header[AGGREGATE_FIXED_COLUMNS:])
    for name, members in sorted(formats.items()):
        if len(members) > 1:
            yield Finding("CROSSWALK_FORMAT", ", ".join(members), name, "files share one format name")
        if name not in columns:
            yield Finding("AGGREGATE_FORMAT", AGGREGATE, name, f"no column for {', '.join(members)}")
    for name in sorted(columns - formats.keys()):
        yield Finding("AGGREGATE_FORMAT", AGGREGATE, name, "column has no file in crosswalks/")


CHECKS = (
    (check_table, (CONTEXT, TABLE)),
    (check_definitions, (CONTEXT, DEFINITIONS)),
    (check_examples, (CONTEXT,)),
    (check_crosswalks, (TABLE,)),
    (check_aggregate, (TABLE, AGGREGATE)),
)


def check(files: Mapping[str, str]) -> list[Finding]:
    """Every finding for one snapshot of the codemeta repository, SKIPPED ones first.

    Raises ValueError, KeyError, IndexError, TypeError or AttributeError when an input file is
    malformed (not JSON, not UTF-8, an unexpected shape); a caller must not read that as drift.
    """
    findings: list[Finding] = []
    skipped: set[str] = set()
    for run, needs in CHECKS:
        gaps = {p for p in needs if p not in files}
        if gaps:
            skipped |= gaps
            continue
        findings.extend(run(files))
    reason = "file not present, checks that need it did not run"
    return [*(Finding("SKIPPED", path, "", reason) for path in sorted(skipped)), *findings]
