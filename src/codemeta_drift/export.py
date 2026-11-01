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

SCHEMA_VERSION = "1.6"

TERMS = {
    "name": ("schema:Thing", "name"),
    "version": ("schema:CreativeWork", "version"),
    "author": ("schema:CreativeWork", "author"),
    # After author: a person sub-term's path starts with author's path.
    "author.givenName": ("schema:Person", "givenName"),
    "author.familyName": ("schema:Person", "familyName"),
    "author.@id": ("schema:Person", "identifier"),
    "contributor": ("schema:CreativeWork", "contributor"),
    "contributor.givenName": ("schema:Person", "givenName"),
    "contributor.familyName": ("schema:Person", "familyName"),
    "contributor.@id": ("schema:Person", "identifier"),
    "license": ("schema:CreativeWork", "license"),
    "identifier": ("schema:Thing", "identifier"),
    # The Software Heritage identifier: CodeMeta has no term for it and holds it in identifier, beside the DOI.
    "swhid": ("schema:Thing", "identifier"),
    "codeRepository": ("schema:SoftwareSourceCode", "codeRepository"),
    "description": ("schema:Thing", "description"),
    "keywords": ("schema:CreativeWork", "keywords"),
    "datePublished": ("schema:CreativeWork", "datePublished"),
}
"""Each exported term and the property table row (parent type, property) its crosswalk cell sits on."""
PEOPLE = ("author", "contributor")
"""The terms that hold people; each has the person sub-terms ``<term>.givenName``, ``.familyName`` and ``.@id``."""


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
    "pkg-info": Spoke("crosswalks/Python PKG-INFO.csv"),
    "r-description": Spoke("crosswalks/R Package Description.csv"),
    "julia": Spoke("crosswalks/Julia Project.csv", person_list=True),
    "bibtex": Spoke("crosswalks/BibTeX.csv"),
    "datacite": Spoke("crosswalks/DataCite.csv", person_list=True, person_prefix=""),
    "setup-py": Spoke("crosswalks/Python Distutils (PyPI).csv"),
    "ruby-gem": Spoke("crosswalks/Ruby Gem.csv", person_list=True),
    "maven": Spoke("crosswalks/Java (Maven).csv", person_list=True),
    "cpan-meta-2": Spoke("crosswalks/Perl Module Description (CPAN::Meta).csv", person_list=True),
    "nuget": Spoke("crosswalks/NuGet.csv"),
    "pubspec": Spoke("crosswalks/Pubspec.csv", person_list=True),
    "cabal": Spoke("crosswalks/Cabal.csv"),
    "typst": Spoke(None),
    "quarto": Spoke(None),
    "github": Spoke("crosswalks/GitHub.csv"),
    "figshare": Spoke("crosswalks/Figshare.csv", person_list=True),
    "bio-tools": Spoke("crosswalks/bio.tools.csv", person_list=True),
    "leiningen": Spoke("crosswalks/Leiningen.csv"),
    "octave": Spoke("crosswalks/Octave.csv"),
    "publiccode-0.8": Spoke("crosswalks/publiccode.csv"),
    "swmath": Spoke("crosswalks/swMATH.csv", person_list=True),
    "spdx-2.3": Spoke("crosswalks/SPDX_2_3.csv"),
    "codemeta-2": Spoke("crosswalks/codemeta-V2.csv", person_list=True, person_prefix=""),
    "dcat-3": Spoke("crosswalks/DCAT-3.csv", person_list=True),
    "doap": Spoke("crosswalks/DOAP.csv", person_list=True),
    "wikidata": Spoke("crosswalks/Wikidata.csv", person_list=True),
}

PATH = re.compile(
    json.loads(resources.files("codemeta_drift").joinpath("mapping.schema.json").read_text("utf-8"))["$defs"]["row"][
        "properties"
    ]["path"]["pattern"]
)

