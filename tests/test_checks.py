import json
from pathlib import Path

import pytest

from codemeta_drift.checks import VALID_EXAMPLES, check

FIXTURES = Path(__file__).parent / "fixtures"

CONTEXT = {
    "type": "@type",
    "schema": "https://schema.org/",
    "codemeta": "https://w3id.org/codemeta/terms/",
    "Person": {"@id": "schema:Person"},
    "name": {"@id": "schema:name"},
    "readme": {"@id": "codemeta:readme", "@type": "@id"},
}
TABLE = [
    "Parent Type,Property,Type,Description",
    "schema:Thing,name,Text,x",
    "codemeta:SoftwareSourceCode,readme,URL,x",
]
DEFINITIONS = {"@graph": [{"@id": "codemeta:readme", "@type": "rdf:Property", "rdfs:label": "readme"}]}
CROSSWALK = "Property,Fmt\nname,title\nreadme,\n"


ALIASES = {"context": "codemeta.jsonld", "definitions": "codemeta_all.jsonld", "table": "properties_description.csv"}


def snapshot(**changes: object) -> dict[str, str]:
    """A consistent minimal codemeta repository.

    Keyword arguments (a path, or a key of ALIASES) replace a file, or drop it when None. A new
    path must be under crosswalks/ or examples/, so a typo cannot add a stray file.
    """
    files = {
        "codemeta.jsonld": json.dumps({"@context": CONTEXT}),
        "codemeta_all.jsonld": json.dumps(DEFINITIONS),
        "properties_description.csv": "\n".join(TABLE) + "\n",
        "crosswalk.csv": "Parent Type,Property,Type,Description,Fmt\nschema:Thing,name,Text,x,title\nc,readme,URL,x,\n",
        "crosswalks/Fmt.csv": CROSSWALK,
        **{path: json.dumps({"@type": "SoftwareSourceCode", "name": "x"}) for path in VALID_EXAMPLES},
    }
    for key, value in changes.items():
        name = ALIASES.get(key, key)
        assert name in files or name.startswith(("crosswalks/", "examples/")), f"unknown file {name}"
        if value is None:
            del files[name]
        else:
            files[name] = value if isinstance(value, str) else json.dumps(value)
    return files


def codes(files: dict[str, str]) -> list[tuple[str, str]]:
    return [(f.code, f.term) for f in check(files)]


def load_fixture(tag: str) -> dict[str, str]:
    """A release fixture as path -> text, read like the CLI reads a working tree."""
    root = FIXTURES / tag
    return {p.relative_to(root).as_posix(): p.read_text("utf-8") for p in root.rglob("*") if p.is_file()}


def test_consistent_repo_has_no_findings():
    assert check(snapshot()) == []


def test_row_without_term_and_term_without_row():
    files = snapshot(
        table="\n".join([*TABLE, "schema:CreativeWork,encoding,MediaObject,x"]),
        context={"@context": {**CONTEXT, "featureList": {"@id": "schema:featureList"}}},
    )
    assert ("TABLE_NO_TERM", "encoding") in codes(files)
    assert ("TERM_NO_ROW", "featureList") in codes(files)


def test_duplicates_are_keyed_on_parent_type_not_namespace():
    same_name_other_parent = "\n".join([*TABLE, "schema:Person,name,Text,x"])
    assert "TABLE_DUPLICATE" not in {c for c, _ in codes(snapshot(table=same_name_other_parent))}
    true_duplicate = "\n".join([*TABLE, "schema:Thing,name,Text,y"])
    assert ("TABLE_DUPLICATE", "name") in codes(snapshot(table=true_duplicate))


def test_row_namespace_disagrees_with_context():
    files = snapshot(context={"@context": {**CONTEXT, "readme": {"@id": "schema:readme"}}})
    assert ("TABLE_NAMESPACE", "readme") in codes(files)


def test_namespace_match_needs_the_whole_prefix():
    files = snapshot(context={"@context": {**CONTEXT, "readme": {"@id": "codemetaX:readme"}}})
    assert ("TABLE_NAMESPACE", "readme") in codes(files)


def test_other_prefixes_and_empty_terms_are_not_properties():
    context = {**CONTEXT, "spdx": "http://spdx.org/licenses/", "dropped": None, "noId": {"@type": "@id"}}
    assert check(snapshot(context={"@context": context})) == []


def test_row_with_empty_parent_still_counts():
    table = "\n".join([TABLE[0], ",name,Text,x", TABLE[2]])
    assert "TERM_NO_ROW" not in {c for c, _ in codes(snapshot(table=table))}


def test_line_numbers_follow_the_file_across_multiline_fields():
    table = "\n".join([TABLE[0], 'schema:Thing,name,Text,"two\nlines"', "schema:Thing,bogus,Text,x", TABLE[2]])
    found = [f for f in check(snapshot(table=table)) if f.code == "CROSSWALK_ROWS"]
    assert [(f.term, f.detail) for f in found] == [("bogus", "no row for properties_description.csv line 4")]


def test_definition_label_typo_names_the_context_alias():
    bad = {"@graph": [{"@id": "codemeta:readme", "@type": "rdf:Property", "rdfs:label": "readMe"}]}
    [finding] = [f for f in check(snapshot(definitions=bad)) if f.code == "DEFINITION_NO_TERM"]
    assert finding.term == "readMe"
    assert "as readme" in finding.detail


def test_definition_type_may_be_a_list():
    bad = {"@graph": [{"@id": "codemeta:readme", "@type": ["rdf:Property"], "rdfs:label": "readMe"}]}
    assert ("DEFINITION_NO_TERM", "readMe") in codes(snapshot(definitions=bad))


