import hashlib
import json
from pathlib import Path

import pytest

from codemeta_drift.cli import read_dir
from codemeta_drift.conformance import SCHEMA_FILES, conform, resolve
from codemeta_drift.export import build_rows

FIXTURES = Path(__file__).parent / "fixtures"
SCHEMAS = {f: json.loads((FIXTURES / "schemas" / name).read_text()) for f, name in SCHEMA_FILES.items()}
EXAMPLE = json.loads((Path(__file__).parent.parent / "examples/mapping-3.1.json").read_text())


def test_vendored_schemas_match_sources():
    lines = (FIXTURES / "schemas/SOURCES").read_text().splitlines()
    sources = {name: digest for name, _, digest in (line.split() for line in lines if not line.startswith("#"))}
    assert sources.keys() == set(SCHEMA_FILES.values())
    for name, digest in sources.items():
        assert hashlib.sha256((FIXTURES / "schemas" / name).read_bytes()).hexdigest() == digest


def test_example_paths_are_in_their_schemas():
    assert conform(EXAMPLE["rows"], SCHEMAS) == []


def test_raw_crosswalk_paths_fail():
    """The 3.1 crosswalk cells that parse as paths, with no curated rows."""
    rows, _ = build_rows(read_dir(FIXTURES / "3.1"), "3.1", [])
    assert [str(f) for f in conform(rows, SCHEMAS)] == [
        "PATH_NOT_IN_SCHEMA cargo: keywords: package.keyword: no 'keyword'",
    ]


@pytest.mark.parametrize(
    ("fmt", "path", "why"),
    [
        ("cff-1.2.0", "identifiers.url", "no 'url'"),  # the 3.1 sameAs cell: identifiers is a list
        ("cff-1.2.0", "title[]", "'title' is not a list"),
        ("cff-1.2.0", "identifiers[kind=doi].value", "items of 'identifiers' have no 'kind'"),
        ("cff-1.2.0", "authors[].orcid", None),  # through items, anyOf and $ref
        ("cff-1.2.0", "identifiers[type=doi].value", None),
        ("pep621", "project.urls.Source", None),  # additionalProperties
        ("pep621", "project.url", "no 'url'"),
        ("npm", "author.name", None),
        ("cargo", "package.authors[]", None),
    ],
)
def test_resolve(fmt: str, path: str, why: str | None):
    assert resolve(SCHEMAS[fmt], path) == why


def test_every_alternative_and_no_null_or_unchecked_format():
    rows = [
        {"format": "pep621", "term": "codeRepository", "path": "project.urls.Source | project.homepage"},
        {"format": "pep621", "term": "identifier", "path": None},
        {"format": "zenodo", "term": "name", "path": "nonsense"},
    ]
    assert [f.detail for f in conform(rows, SCHEMAS)] == ["project.homepage: no 'homepage'"]
