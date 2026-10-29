import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from codemeta_drift.export import generator

ROOT = Path(__file__).parent.parent
SCHEMA = json.loads((ROOT / "src/codemeta_drift/mapping.schema.json").read_text())
EXAMPLE = json.loads((ROOT / "examples/mapping-3.1.json").read_text())
PATH = re.compile(SCHEMA["$defs"]["row"]["properties"]["path"]["pattern"])

FORMATS = ("cff-1.2.0", "codemeta", "zenodo", "pep621", "cargo", "npm")
TERMS = ("name", "version", "author", "license", "identifier", "codeRepository", "description", "keywords")


def test_schema_is_valid_2020_12():
    Draft202012Validator.check_schema(SCHEMA)


def test_example_validates():
    Draft202012Validator(SCHEMA).validate(EXAMPLE)


def test_example_has_a_row_for_every_format_and_term():
    pairs = [(row["format"], row["term"]) for row in EXAMPLE["rows"]]
    assert len(pairs) == len(set(pairs))
    assert {(f, t) for f in FORMATS for t in TERMS} <= set(pairs)


@pytest.mark.parametrize("path", sorted({row["path"] for row in EXAMPLE["rows"] if row["path"]}))
def test_path_grammar_accepts_example_paths(path: str):
    assert PATH.fullmatch(path)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "a..b",
        ".a",
        "a.",
        "a[0]",
        "a[]x",
        "a[type=]",
        "a[=doi]",
        "a[]]",
        "a.[]",
        "a|b",
        "a | ",
        "a  | b",
        "a b",
        "1a",
    ],
)
def test_path_grammar_rejects_malformed_paths(path: str):
    assert not PATH.fullmatch(path)


def test_unknown_schema_major_fails_validation():
    errors = list(Draft202012Validator(SCHEMA).iter_errors({**EXAMPLE, "schema_version": "2.0"}))
    assert [e.json_path for e in errors] == ["$.schema_version"]


def test_a_minor_with_new_optional_fields_validates():
    """A 1.0 consumer validates a 1.1 file that adds optional fields, as the contract promises."""
    later = {
        **EXAMPLE,
        "schema_version": "1.1",
        "created": "2027-01-01",
        "generator": {**EXAMPLE["generator"], "url": "https://example.org"},
        "rows": [{**row, "predicate_id": "skos:exactMatch"} for row in EXAMPLE["rows"]],
    }
    Draft202012Validator(SCHEMA).validate(later)


def test_example_generator_is_this_release():
    assert EXAMPLE["generator"] == generator()


def test_example_null_rows():
    nulls = {(row["format"], row["term"]) for row in EXAMPLE["rows"] if row["path"] is None}
    assert nulls == {(f, t) for f in ("pep621", "cargo", "npm") for t in ("author.@id", "identifier")}
