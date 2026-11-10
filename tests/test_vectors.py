"""The grammar vectors: each path fits the grammar, and resolves to the listed values in its document."""

import json
from importlib import resources

import pytest

from codemeta_drift.export import PATH
from codemeta_drift.paths import resolve

PACKAGE = resources.files("codemeta_drift")
VECTORS = json.loads(PACKAGE.joinpath("mapping-vectors.json").read_text("utf-8"))
CASES = VECTORS["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_vector_path_is_in_the_grammar(case: dict) -> None:
    assert PATH.fullmatch(case["path"])


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_vector_resolves(case: dict) -> None:
    assert resolve(case["document"], case["path"]) == case["expected"]


def test_vectors_cover_each_form() -> None:
    paths = " ".join(c["path"] for c in CASES)
    for form in (" | ", " + ", "[]", "[type=", "@url", "Authors@R", "dcterms:", ".url", "[@id=./]"):
        assert form in paths


@pytest.mark.parametrize(
    "case", [c for c in CASES if "parser" in c["name"] and "Author" in c["name"]], ids=lambda c: c["name"]
)
def test_pkg_info_parser_vectors_include_raw_headers(case: dict) -> None:
    assert case["raw_input"]["format"] == "pkg-info"
    assert case["raw_input"]["text"].startswith(("Author: ", "Author-email: "))
    assert case["raw_input"]["text"].endswith("\n")


# The lists rule of docs/mapping-export.md for RO-Crate and Croissant: these keys are read as lists.
LISTED = ("author", "creator", "contributor", "identifier", "license", "publisher")


def read_json_ld(fmt: str, text: str) -> dict:
    """A crate or Croissant file read as docs/mapping-export.md says: references replaced, bare values listed."""
    tree = json.loads(text)
    root = tree
    if fmt == "ro-crate":
        entities = {e["@id"]: e for e in tree["@graph"]}
        root = next(e for e in tree["@graph"] if e["@id"] == "./")

        def entity(value: object) -> object:
            is_ref = isinstance(value, dict) and value.keys() == {"@id"}
            return entities.get(value["@id"], value) if is_ref else value

        for key, value in root.items():
            root[key] = [entity(v) for v in value] if isinstance(value, list) else entity(value)
    for key in LISTED:
        if key in root and not isinstance(root[key], list):
            root[key] = [root[key]]
    return tree


JSON_LD = {
    c["raw_input"]["format"]: c for c in CASES if c.get("raw_input", {}).get("format") in ("ro-crate", "croissant")
}


@pytest.mark.parametrize("fmt", ["ro-crate", "croissant"])
def test_json_ld_parser_vectors_match_the_reading_rules(fmt: str) -> None:
    case = JSON_LD[fmt]
    assert read_json_ld(fmt, case["raw_input"]["text"]) == case["document"]


# What each non-null curated row reads from the parser vectors' documents.
EXPECTED = {
    "name": ["Carberry's lab notes"],
    "version": ["1.2.0"],
    "author.givenName": ["Josiah"],
    "author.familyName": ["Carberry"],
    "author.@id": ["https://orcid.org/0000-0002-1825-0097"],
    "license": ["https://spdx.org/licenses/MIT"],
    "identifier": ["https://doi.org/10.5555/carberry.notes"],
    "description": ["Readings from the psychoceramics lab."],
    "datePublished": ["2026-11-10"],
    "publisher": ["Psychoceramics Society"],
}


@pytest.mark.parametrize("fmt", ["ro-crate", "croissant"])
def test_curated_json_ld_rows_read_the_vector_documents(fmt: str) -> None:
    rows = json.loads(PACKAGE.joinpath("curated-4.0.json").read_text("utf-8"))["rows"]
    paths = {r["term"]: r["path"] for r in rows if r["format"] == fmt}
    document = JSON_LD[fmt]["document"]
    for term, values in EXPECTED.items():
        assert resolve(document, paths[term]) == values, term
    assert [a["name"] for a in resolve(document, paths["author"])] == ["Josiah Carberry"]
    assert resolve(document, paths["keywords"]) in (["ceramics, cracks"], [["ceramics", "cracks"]])
    assert resolve(document, paths["resourceType"]) in (["Dataset"], ["sc:Dataset"])
    for term in ("contributor", "contributor.givenName", "contributor.familyName", "contributor.@id"):
        assert resolve(document, paths[term]) == [], term
