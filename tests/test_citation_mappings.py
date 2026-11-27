from functools import cache
from pathlib import Path
from typing import Any

import pytest

from codemeta_drift.cli import read_dir
from codemeta_drift.coverage import coverage
from codemeta_drift.export import CITATION_TERMS, curated_tags, export
from codemeta_drift.paths import resolve

FIXTURES = Path(__file__).parent / "fixtures"

CROSSREF = {
    "DOI": "10.5555/paper",
    "URL": "https://doi.org/10.5555/paper",
    "title": ["On the grading of lenses"],
    "abstract": "<jats:p>Lenses, graded.</jats:p>",
    "publisher": "Imaginary Lens Society Press",
    "type": "journal-article",
    "published": {"date-parts": [[2026, 11, 26]]},
    "issued": {"date-parts": [[2026]]},
    "container-title": ["Journal of Imaginary Lenses"],
    "volume": "12",
    "issue": "3",
    "page": "101-120",
    "article-number": "e42",
    "author": [
        {"name": "Imaginary Lens Society"},
        {"given": "Magda", "family": "Moon", "ORCID": "https://orcid.org/0000-0002-1825-0097"},
    ],
    "contributor": [{"given": "Ada", "family": "Valence", "ORCID": "https://orcid.org/0000-0001-5109-3700"}],
}
"""A Crossref REST message: one work."""

ARXIV = {
    "id": "http://arxiv.org/abs/2611.23456v2",
    "title": "On the grading of lenses",
    "summary": "Lenses, graded.",
    "published": "2026-11-26T00:00:00Z",
    "doi": "10.5555/paper",
    "primary_category": {"term": "cs.DL", "scheme": "http://arxiv.org/schemas/atom"},
    "link": [
        {"rel": "related", "title": "doi", "href": "https://doi.org/10.5555/other"},
        {"rel": "alternate", "type": "text/html", "href": "https://arxiv.org/abs/2611.23456v2"},
    ],
    "author": [{"name": "Magda Moon"}],
}
"""An arXiv Atom entry, read as docs/reading-formats.md#arxiv says: attributes are plain keys, author and link lists."""

PREFERRED = {
    "type": "article",
    "title": "On the grading of lenses",
    "version": "2",
    "authors": [
        {"given-names": "Magda", "family-names": "Moon", "orcid": "https://orcid.org/0000-0002-1825-0097"},
        {"name": "Imaginary Lens Society"},
    ],
    "license": "CC-BY-4.0",
    "license-url": "https://example.org/licence",
    "doi": "10.5555/paper",
    "identifiers": [
        {"type": "doi", "value": "10.5555/other"},
        {"type": "swh", "value": "swh:1:rel:0000000000000000000000000000000000000000"},
    ],
    "repository-code": "https://example.org/lens-grader",
    "abstract": "Lenses, graded.",
    "keywords": ["optics"],
    "date-published": "2026-11-26",
    "year": 2026,
    "publisher": {"name": "Imaginary Lens Society Press"},
    "url": "https://example.org/paper",
    "journal": "Journal of Imaginary Lenses",
    "collection-title": "Lens Proceedings",
    "volume": 12,
    "issue": "3",
    "start": "101",
    "end": "120",
}
"""A CFF reference: the value of a CITATION.cff's preferred-citation."""

DATACITE = {
    "url": "https://example.org/landing",
    "creators": [{"name": "Imaginary Lens Society", "nameType": "Organizational"}],
    "contributors": [{"name": "Valence, Ada", "nameType": "Personal", "contributorType": "Editor"}],
    "relatedIdentifiers": [
        {"relationType": "IsVersionOf", "relatedIdentifier": "10.5555/concept"},
        {"relationType": "HasVersion", "relatedIdentifier": "10.5555/version"},
        {"relationType": "References", "relatedIdentifier": "10.5555/paper"},
    ],
}
"""A DataCite REST record's attributes."""

CFF = {"cff-version": "1.2.0", "title": "Lens Grader", "preferred-citation": PREFERRED}

