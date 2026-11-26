"""How well CodeMeta's own crosswalks hold up, read from the curated mapping export."""

import re
from collections.abc import Mapping
from typing import Any

from codemeta_drift.checks import TABLE, code_span, crosswalk_paths, format_name
from codemeta_drift.export import (
    FORMATS,
    NO_PROPERTY,
    PEOPLE,
    TERMS,
    classify,
    crosswalk_cells,
    derive,
)
from codemeta_drift.hub import validate_mapping

STATUSES = {
    "as-is": ("✓", "CodeMeta's crosswalk cell is the path"),
    "scope": (
        "⊂",
        (
            "the crosswalk cell is right by CodeMeta's definition, but codemeta-drift reads the term more narrowly"
            " (identifier as the software's DOI, a person's @id as their ORCID, publisher as its name, swhid as a"
            " term of its own) or also reads another field, such as a fallback or a newer one; the reviewed"
            " mapping gives the path, or says the format has none"
        ),
    ),
    "notation": (
        "≈",
        (
            "the crosswalk cell names the right field, but in a form a tool can't use as a path, such as another"
            " case, no prefix or XPath; the reviewed mapping gives the path"
        ),
    ),
    "corrected": ("✎", "the crosswalk cell is wrong, ambiguous or prose; the reviewed mapping gives the path"),
    "added": ("+", "the format has the field but the crosswalk has no cell for it; the reviewed mapping adds the path"),
    "no field": ("–", "the format has no field for this term"),  # noqa: RUF001 - an en dash, as in the docs
    "no term": ("∅", "CodeMeta has no property for this term; the reviewed mapping adds the path"),
}
"""Each cell status, its mark and what it means. The order is the legend's.

A row's ``kind`` (scope or notation) names a cell that would otherwise be corrected.
When a cell has both a notation gap and a scope gap, notation wins.
"""

SHAPES = {
    "path": ("•", "the cell looks like one path; nobody has checked it"),
    "prose": ("¶", "the cell is prose or a list, not one path"),
    "empty": ("○", "the cell is empty: the format may have no field, or the crosswalk leaves it out"),
    "no-term": ("∅", "CodeMeta's property table has no row for this term"),
    "unmatched": ("?", "the crosswalk and the property table list this property a different number of times"),
}
"""What a cell of a crosswalk with no reviewed mapping shows: only its shape, from ``classify``."""

SHORT_LABELS = {"Perl Module Description (CPAN::Meta)": "Perl (CPAN::Meta)"}
"""Shorter names for the crosswalks whose own header runs long, keyed by file name."""

NOT_REVIEWED = {
    "DCAT": (
        "superseded",
        "DCAT 2, which DCAT 3 replaced as the W3C Recommendation in 2024; the reviewed dcat-3 rows read that",
        "https://www.w3.org/TR/vocab-dcat-3/",
    ),
    "codemeta-V1": (
        "superseded",
        "CodeMeta 1.0; the reviewed codemeta and codemeta-2 rows read the contexts that replaced it",
        "https://codemeta.github.io/terms/",
    ),
    "ASCL": (
        "registry",
        "the Astrophysics Source Code Library's entry fields, a registry record",
        "https://ascl.net/",
    ),
    "SciCrunchRegistry": (
        "registry",
        "the SciCrunch Registry's resource fields, the records behind RRIDs",
        "https://scicrunch.org/resources",
    ),
    "OntoSoft": (
        "registry",
        "the ontology of the OntoSoft software registry, whose code was last changed in 2023",
        "https://github.com/KnowledgeCaptureAndDiscovery/ontosoft",
    ),
    "Software Ontology": (
        "niche",
        "an OWL ontology that classifies software tools in knowledge bases, not a metadata file",
        "https://github.com/allysonlister/swo",
    ),
    "Software Discovery Index": (
        "niche",
        "the NIH BD2K software index proposed at a 2014 workshop; no index was launched",
        "https://web.archive.org/web/20141207053849/http://softwarediscoveryindex.org/report/",
    ),
    "csdms": (
        "registry",
        "the model-description fields of the CSDMS model repository, a catalogue of earth-surface models",
        "https://csdms.colorado.edu/wiki/Model_download_portal",
    ),
    "usgs-modelcatalog": (
        "registry",
        "the record fields of the USGS model catalog",
        "https://data.usgs.gov/modelcatalog/",
    ),
    "Trove Software Map": (
        "niche",
        "Trove classifiers, a category vocabulary rather than a record format; a package's classifiers are in pkg-info",
        "https://pypi.org/classifiers/",
    ),
}
"""Why each crosswalk with no reviewed mapping stays so, keyed by file name: (status, reason, URL)."""