def test_definition_iri_disagrees_with_context():
    bad = {"@graph": [{"@id": "codemeta:name", "@type": "rdf:Property", "rdfs:label": "name"}]}
    assert ("DEFINITION_IRI", "name") in codes(snapshot(definitions=bad))


def test_example_terms_outside_inline_context_and_keywords():
    example = {"@context": {"x": "schema:x"}, "@id": "y", "type": "z", "schema:foo": 1, "author": [{"bogus": 1}]}
    found = codes(snapshot(**{"examples/codemeta.json": example}))
    assert [t for c, t in found if c == "EXAMPLE_NO_TERM"] == ["author", "bogus"]


@pytest.mark.parametrize("path", VALID_EXAMPLES)
def test_every_valid_example_is_checked(path: str):
    assert ("EXAMPLE_NO_TERM", "bogus") in codes(snapshot(**{path: {"bogus": 1}}))


def test_crosswalk_rows_are_matched_by_name_not_count():
    """A renamed row is reported as both a stray row and a missing one, never as a silent remap."""
    shifted = "Property,Fmt\nname,title\nposition,maint\n"
    findings = [f for f in check(snapshot(**{"crosswalks/Fmt.csv": shifted})) if f.code == "CROSSWALK_ROWS"]
    assert [(f.term, f.file) for f in findings] == [
        ("position", "crosswalks/Fmt.csv"),
        ("readme", "crosswalks/Fmt.csv"),
    ]
    assert "the table has readme there" in findings[0].detail


def test_many_for_one_replacement_does_not_repeat_the_table_names():
    shifted = "Property,Fmt\nposition,maint\n"
    found = [f for f in check(snapshot(**{"crosswalks/Fmt.csv": shifted})) if f.code == "CROSSWALK_ROWS"]
    assert all("the table has" not in f.detail for f in found)


def test_crosswalks_that_agree_are_reported_once():
    files = snapshot(
        **{"crosswalks/Fmt.csv": "Property,Fmt\nname,t\n", "crosswalks/Other.csv": "Property,Other\nname,\n"}
    )
    files["crosswalk.csv"] = files["crosswalk.csv"].replace(",Fmt\n", ",Fmt,Other\n")
    [finding] = [f for f in check(files) if f.code == "CROSSWALK_ROWS"]
    assert finding.file == "crosswalks/*.csv (all 2)"


def test_aggregate_format_both_ways():
    files = snapshot(**{"crosswalks/New.csv": CROSSWALK.replace("Fmt", "New")})
    files["crosswalk.csv"] = files["crosswalk.csv"].replace(",Fmt\n", ",Fmt,Gone\n", 1)
    found = {(f.term, f.detail) for f in check(files) if f.code == "AGGREGATE_FORMAT"}
    assert found == {("New", "no column for crosswalks/New.csv"), ("Gone", "column has no file in crosswalks/")}


def test_two_crosswalks_with_one_format_name():
    files = snapshot(**{"crosswalks/Fmt2.csv": CROSSWALK})
    assert ("CROSSWALK_FORMAT", "Fmt") in codes(files)


def test_no_crosswalk_files_skips_the_format_comparison():
    files = snapshot(**{"crosswalks/Fmt.csv": None})
    assert "AGGREGATE_FORMAT" not in {c for c, _ in codes(files)}


@pytest.mark.parametrize(
    ("dropped", "skipped"),
    [
        (["definitions"], ["codemeta_all.jsonld"]),
        (["crosswalk.csv"], ["crosswalk.csv"]),
        (["context"], ["codemeta.jsonld"]),
        (["table"], ["properties_description.csv"]),
        (["table", "context"], ["codemeta.jsonld", "properties_description.csv"]),
    ],
)
def test_missing_file_skips_its_checks_only(dropped: list[str], skipped: list[str]):
    findings = check(snapshot(**dict.fromkeys(dropped)))
    assert [f.file for f in findings if f.code == "SKIPPED"] == skipped
    assert all(f.code == "SKIPPED" for f in findings)


@pytest.mark.parametrize(
    "change",
    [
        {"context": "{bad"},
        {"context": {"@context": ["https://w3id.org/codemeta/3.0"]}},
        {"definitions": {"@graph": [{"@type": "rdf:Property"}]}},
        {"crosswalk.csv": ""},
    ],
)
def test_malformed_input_raises_instead_of_reporting(change: dict[str, object]):
    """The CLI turns these into exit 2; check() must not swallow them as findings or as silence."""
    with pytest.raises((ValueError, KeyError, IndexError, TypeError, AttributeError)):
        check(snapshot(**change))


@pytest.mark.parametrize("tag", ["3.1", "4.0"])
def test_release_matches_golden_output(tag: str):
    """Each release fixture prints its recorded findings.

    The golden files pin the output; they do not prove it right, the unit tests above do. Review
    the diff before regenerating with
    `uv run codemeta-drift tests/fixtures/<tag> > tests/fixtures/<tag>.expected`.
    """
    files = load_fixture(tag)
    expected = (FIXTURES / f"{tag}.expected").read_text("utf-8").splitlines()
    assert [str(f) for f in check(files)] == expected


def test_4_0_evidence_for_the_alignment_issue():
    """The facts the alignment issue quotes, pinned so a refactor cannot lose them."""
    found = codes(load_fixture("4.0"))
    for fact in [
        *(("TABLE_NO_TERM", t) for t in ("encoding", "fileFormat", "softwareSuggestions")),
        *(("TERM_NO_ROW", t) for t in ("archivedAt", "encodingFormat", "featureList")),
        ("EXAMPLE_NO_TERM", "softwareSuggestions"),
        ("DEFINITION_NO_TERM", "contiIntegration"),
        ("AGGREGATE_FORMAT", "GitLab"),
        ("AGGREGATE_FORMAT", "code.json"),
    ]:
        assert fact in found