PERSON = CROSSREF["author"][1]
# Every non-null row of each format, and what its path gives in that format's sample. Each value appears
# once in its sample, so a path that names the wrong key, or an alternative out of order, gives another.
EXPECTED: dict[str, tuple[dict[str, Any], dict[str, list[Any]]]] = {
    "crossref": (
        CROSSREF,
        {
            "name": ["On the grading of lenses"],
            "author": CROSSREF["author"],
            "author.givenName": ["Magda"],
            "author.familyName": ["Moon"],
            "author.@id": ["https://orcid.org/0000-0002-1825-0097"],
            "author.name": ["Imaginary Lens Society"],
            "contributor": CROSSREF["contributor"],
            "contributor.givenName": ["Ada"],
            "contributor.familyName": ["Valence"],
            "contributor.@id": ["https://orcid.org/0000-0001-5109-3700"],
            "identifier": ["10.5555/paper"],
            "url": ["https://doi.org/10.5555/paper"],
            "description": ["<jats:p>Lenses, graded.</jats:p>"],
            "datePublished": [[[2026, 11, 26]]],
            "publisher": ["Imaginary Lens Society Press"],
            "resourceType": ["journal-article"],
            "containerTitle": ["Journal of Imaginary Lenses"],
            "volume": ["12"],
            "issue": ["3"],
            "pagination": ["101-120"],
        },
    ),
    "arxiv": (
        ARXIV,
        {
            "name": ["On the grading of lenses"],
            "author": ARXIV["author"],
            "author.name": ["Magda Moon"],
            "description": ["Lenses, graded."],
            "datePublished": ["2026-11-26T00:00:00Z"],
            "arxivId": ["https://arxiv.org/abs/2611.23456v2"],
            "primaryCategory": ["cs.DL"],
            "relatedDoi": ["10.5555/paper"],
        },
    ),
    "cff-preferred": (
        PREFERRED,
        {
            "name": ["On the grading of lenses"],
            "version": ["2"],
            "author": PREFERRED["authors"],
            "author.givenName": ["Magda"],
            "author.familyName": ["Moon"],
            "author.@id": ["https://orcid.org/0000-0002-1825-0097"],
            "author.name": ["Imaginary Lens Society"],
            "license": ["CC-BY-4.0"],
            "identifier": ["10.5555/paper"],
            "swhid": ["swh:1:rel:0000000000000000000000000000000000000000"],
            "codeRepository": ["https://example.org/lens-grader"],
            "description": ["Lenses, graded."],
            "keywords": [["optics"]],
            "datePublished": ["2026-11-26"],
            "publisher": ["Imaginary Lens Society Press"],
            "resourceType": ["article"],
            "url": ["https://example.org/paper"],
            "containerTitle": ["Journal of Imaginary Lenses"],
            "volume": [12],
            "issue": ["3"],
            "pagination": ["101", "120"],
        },
    ),
    "datacite": (
        DATACITE,
        {
            "author.name": ["Imaginary Lens Society"],
            "author.resourceType": ["Organizational"],
            "contributor.name": ["Valence, Ada"],
            "contributor.resourceType": ["Personal"],
            "url": ["https://example.org/landing"],
            "isVersionOf": ["10.5555/concept"],
            "hasVersion": ["10.5555/version"],
        },
    ),
    "cff-1.2.0": (CFF, {"preferredCitation": [PREFERRED]}),
}
"""For datacite and cff-1.2.0 only the citation terms: their other rows read CodeMeta's crosswalk."""


@cache
def exported(tag: str) -> dict[str, Any]:
    mapping, findings = export(read_dir(FIXTURES / tag), tag)
    assert not findings
    return mapping


@pytest.mark.parametrize("tag", curated_tags())
@pytest.mark.parametrize("fmt", EXPECTED)
def test_every_citation_provider_row_resolves_in_a_sample(tag: str, fmt: str) -> None:
    sample, expected = EXPECTED[fmt]
    rows = {
        row["term"]: row["path"]
        for row in exported(tag)["rows"]
        if row["format"] == fmt
        and row["path"]
        and (fmt not in ("datacite", "cff-1.2.0") or row["term"] in CITATION_TERMS)
    }
    assert rows.keys() == expected.keys()
    assert {term: resolve(sample, path) for term, path in rows.items()} == expected


@pytest.mark.parametrize("tag", curated_tags())
def test_citation_terms_with_a_property_row_join_its_cell(tag: str) -> None:
    cells = {(c["format"], c["term"]): c for c in coverage(exported(tag))["cells"]}
    assert cells["cff-1.2.0", "preferredCitation"]["status"] == "as-is"
    author = cells["datacite", "author.name"]
    assert (author["status"], author["cell"].strip()) == ("notation", "creatorName")
    # DataCite's url cell is empty, so the reviewed path is still one no upstream cell supplies.
    assert (cells["datacite", "url"]["status"], cells["datacite", "url"]["cell"]) == ("added", "")
    # The property table's Person rows describe creators: a contributor's name joins no cell.
    assert cells["datacite", "contributor.name"]["cell"] is None
    assert cells["datacite", "contributor.name"]["crosswalk"] is None


def test_the_export_names_its_schema_version() -> None:
    assert exported(curated_tags()[-1])["schema_version"] == "1.10"
