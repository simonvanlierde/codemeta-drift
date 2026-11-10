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
