"""Build a mapping export (docs/mapping-export.md) from CodeMeta's crosswalks and curated rows.

A row reads its crosswalk cell when the cell is a path in the export's grammar. Every other row
(a prose cell, an empty one, a wrong one, or a format with no crosswalk) comes from
``curated-<tag>.json``, which gives the path and the reason. A cell that is not a path and has no
curated row is refused, never guessed.
"""

import json
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import metadata, resources
from typing import Any

from codemeta_drift.checks import Finding, csv_rows, table_rows

SCHEMA_VERSION = "1.0"

TERMS = {
    "name": ("schema:Thing", "name"),
    "version": ("schema:CreativeWork", "version"),
    "author": ("schema:CreativeWork", "author"),
    # After author: a person sub-term's path starts with author's path.
    "author.givenName": ("schema:Person", "givenName"),
    "author.familyName": ("schema:Person", "familyName"),
    "author.@id": ("schema:Person", "identifier"),
    "license": ("schema:CreativeWork", "license"),
    "identifier": ("schema:Thing", "identifier"),
    "codeRepository": ("schema:SoftwareSourceCode", "codeRepository"),
    "description": ("schema:Thing", "description"),
    "keywords": ("schema:CreativeWork", "keywords"),
}
"""Each exported term and the property table row (parent type, property) its crosswalk cell sits on."""


@dataclass(frozen=True)
class Spoke:
    """How one format's crosswalk cells turn into paths.

    Attributes:
        crosswalk: The crosswalk file, or None when CodeMeta has none for the format.
        person_list: The format keeps authors in a list, so author's path ends in ``[]``.
        person_prefix: How a person sub-term cell starts when it is relative to one author
            (``person.`` in CFF, nothing in Zenodo); it is replaced by author's path. None means
            the cell is already absolute.
    """

    crosswalk: str | None
    person_list: bool = False
    person_prefix: str | None = None


FORMATS = {
    "cff-1.2.0": Spoke("crosswalks/Citation File Format 1.2.0.csv", person_list=True, person_prefix="person."),
    "codemeta": Spoke(None),
    "zenodo": Spoke("crosswalks/Zenodo.csv", person_list=True, person_prefix=""),
    "pep621": Spoke(None),
    "cargo": Spoke("crosswalks/Cargo.csv", person_list=True),
    "npm": Spoke("crosswalks/NodeJS.csv"),
}

PATH = re.compile(
    json.loads(resources.files("codemeta_drift").joinpath("mapping.schema.json").read_text("utf-8"))["$defs"]["row"][
        "properties"
    ]["path"]["pattern"]
)


def classify(cell: str) -> str:
    """``path`` when a crosswalk cell is a path in the export grammar, else ``empty`` or ``prose``."""
    cell = cell.strip()
    if not cell:
        return "empty"
    return "path" if PATH.fullmatch(cell) else "prose"


def crosswalk_cells(files: Mapping[str, str], crosswalk: str) -> dict[tuple[str, str], str]:
    """Maps (parent type, property) of the property table to the crosswalk's cell for it.

    The crosswalk has no type column, so a property listed under two types (``identifier`` under
    Thing and Person) is matched by its n-th occurrence in each file, never by line number. A
    property whose count differs between the files gets no cell, since the match would be a guess.
    """
    parents: dict[str, list[str]] = {}
    for _, row in table_rows(files):
        parents.setdefault(row[1], []).append(row[0])
    rows = [(row[0], row[1] if len(row) > 1 else "") for _, row in csv_rows(files[crosswalk])[1:]]
    counts = Counter(name for name, _ in rows)
    seen: Counter[str] = Counter()
    cells = {}
    for name, cell in rows:
        if counts[name] == len(parents.get(name, ())):
            cells[(parents[name][seen[name]], name)] = cell
        seen[name] += 1
    return cells


def identity(term: str) -> str:
    """codemeta.json's own path for a term: author is a list, its sub-terms sit in each element."""
    return "author[]" if term == "author" else term.replace("author.", "author[].")