COLUMNS = [fmt for fmt in FORMATS if fmt != "codemeta"]
"""The formats shown: codemeta.json is the hub every path is joined through, so it has no crosswalk to check."""


def columns(mapping: dict[str, Any]) -> list[str]:
    """The ``COLUMNS`` the mapping has rows for: an older or hand-written export may lack some."""
    present = {row["format"] for row in mapping["rows"]}
    return [fmt for fmt in COLUMNS if fmt in present]


def status(row: dict[str, Any], parents: dict[str, str | None], kind: str | None = None) -> str:
    """One export row's status; ``parents`` holds the format's people paths (author, contributor).

    ``kind`` is the row's own, which turns a corrected cell into scope or notation.
    """
    if row["source"].startswith("crosswalk:"):
        return "as-is"
    if row["term"] in NO_PROPERTY and row["path"] is not None:
        return "no term"
    cell = (row.get("crosswalk_cell") or "").strip()
    parent = row["term"].partition(".")[0]
    # A person sub-term reads the shared Person row, so its cell says nothing when its list has no field.
    if row["path"] is None and (not cell or (parent != row["term"] and parents.get(parent) is None)):
        return "no field"
    return (kind or "corrected") if cell else "added"


def anchor(fmt: str) -> str:
    """GitHub's link target for a format's heading: ``cff-1.2.0`` becomes ``cff-120``."""
    return re.sub(r"[^a-z0-9-]", "", fmt.lower())


def coverage(mapping: dict[str, Any]) -> dict[str, Any]:
    """Every (format, term) cell of a mapping export with its status, path, original cell and reason."""
    validate_mapping(mapping)
    rows = {(row["format"], row["term"]): row for row in mapping["rows"]}
    cells = []
    for fmt in columns(mapping):
        parents = {term: rows[fmt, term]["path"] for term in ("author", "contributor") if (fmt, term) in rows}
        for term in TERMS:
            row = rows.get((fmt, term))
            if row is None:
                continue
            source = row["source"]
            cells.append(
                {
                    "format": fmt,
                    "term": term,
                    "status": status(row, parents, row.get("kind")),
                    "path": row["path"],
                    "cell": row.get("crosswalk_cell"),
                    "crosswalk": FORMATS[fmt].crosswalk,
                    "reason": source.removeprefix("curated:") if source.startswith("curated:") else None,
                }
            )
    return {
        "codemeta_tag": mapping["codemeta_tag"],
        "generator": mapping["generator"],
        "formats": columns(mapping),
        "terms": list(TERMS),
        "statuses": {name: {"mark": mark, "meaning": meaning} for name, (mark, meaning) in STATUSES.items()},
        "cells": cells,
    }


def unreviewed(files: Mapping[str, str], mapping: dict[str, Any]) -> dict[str, Any]:
    """Every crosswalk in ``files`` the mapping does not review, each cell with the shape ``SHAPES`` names.

    ``files`` should be the mapping's own CodeMeta tag. A format is its crosswalk's file name without
    ``.csv``, not a mapping format id; its label is the header's second cell, or ``SHORT_LABELS``.
    Formats are sorted by label; each has the ``status``, ``reason`` and ``url`` of ``NOT_REVIEWED``, all
    None for a crosswalk it does not list. Cells have the keys of ``coverage``'s, with no path and no reason.
    """
    reviewed = {FORMATS[fmt].crosswalk for fmt in columns(mapping)}
    formats, cells = [], []
    for path in crosswalk_paths(files):
        if path in reviewed:
            continue
        fmt = path.removeprefix("crosswalks/").removesuffix(".csv")
        label = SHORT_LABELS.get(fmt) or format_name(files[path]).strip()
        status, reason, url = NOT_REVIEWED.get(fmt, (None, None, None))
        formats.append(
            {"format": fmt, "label": label, "crosswalk": path, "status": status, "reason": reason, "url": url}
        )
        joined = crosswalk_cells(files, path)
        for term, key in TERMS.items():
            cell = joined.get(key)
            status = "no-term" if term in NO_PROPERTY else "unmatched" if cell is None else classify(cell)
            cells.append(
                {
                    "format": fmt,
                    "term": term,
                    "status": status,
                    "path": None,
                    "cell": cell,
                    "crosswalk": path,
                    "reason": None,
                }
            )
    formats.sort(key=lambda f: f["label"].casefold())
    return {
        "codemeta_tag": mapping["codemeta_tag"],
        "statuses": {name: {"mark": mark, "meaning": meaning} for name, (mark, meaning) in SHAPES.items()},
        "formats": formats,
        "cells": cells,
    }


