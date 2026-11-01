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
TERMS = ("name", "version", "author", "license", "identifier", "swhid", "codeRepository", "description", "keywords")


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
        "@@a",
        "a[@@x=1]",
        "a.@",
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
    contributor = ("contributor", "contributor.givenName", "contributor.familyName", "contributor.@id")
    assert nulls == (
        {(f, t) for f in ("pep621", "cargo", "npm") for t in ("author.@id", "identifier", "swhid", "contributor.@id")}
        | {(f, t) for f in ("cff-1.2.0", "pep621", "cargo") for t in contributor}
        | {(f, "datePublished") for f in ("pep621", "cargo", "npm")}
        | {("pkg-info", t) for t in ("author.@id", "identifier", "swhid", "datePublished", *contributor)}
        | {("r-description", t) for t in ("identifier", "swhid", "keywords")}
        | {("julia", t) for t in ("license", "identifier", "swhid", "codeRepository", "description", "keywords")}
        | {("julia", t) for t in ("datePublished", *contributor)}
        | {("bibtex", t) for t in ("author.@id", *contributor)}
        | {
            ("setup-py", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "datePublished",
            )
        }
        | {
            ("ruby-gem", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "keywords",
                "datePublished",
            )
        }
        | {("maven", t) for t in ("author.@id", "contributor.@id", "identifier", "swhid", "keywords", "datePublished")}
        | {("cpan-meta-2", t) for t in ("author.@id", "contributor.@id", "identifier", "swhid", "datePublished")}
        | {
            ("nuget", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "datePublished",
            )
        }
        | {
            ("pubspec", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "license",
                "identifier",
                "swhid",
                "datePublished",
            )
        }
        | {
            ("cabal", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "datePublished",
            )
        }
        | {
            ("typst", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "datePublished",
            )
        }
        | {
            ("quarto", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "license",
                "identifier",
                "swhid",
                "codeRepository",
                "description",
                "keywords",
                "datePublished",
            )
        }
        | {
            ("github", t)
            for t in (
                "version",
                "author.givenName",
                "author.familyName",
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "datePublished",
            )
        }
        | {
            ("figshare", t)
            for t in (
                "version",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "swhid",
                "codeRepository",
            )
        }
        | {
            ("bio-tools", t)
            for t in (
                "swhid",
                "datePublished",
            )
        }
        | {
            ("leiningen", t)
            for t in (
                "author",
                "author.givenName",
                "author.familyName",
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "keywords",
                "datePublished",
            )
        }
        | {
            ("octave", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "keywords",
            )
        }
        | {
            ("publiccode-0.8", t)
            for t in (
                "author",
                "author.givenName",
                "author.familyName",
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "keywords",
            )
        }
        | {
            ("swmath", t)
            for t in (
                "version",
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "swhid",
                "datePublished",
            )
        }
        | {
            ("spdx-2.3", t)
            for t in (
                "author.@id",
                "contributor",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
                "identifier",
                "keywords",
            )
        }
        | {("dcat-3", t) for t in ("swhid",)}
        | {
            ("doap", t)
            for t in (
                "identifier",
                "swhid",
            )
        }
        | {
            ("wikidata", t)
            for t in (
                "author.givenName",
                "author.familyName",
                "author.@id",
                "contributor.givenName",
                "contributor.familyName",
                "contributor.@id",
            )
        }
    )


@pytest.mark.parametrize("cell", [False, 42, ["package.keyword"], {}])
def test_crosswalk_cell_rejects_non_text_values(cell: object):
    row = {**EXAMPLE["rows"][0], "crosswalk_cell": cell}
    errors = list(Draft202012Validator(SCHEMA).iter_errors({**EXAMPLE, "rows": [row]}))
    assert [e.json_path for e in errors] == ["$.rows[0].crosswalk_cell"]


def test_original_cell_is_optional_for_older_exports():
    older = {
        **EXAMPLE,
        "schema_version": "1.2",
        "rows": [{k: v for k, v in row.items() if k != "crosswalk_cell"} for row in EXAMPLE["rows"]],
    }
    Draft202012Validator(SCHEMA).validate(older)
