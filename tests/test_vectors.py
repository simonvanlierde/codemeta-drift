"""The grammar vectors: each path fits the grammar, and resolves to the listed values in its document."""

import json
import re
from importlib import resources
from typing import Any

import pytest

from codemeta_drift.export import PATH

PACKAGE = resources.files("codemeta_drift")
SCHEMA = json.loads(PACKAGE.joinpath("mapping.schema.json").read_text("utf-8"))
VECTORS = json.loads(PACKAGE.joinpath("mapping-vectors.json").read_text("utf-8"))
CASES = VECTORS["cases"]
STEP = re.compile(r"(@?[A-Za-z_][A-Za-z0-9_@-]*)(?:(\[\])|\[(@?[A-Za-z_][A-Za-z0-9_@-]*)=([A-Za-z0-9_.-]+)\])?")


def resolve(doc: Any, path: str) -> list[Any]:  # noqa: ANN401 - parsed JSON
    """The documented meaning: values in document order, from the first alternative that has any."""
    for alternative in path.split(" | "):
        nodes = [doc]
        for step in re.split(r"\.(?![^\[\]]*\])", alternative):  # a dot inside [k=v] is part of the value
            key, is_list, fkey, fvalue = STEP.fullmatch(step).groups()  # ty: ignore[unresolved-attribute]
            nodes = [n[key] for n in nodes if isinstance(n, dict) and key in n]
            if is_list or fkey:
                nodes = [e for n in nodes if isinstance(n, list) for e in n]
            if fkey:
                nodes = [e for e in nodes if isinstance(e, dict) and str(e.get(fkey)) == fvalue]
        if nodes:
            return nodes
    return []


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_vector_path_is_in_the_grammar(case: dict) -> None:
    assert PATH.fullmatch(case["path"])
    assert re.fullmatch(SCHEMA["$defs"]["row"]["properties"]["path"]["pattern"], case["path"])


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_vector_resolves(case: dict) -> None:
    assert resolve(case["document"], case["path"]) == case["expected"]


def test_vectors_cover_each_form() -> None:
    paths = " ".join(c["path"] for c in CASES)
    for form in (" | ", "[]", "[type=", "@url", "Authors@R"):
        assert form in paths