def markdown(mapping: dict[str, Any], files: Mapping[str, str] | None = None) -> str:
    """docs/coverage-<tag>.md: a counts table, the term-by-format matrix and the reason for every curated cell.

    With the files of the mapping's CodeMeta tag, it ends with the crosswalks nobody has reviewed.
    """
    data = coverage(mapping)
    tag, formats = data["codemeta_tag"], data["formats"]
    by_key = {(c["format"], c["term"]): c for c in data["cells"]}
    own = [f for f in formats if not FORMATS[f].crosswalk]
    owns = f"{', '.join(f'`{f}`' for f in own)} have no CodeMeta crosswalk, so each of their paths is added here. "
    lines = [
        "---",
        (
            f'description: "The crosswalk coverage matrix at CodeMeta {tag}: for each reviewed format and term,'
            ' whether the crosswalk cell works as written, and the reviewed path where it does not."'
        ),
        "---",
        "",
        f"# Crosswalk coverage at CodeMeta {tag}",
        "",
        f"<!-- Generated by `codemeta-drift hub coverage examples/mapping-{tag}.json --codemeta <checkout>`; edit the curated rows, not this file. -->",  # noqa: E501
        "",
        (
            f"How CodeMeta's {tag} crosswalks map {len(data['terms'])} CodeMeta terms in {len(formats)} formats, "
            "read from the reviewed [mapping export](mapping-export.md). "
            + (owns if own else "")
            + "The [web page](https://simonvanlierde.com/codemeta-drift/) also checks CodeMeta's main branch "
            "against the newest tag each week."
        ),
        "",
        "| Mark | Status | Meaning |",
        "| --- | --- | --- |",
        *(f"| {mark} | {name} | {meaning} |" for name, (mark, meaning) in STATUSES.items()),
        "",
        "## Counts",
        "",
        "| Format | Crosswalk | " + " | ".join(STATUSES) + " |",
        "| --- | --- | " + " | ".join("---:" for _ in STATUSES) + " |",
    ]
    for fmt in formats:
        counts = [sum(c["status"] == s for c in data["cells"] if c["format"] == fmt) for s in STATUSES]
        path = FORMATS[fmt].crosswalk
        crosswalk = f"`{path.removeprefix('crosswalks/')}`" if path else "none"
        lines.append(f"| {fmt} | {crosswalk} | " + " | ".join(map(str, counts)) + " |")
    lines += ["", "## Matrix", "", "| Term | " + " | ".join(formats) + " |", "| --- |" + " --- |" * len(formats)]
    for term in data["terms"]:
        marks = []
        for fmt in formats:
            cell = by_key.get((fmt, term))
            if cell is None:
                marks.append("")
                continue
            mark = STATUSES[cell["status"]][0]
            # GitHub ends a table cell at a bare |, even inside a code span.
            path = f" {code_span(cell['path']).replace('|', '\\|')}" if cell["path"] else ""
            link = f"[{mark}](#{anchor(fmt)})" if cell["reason"] else mark
            marks.append(link + path)
        lines.append(f"| `{term}` | " + " | ".join(marks) + " |")
    lines += ["", "## Curated cells", ""]
    for fmt in formats:
        lines += [f"### {fmt}", ""]
        for cell in data["cells"]:
            if cell["format"] != fmt or not cell["reason"]:
                continue
            # Stripped: DataCite's name cell is "title ", with a stray trailing space.
            was = (
                f"crosswalk cell {code_span(cell['cell'].strip())}"
                if (cell["cell"] or "").strip()
                else "no crosswalk cell"
            )
            now = code_span(cell["path"]) if cell["path"] else "no path"
            reason = cell["reason"][0].upper() + cell["reason"][1:].rstrip(".")
            # A bare URL in a reason (SPDX's git+https://host/path.git) is shown as code, not a link.
            # It starts after a space or "(" and never ends in a full stop; <autolinks> and `code` are left alone.
            reason = re.sub(r"(?<![^\s(])[^\s`<(]*https?://[^\s;,)`>]*[^\s;,)`>.]", lambda m: f"`{m[0]}`", reason)
            lines.append(f"- `{cell['term']}` ({cell['status']}): {was} → {now}. {reason}.")
        lines.append("")
    if files is not None:
        lines += unreviewed_markdown(unreviewed(files, mapping), data["terms"])
    return "\n".join(lines)


