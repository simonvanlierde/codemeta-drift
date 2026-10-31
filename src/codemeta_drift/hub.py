"""Field correspondences joined through the curated CodeMeta export, without value conversion."""

import csv
import io
import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import quote

from codemeta_drift.checks import table_rows
from codemeta_drift.export import FORMATS, PATH, TERMS

REPO = "https://github.com/simonvanlierde/codemeta-drift/"


def validate_mapping(data: Any) -> None:  # noqa: ANN401
    """Reject unsupported versions, malformed rows and repeated format/term pairs before joining."""
    if not isinstance(data, dict) or not isinstance(data.get("schema_version"), str):
        msg = "mapping must have a schema_version string"
        raise ValueError(msg)  # noqa: TRY004 - malformed JSON documents share one CLI error
    if not re.fullmatch(r"1\.(0|[1-9][0-9]*)", data["schema_version"]):
        msg = f"unsupported mapping schema_version {data['schema_version']!r}"
        raise ValueError(msg)
    generator = data.get("generator")
    if (
        not isinstance(data.get("codemeta_tag"), str)
        or not data["codemeta_tag"]
        or not isinstance(generator, dict)
        or any(not isinstance(generator.get(key), str) or not generator[key] for key in ("name", "version"))
        or not isinstance(data.get("rows"), list)
    ):
        msg = "mapping needs codemeta_tag, generator name/version and rows"
        raise ValueError(msg)
    seen = set()
    for i, row in enumerate(data["rows"], 1):
        if not isinstance(row, dict) or not {"format", "term", "path", "source"} <= row.keys():
            msg = f"mapping row {i} needs format, term, path and source"
            raise ValueError(msg)
        if (
            not isinstance(row["format"], str)
            or row["format"] not in FORMATS
            or not isinstance(row["term"], str)
            or row["term"] not in TERMS
            or not isinstance(row["source"], str)
            or not re.fullmatch(r"(crosswalk:crosswalks/[^@]+\.csv@[^@\s]+|curated:\S.*)", row["source"])
            or (row["path"] is not None and (not isinstance(row["path"], str) or not PATH.fullmatch(row["path"])))
            or any(key in row and not isinstance(row[key], str) for key in ("comment", "see_also"))
            or ("see_also" in row and not row["see_also"].startswith("https://"))
        ):
            msg = f"invalid or unsupported mapping row {i}"
            raise ValueError(msg)
        key = row["format"], row["term"]
        if key in seen:
            msg = f"duplicate mapping row for {key}"
            raise ValueError(msg)
        seen.add(key)


def spokes(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the six-format export and add Go's module directive as a repository correspondence."""
    validate_mapping(mapping)
    return [
        *mapping["rows"],
        {
            "format": "gomod",
            "term": "codeRepository",
            "path": "module",
            "source": "curated:go.mod's module directive is a module path, not a repository URL",
        },
    ]


def pair_rows(mapping: dict[str, Any], source: str, target: str) -> list[dict[str, str]]:
    """Join non-null rows by term; the paths correspond but their values may need conversion."""
    rows = spokes(mapping)
    formats = {row["format"] for row in rows}
    if source not in formats or target not in formats:
        msg = f"source and target must be present formats: {', '.join(sorted(formats))}"
        raise ValueError(msg)
    targets = {row["term"]: row["path"] for row in rows if row["format"] == target and row["path"] is not None}
    return [
        {"term": row["term"], "source": row["path"], "target": targets[row["term"]]}
        for row in rows
        if row["format"] == source and row["path"] is not None and row["term"] in targets
    ]


def table(rows: Iterable[Mapping[str, str]], columns: list[str], delimiter: str = ",") -> str:
    """Serialize rows with proper quoting, including paths containing alternatives."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, delimiter=delimiter, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def sssom(mapping: dict[str, Any]) -> str:
    """SSSOM 1.0 TSV spokes with explicit CURIEs and conservative relatedMatch predicates.

    The hub identifies complete field paths, including person sub-terms and swhid, in its own
    namespace. It does not invent CodeMeta vocabulary terms for these compound correspondences.
    """
    rows = spokes(mapping)
    metadata = (
        f"# mapping_set_id: {REPO}blob/main/docs/crosswalk-hub.md\n"
        "# license: https://spdx.org/licenses/Apache-2.0.html\n"
        "# sssom_version: '1.0'\n"
        "# curie_map:\n"
        f"#   term: {REPO}blob/main/docs/mapping-export.md#\n"
        f"#   field: {REPO}blob/main/docs/crosswalk-hub.md#\n"
        f"#   format: {REPO}blob/main/docs/crosswalk-hub.md#\n"
        "#   skos: http://www.w3.org/2004/02/skos/core#\n"
        "#   semapv: https://w3id.org/semapv/vocab/\n"
    )
    mappings = [
        {
            "subject_id": f"term:{quote(row['term'], safe='')}",
            "predicate_id": "skos:relatedMatch",
            "object_id": f"field:{row['format']}/{quote(row['path'], safe='')}",
            "mapping_justification": "semapv:ManualMappingCuration",
            "object_source": f"format:{row['format']}",
            "subject_source_version": mapping["codemeta_tag"],
            "comment": row["source"] + (f"; {row['comment']}" if row.get("comment") else ""),
        }
        for row in rows
        if row["path"] is not None
    ]
    return metadata + table(
        mappings,
        [
            "subject_id",
            "predicate_id",
            "object_id",
            "mapping_justification",
            "object_source",
            "subject_source_version",
            "comment",
        ],
        "\t",
    )


def crosswalk(mapping: dict[str, Any], files: Mapping[str, str], fmt: str) -> str:
    """CodeMeta's two-column layout, with the property table's order and duplicate rows.

    Person rows describe the author mapping, since the property table has no separate contributor
    person rows. The synthetic swhid term must not replace the software identifier (DOI).
    """
    rows = spokes(mapping)
    if fmt not in {row["format"] for row in rows}:
        msg = f"unknown format {fmt!r}"
        raise ValueError(msg)
    paths = {
        TERMS[row["term"]]: row["path"] or ""
        for row in rows
        if row["format"] == fmt and row["term"] != "swhid" and not row["term"].startswith("contributor.")
    }
    return table(
        [{"Property": row[1], fmt: paths.get((row[0], row[1]), "")} for _, row in table_rows(files)], ["Property", fmt]
    )