def curated_tags() -> list[str]:
    """CodeMeta tags with a curated-<tag>.json in this package."""
    names = (p.name for p in resources.files("codemeta_drift").iterdir())
    return sorted(n.removeprefix("curated-").removesuffix(".json") for n in names if n.startswith("curated-"))


def read_curated(tag: str) -> list[dict[str, Any]]:
    """The curated rows for a CodeMeta tag. Raises KeyError for a tag with no file."""
    if tag not in curated_tags():
        raise KeyError(tag)
    return json.loads(resources.files("codemeta_drift").joinpath(f"curated-{tag}.json").read_text("utf-8"))["rows"]


def build_rows(
    files: Mapping[str, str], tag: str, curated: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[Finding]]:
    """Export rows for every format and term, and a finding for each row it cannot make.

    Rows that can be made are returned even when there are findings, so the raw crosswalk can be
    checked on its own (``curated=[]``).
    """
    overrides = {(c["format"], c["term"]): c for c in curated}
    rows, findings = [], []
    for fmt, spoke in FORMATS.items():
        cells = crosswalk_cells(files, spoke.crosswalk) if spoke.crosswalk and spoke.crosswalk in files else {}
        made: dict[str, str | None] = {}
        for term, key in TERMS.items():
            override = overrides.get((fmt, term))
            if fmt == "codemeta" and not override:
                override = {"path": identity(term), "reason": "codemeta's own term"}
            row, finding = make_row(fmt, spoke, term, cells.get(key), made, override, tag)
            if finding:
                findings.append(finding)
            if row:
                made[term] = row["path"]
                rows.append(row)
    return rows, findings


def make_row(
    fmt: str,
    spoke: Spoke,
    term: str,
    cell: str | None,
    made: Mapping[str, str | None],
    override: dict[str, Any] | None,
    tag: str,
) -> tuple[dict[str, Any] | None, Finding | None]:
    """One export row, from the curated row if there is one, else from the cell."""
    label = spoke.crosswalk or fmt
    derived = None
    if cell is not None and classify(cell) == "path":
        derived = derive(spoke, term, cell.strip(), made)
    if override:
        if derived is not None and derived == override["path"]:
            return None, Finding("CURATED_REPEATS", label, term, f"curated row repeats the cell {cell!r}")
        row = {"format": fmt, "term": term, "path": override["path"], "source": f"curated:{override['reason']}"}
        return row | {k: override[k] for k in ("see_also", "comment") if k in override}, None
    if spoke.crosswalk is None:
        return None, Finding("CELL_MISSING", fmt, term, "no crosswalk and no curated row")
    if cell is None:
        return None, Finding("CELL_MISSING", label, term, "no cell joined to the property table, and no curated row")
    if derived is None:
        kind = classify(cell)
        detail = (
            f"{kind} cell {cell.strip()!r}, and no curated row" if kind == "prose" else "empty cell, no curated row"
        )
        return None, Finding(f"CELL_{kind.upper()}", label, term, detail)
    return {"format": fmt, "term": term, "path": derived, "source": f"crosswalk:{spoke.crosswalk}@{tag}"}, None


def derive(spoke: Spoke, term: str, cell: str, made: Mapping[str, str | None]) -> str | None:
    """The path a cell means for a term, or None when it depends on an author path that is missing."""
    if term == "author":
        return f"{cell}[]" if spoke.person_list else cell
    if term.startswith("author.") and spoke.person_prefix is not None and cell.startswith(spoke.person_prefix):
        author = made.get("author")
        return f"{author}.{cell.removeprefix(spoke.person_prefix)}" if author else None
    return cell


def generator() -> dict[str, str]:
    """This tool's name and installed version, for the export header."""
    return {"name": "codemeta-drift", "version": metadata.version("codemeta-drift")}


def export(files: Mapping[str, str], tag: str) -> tuple[dict[str, Any], list[Finding]]:
    """The mapping export for one CodeMeta tag, and the findings that block it."""
    rows, findings = build_rows(files, tag, read_curated(tag))
    return {"schema_version": SCHEMA_VERSION, "codemeta_tag": tag, "generator": generator(), "rows": rows}, findings