def unreviewed_markdown(data: dict[str, Any], terms: list[str]) -> list[str]:
    """The not-reviewed section of docs/coverage-<tag>.md: one row per crosswalk, one mark per term."""
    marks = {(c["format"], c["term"]): SHAPES[c["status"]][0] for c in data["cells"]}
    lines = [
        "## Not reviewed",
        "",
        f"CodeMeta has {len(data['formats'])} more crosswalks with no reviewed mapping.",
        "",
        "| Mark | Shape | Meaning |",
        "| --- | --- | --- |",
        *(f"| {mark} | {name} | {meaning} |" for name, (mark, meaning) in SHAPES.items()),
        "",
        "| Format | " + " | ".join(f"`{term}`" for term in terms) + " |",
        "| --- |" + " :-: |" * len(terms),
    ]
    for fmt in data["formats"]:
        row = " | ".join(marks[fmt["format"], term] for term in terms)
        lines.append(f"| {fmt['label'].replace('|', '\\|')} | {row} |")
    lines.append("")
    if why := [fmt for fmt in data["formats"] if fmt["status"]]:
        lines += ["Why each is not reviewed:", ""]
        lines += [f"- {f['label']} ({f['status']}): {f['reason']}. <{f['url']}>" for f in why]
        lines.append("")
    return lines


def upstream(files: Mapping[str, str], mapping: dict[str, Any]) -> list[dict[str, Any]]:
    """The cells whose crosswalk text in ``files`` (a newer CodeMeta commit) differs from the export's tag.

    ``state`` is ``missing`` when the new commit has no such crosswalk file or no property table;
    ``unmatched`` when its crosswalk and property table list a property a different number of times
    and :func:`crosswalk_rows` can't join its cell; ``fixed`` when a corrected or added cell now gives the reviewed
    path, so the curated row could go; else ``changed``.
    """
    paths = {(row["format"], row["term"]): row["path"] for row in mapping["rows"]}
    cells: dict[str, dict[tuple[str, str], str]] = {}
    changed = []
    for c in coverage(mapping)["cells"]:
        crosswalk = c["crosswalk"]
        if crosswalk is None:
            continue
        if crosswalk not in files or TABLE not in files:
            changed.append({**c, "now": None, "state": "missing"})
            continue
        if crosswalk not in cells:
            cells[crosswalk] = crosswalk_cells(files, crosswalk)
        now = cells[crosswalk].get(TERMS[c["term"]])
        if (now or "").strip() == (c["cell"] or "").strip():
            continue
        if now is None:
            state = "unmatched"
        elif c["status"] != "as-is" and fixes(c, now.strip(), paths):
            state = "fixed"
        else:
            state = "changed"
        changed.append({**c, "now": now, "state": state})
    return changed


def fixes(cell: dict[str, Any], now: str, paths: Mapping[tuple[str, str], str | None]) -> bool:
    """Whether new crosswalk text gives the curated path once derived.

    A row with no path never counts: the export refuses an empty cell without its curated row.
    """
    if cell["path"] is None or not now or classify(now) != "path":
        return False
    fmt = cell["format"]
    made = {term: paths.get((fmt, term)) for term in PEOPLE}
    # The curated path is in derived form: a list's [] added, CFF's person. replaced by the author path.
    return derive(FORMATS[fmt], cell["term"], now, made) == cell["path"]
