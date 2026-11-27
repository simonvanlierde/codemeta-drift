from pathlib import Path

import pytest

from codemeta_drift.cli import read_dir
from codemeta_drift.export import curated_tags, export
from codemeta_drift.paths import resolve

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("tag", curated_tags())
def test_crosswalks_for_citation_providers(tag: str) -> None:
    mapping, findings = export(read_dir(FIXTURES / tag), tag)
    assert not findings
    rows = {(row["format"], row["term"]): row["path"] for row in mapping["rows"]}

    crossref = {
        "DOI": "10.5555/paper",
        "published": {"date-parts": [[2026, 11, 26]]},
        "container-title": ["Proceedings of the Imaginary Lens Society"],
        "author": [{"name": "Imaginary Lens Society"}, {"given": "Magda", "family": "Moon"}],
        "contributor": [{"given": "Ada", "family": "Valence", "ORCID": "https://orcid.org/0000-0002-1825-0097"}],
        "editor": [{"family": "Asher"}],
        "license": [
            {"content-version": "am", "URL": "https://creativecommons.org/licenses/by/4.0/"},
            {"content-version": "tdm", "URL": "https://example.org/tdm"},
        ],
    }
    assert resolve(crossref, rows["crossref", "identifier"]) == ["10.5555/paper"]
    assert resolve(crossref, rows["crossref", "datePublished"]) == [[[2026, 11, 26]]]
    assert resolve(crossref, rows["crossref", "containerTitle"]) == ["Proceedings of the Imaginary Lens Society"]
    assert resolve(crossref, rows["crossref", "author.name"]) == ["Imaginary Lens Society"]
    assert resolve(crossref, rows["crossref", "contributor"]) == crossref["contributor"]
    assert resolve(crossref, rows["crossref", "contributor.givenName"]) == ["Ada"]
    assert resolve(crossref, rows["crossref", "contributor.familyName"]) == ["Valence"]
    assert resolve(crossref, rows["crossref", "contributor.@id"]) == ["https://orcid.org/0000-0002-1825-0097"]
    assert rows["crossref", "license"] is None

    arxiv = {
        "id": "https://arxiv.org/abs/2611.23456",
        "link": [
            {"rel": "related", "title": "doi", "href": "https://doi.org/10.5555/paper"},
            {"rel": "alternate", "href": "https://arxiv.org/abs/2611.23456v2"},
        ],
        "author": [{"name": "Magda Moon"}],
    }
    assert resolve(arxiv, rows["arxiv", "arxivId"]) == ["https://arxiv.org/abs/2611.23456v2"]
    assert resolve(arxiv, rows["arxiv", "relatedDoi"]) == ["https://doi.org/10.5555/paper"]
    assert resolve(arxiv, rows["arxiv", "author.name"]) == ["Magda Moon"]

    datacite = {
        "creators": [{"name": "Imaginary Lens Society", "nameType": "Organizational"}],
        "relatedIdentifiers": [
            {"relationType": "IsVersionOf", "relatedIdentifier": "10.5555/concept"},
            {"relationType": "References", "relatedIdentifier": "10.5555/paper"},
        ],
    }
    assert resolve(datacite, rows["datacite", "author.name"]) == ["Imaginary Lens Society"]
    assert resolve(datacite, rows["datacite", "author.resourceType"]) == ["Organizational"]
    assert resolve(datacite, rows["datacite", "isVersionOf"]) == ["10.5555/concept"]

    cff = {
        "title": "Lens Grader",
        "type": "software",
        "preferred-citation": {
            "title": "On the grading of lenses",
            "type": "article",
            "journal": "Journal of Imaginary Lenses",
        },
    }
    preferred = resolve(cff, rows["cff-1.2.0", "preferredCitation"])[0]
    assert resolve(cff, rows["cff-1.2.0", "resourceType"]) == ["software"]
    assert resolve(preferred, rows["cff-preferred", "resourceType"]) == ["article"]
    assert resolve(preferred, rows["cff-preferred", "containerTitle"]) == ["Journal of Imaginary Lenses"]