# Splits a path into its single-chain pieces, at both `` | `` and `` + ``.
PIECES = re.compile(r" [|+] ")


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
    """codemeta.json's own path for a term: author and contributor are lists, their sub-terms sit in each element."""
    parent, dot, rest = term.partition(".")
    return f"{parent}[]{dot}{rest}" if parent in PEOPLE else term


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
    checked on its own (``curated=[]``). Raises ValueError for a curated row without a required key.
    """
    name = f"curated-{tag}.json"
    overrides: dict[tuple[str, str], dict[str, Any]] = {}
    rows, findings = [], []
    for i, c in enumerate(curated, 1):
        if missing := sorted({"format", "term", "path", "reason"} - c.keys()):
            msg = f"{name}: row {i} has no {', '.join(missing)}"
            raise ValueError(msg)
        if (c["format"], c["term"]) in overrides:
            findings.append(Finding("CURATED_DUPLICATE", name, c["term"], f"second row for {c['format']}"))
        overrides[c["format"], c["term"]] = c
    findings += [
        Finding("CURATED_UNUSED", name, term, f"no {fmt} row has this term")
        for fmt, term in overrides
        if fmt not in FORMATS or term not in TERMS
    ]
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
                row["crosswalk_cell"] = cells.get(key)
                made[term] = row["path"]
                rows.append(row)
        findings += shared_paths(spoke.crosswalk or fmt, fmt, [r for r in rows if r["format"] == fmt])
    return rows, findings


# (format, two terms) whose paths are equal by design: codemeta.json holds the SWHID in identifier, beside the DOI.
SHARED_ON_PURPOSE = {
    ("codemeta", frozenset({"identifier", "swhid"})),
    ("codemeta-2", frozenset({"identifier", "swhid"})),
}


def shared_paths(label: str, fmt: str, rows: list[dict[str, Any]]) -> list[Finding]:
    """A ``PATH_SHARED`` finding for each two terms of ``fmt`` whose paths are equal or one holds the other.

    A wrong cell that still looks like a path (npm's identifier cell ``name``) mostly names another
    term's key. Person sub-terms are left out: they sit inside author's path on purpose. So are the
    pairs in ``SHARED_ON_PURPOSE``, codemeta's and codemeta-2's identifier and swhid, which the
    consumer tells apart by spelling. In every other format those two have keys of their own.
    """
    paths = [
        (row["term"], alternative)
        for row in rows
        if "." not in row["term"] and row["path"]
        for alternative in PIECES.split(row["path"])
    ]
    findings = []
    for i, (term, path) in enumerate(paths):
        for other, other_path in paths[:i]:
            if term == other or (fmt, frozenset({term, other})) in SHARED_ON_PURPOSE:
                continue
            a, b = path.replace("[]", ""), other_path.replace("[]", "")
            if a == b or a.startswith(f"{b}.") or b.startswith(f"{a}."):
                findings.append(Finding("PATH_SHARED", label, term, f"{path!r} overlaps {other}'s {other_path!r}"))
    return findings


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
        if finding := curated_finding(label, term, cell, derived, override):
            return None, finding
        row = {"format": fmt, "term": term, "path": override["path"], "source": f"curated:{override['reason']}"}
        return row | {k: override[k] for k in ("see_also", "comment") if k in override}, None
    if finding := cell_finding(spoke, label, term, cell, derived):
        return None, finding
    row = {"format": fmt, "term": term, "path": derived, "source": f"crosswalk:{spoke.crosswalk}@{tag}"}
    if note := CROSSWALK_COMMENTS.get((fmt, term)):
        row["comment"] = note
    return row, None


DATACITE_NAME = (
    "DataCite's givenName and familyName are optional. Without them, name holds the whole name,"
    " written 'Family, Given' for a Personal nameType, and the consumer splits it."
)

# Guidance for a row that reads its cell as it is, so it has no curated row to hold a comment.
CROSSWALK_COMMENTS = {
    ("cff-1.2.0", "author.familyName"): (
        "CFF keeps a name particle and suffix apart: the family name is name-particle, family-names and"
        " name-suffix joined by spaces, so Antonie van Leeuwenhoek has family-names Leeuwenhoek and"
        " name-particle van, and a family name of van Leeuwenhoek."
    ),
    ("datacite", "author.givenName"): DATACITE_NAME,
    ("datacite", "author.familyName"): DATACITE_NAME,
    ("datacite", "contributor.givenName"): DATACITE_NAME,
    ("datacite", "contributor.familyName"): DATACITE_NAME,
    ("cpan-meta-2", "license"): (
        "license is a list of CPAN::Meta licence strings (perl_5, mit, apache_2_0), not SPDX ids; the"
        " consumer maps them with the spec's table. A single string is a list of one."
    ),
    ("nuget", "author"): (
        "authors is one string; the consumer splits it on commas and trims each name, as swh-indexer does."
    ),
    ("cabal", "author"): (
        "author is free text: often one name, 'Name <email>', or several names joined by commas. The"
        " consumer splits it."
    ),
    ("cabal", "keywords"): (
        "category is free text for Hackage's catalogue ('Data, Text'), not a keyword list; the consumer"
        " splits it on commas."
    ),
    ("codemeta-2", "license"): (
        "The 2.0 context types license as @id, and the example writes a URL (https://spdx.org/licenses/MIT),"
        " not a bare SPDX id."
    ),
    ("codemeta-2", "swhid"): (
        "CodeMeta has no SWHID term; a SWHID sits in identifier, beside the DOI, as a swh:1: string or a"
        " PropertyValue (propertyID SWHID) whose value is one."
    ),
    ("dcat-3", "author"): (
        "The spec recommends a foaf:Agent as the value, so an element is an object or an IRI. A creator"
        " with only an IRI has no name sub-fields."
    ),
    ("dcat-3", "contributor"): (
        "DCAT lists dcterms:contributor, dcterms:creator and dcterms:publisher as the standard properties"
        " for basic agent associations (section 13.1); prov:qualifiedAttribution with dcat:hadRole is for"
        " other roles, which a path cannot express."
    ),
    ("dcat-3", "identifier"): (
        "dcterms:identifier is repeatable and untyped; a DOI is told from a SWHID by its spelling."
    ),
    ("dcat-3", "keywords"): "Repeatable: a single keyword may be a string rather than an array.",
    ("dcat-3", "datePublished"): (
        "A date typed xsd:gYear, xsd:gYearMonth, xsd:date or xsd:dateTime; a record may give several"
        " (Zenodo gives a year and a date), so take the most precise. A typed literal may arrive as"
        ' {"@value", "@type"}.'
    ),
}


def cell_finding(spoke: Spoke, label: str, term: str, cell: str | None, derived: str | None) -> Finding | None:
    """Why a row with no curated row can't come from its cell: it has none, it isn't a path, or its path is wrong."""
    if cell is None:
        detail = "no cell joined to the property table" if spoke.crosswalk else "no crosswalk"
        return Finding("CELL_MISSING", label, term, f"{detail}, and no curated row")
    if derived is None:
        kind = classify(cell)
        if kind == "path":
            detail = f"cell {cell.strip()!r} is relative to {term.partition('.')[0]}, which has no path"
            return Finding("CELL_NO_AUTHOR", label, term, detail)
        detail = (
            f"{kind} cell {cell.strip()!r}, and no curated row" if kind == "prose" else "empty cell, no curated row"
        )
        return Finding(f"CELL_{kind.upper()}", label, term, detail)
    if not PATH.fullmatch(derived):  # such as authors[][] from a cell that already reads as a list
        return Finding("CELL_PATH", label, term, f"cell {cell.strip()!r} gives {derived!r}, which is not a path")
    return None


def curated_finding(
    label: str, term: str, cell: str | None, derived: str | None, override: dict[str, Any]
) -> Finding | None:
    """Why a curated row can't be used: its path is malformed, its cell changed, or it repeats the cell."""
    if override["path"] is not None and not PATH.fullmatch(override["path"]):
        return Finding("CURATED_PATH", label, term, f"{override['path']!r} is not a path")
    if (was := override.get("cell")) != (now := cell and cell.strip()):
        return Finding(
            "CURATED_STALE", label, term, f"the curated row is for the cell {was!r}, the cell is now {now!r}"
        )
    if derived is not None and derived == override["path"]:
        return Finding("CURATED_REPEATS", label, term, f"curated row repeats the cell {cell!r}")
    return None


def derive(spoke: Spoke, term: str, cell: str, made: Mapping[str, str | None]) -> str | None:
    """The path a cell means for a term, or None when it depends on an author or contributor path that is missing."""
    parent = term.partition(".")[0]
    if term in PEOPLE:
        return f"{cell}[]" if spoke.person_list else cell
    if parent in PEOPLE and spoke.person_prefix is not None and cell.startswith(spoke.person_prefix):
        people = made.get(parent)
        return f"{people}.{cell.removeprefix(spoke.person_prefix)}" if people else None
    return cell


def generator() -> dict[str, str]:
    """This tool's name and installed version, for the export header."""
    return {"name": "codemeta-drift", "version": metadata.version("codemeta-drift")}


def export(files: Mapping[str, str], tag: str) -> tuple[dict[str, Any], list[Finding]]:
    """The mapping export for one CodeMeta tag, and the findings that block it."""
    rows, findings = build_rows(files, tag, read_curated(tag))
    return {"schema_version": SCHEMA_VERSION, "codemeta_tag": tag, "generator": generator(), "rows": rows}, findings
