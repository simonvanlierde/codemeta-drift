"""The grammar vectors: each path fits the grammar, and resolves to the listed values in its document."""

import json
import re
from importlib import resources

import pytest

from codemeta_drift.export import PATH
from codemeta_drift.paths import resolve

PACKAGE = resources.files("codemeta_drift")
SCHEMA = json.loads(PACKAGE.joinpath("mapping.schema.json").read_text("utf-8"))
VECTORS = json.loads(PACKAGE.joinpath("mapping-vectors.json").read_text("utf-8"))
CASES = VECTORS["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_vector_path_is_in_the_grammar(case: dict) -> None:
    assert PATH.fullmatch(case["path"])
    assert re.fullmatch(SCHEMA["$defs"]["row"]["properties"]["path"]["pattern"], case["path"])


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_vector_resolves(case: dict) -> None:
    assert resolve(case["document"], case["path"]) == case["expected"]


def test_vectors_cover_each_form() -> None:
    paths = " ".join(c["path"] for c in CASES)
    for form in (" | ", " + ", "[]", "[type=", "@url", "Authors@R", "dcterms:", ".url"):
        assert form in paths
