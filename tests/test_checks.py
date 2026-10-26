import json
from collections.abc import Callable
from pathlib import Path

import pytest

from codemeta_drift.checks import VALID_EXAMPLES, Finding, check, csv_rows

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
    duplicate = Finding("TABLE_DUPLICATE", "properties_description.csv", "name", "schema:Thing,name appears 2 times")
    assert duplicate in check(snapshot(table=true_duplicate))


def test_row_namespace_disagrees_with_context():
    files = snapshot(context={"@context": {**CONTEXT, "readme": {"@id": "schema:readme"}}})
    assert ("TABLE_NAMESPACE", "readme") in codes(files)


def test_namespace_match_needs_the_whole_prefix():
    files = snapshot(context={"@context": {**CONTEXT, "readme": {"@id": "codemetaX:readme"}}})
    assert ("TABLE_NAMESPACE", "readme") in codes(files)


def test_other_prefixes_and_empty_terms_are_not_properties():
    context = {
        **CONTEXT,
        "spdx": "http://spdx.org/licenses/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "dropped": None,
        "noId": {"@type": "@id"},
    }
    assert check(snapshot(context={"@context": context})) == []


def test_term_is_a_property_by_its_first_letter_only():
    files = snapshot(context={"@context": {**CONTEXT, "xRef": {"@id": "schema:xRef"}}})
    assert ("TERM_NO_ROW", "xRef") in codes(files)


def test_table_row_without_property_is_ignored():
    assert check(snapshot(table="\n".join([*TABLE, "schema:Thing,,Text,x"]))) == []


def test_csv_rows_number_lines_from_one_and_skip_short_and_blank_rows():
    assert csv_rows("a,b\nc\n\n,d\ne,f\n", key=1) == [(1, ["a", "b"]), (4, ["", "d"]), (5, ["e", "f"])]


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


def test_definition_nodes_without_type_are_not_properties():
    graph = {"@graph": [*DEFINITIONS["@graph"], {"@id": "codemeta:", "rdfs:label": "ontology"}]}
    assert check(snapshot(definitions=graph)) == []


def test_definition_without_label_is_reported_with_an_empty_term():
    bad = {"@graph": [{"@id": "codemeta:readme", "@type": "rdf:Property"}]}
    [finding] = [f for f in check(snapshot(definitions=bad)) if f.code == "DEFINITION_NO_TERM"]
    assert finding.term == ""


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


def test_missing_example_does_not_stop_the_others():
    files = snapshot(**{"codemeta.json": None, "examples/codemeta.json": {"bogus": 1}})
    assert ("EXAMPLE_NO_TERM", "bogus") in codes(files)


def test_name_repeated_in_a_long_table_still_matches():
    """With autojunk on, difflib cannot anchor on a name in over 1% of 200+ rows and reports it as drift."""
    names = [*(f"p{i}" for i in range(200)), "q", "name", "r", "name", "name"]
    context = {"@context": {**CONTEXT, **{n: {"@id": f"schema:{n}"} for n in names}}}
    table = "\n".join([*TABLE, *(f"schema:T{i},{n},Text,x" for i, n in enumerate(names))])
    renamed = [{"q": "q2", "r": "r2"}.get(n, n) for n in names]
    crosswalk = "\n".join(["Property,Fmt", "name", "readme", *renamed]) + "\n"
    found = codes(snapshot(context=context, table=table, **{"crosswalks/Fmt.csv": crosswalk}))
    assert sorted(t for c, t in found if c == "CROSSWALK_ROWS") == ["q", "q2", "r", "r2"]


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


def test_crosswalks_that_agree_in_part_are_listed():
    short = "Property,Fmt\nname,t\n"
    files = snapshot(**{"crosswalks/Fmt.csv": short, "crosswalks/Two.csv": short, "crosswalks/Ok.csv": CROSSWALK})
    [finding] = [f for f in check(files) if f.code == "CROSSWALK_ROWS"]
    assert finding.file == "crosswalks/Fmt.csv, crosswalks/Two.csv"


def test_aggregate_row_with_empty_parent_and_type_still_counts():
    files = snapshot(
        **{"crosswalk.csv": "Parent Type,Property,Type,Description,Fmt\nschema:Thing,name,Text,x,title\n,readme,,x,\n"}
    )
    assert check(files) == []


def test_aggregate_format_both_ways():
    files = snapshot(**{"crosswalks/New.csv": CROSSWALK.replace("Fmt", "New")})
    files["crosswalk.csv"] = files["crosswalk.csv"].replace(",Fmt\n", ",Fmt,Gone\n", 1)
    found = {(f.file, f.term, f.detail) for f in check(files) if f.code == "AGGREGATE_FORMAT"}
    assert found == {
        ("crosswalk.csv", "New", "no column for crosswalks/New.csv"),
        ("crosswalk.csv", "Gone", "column has no file in crosswalks/"),
    }


def test_two_crosswalks_with_one_format_name():
    new = CROSSWALK.replace("Fmt", "New")
    found = [
        f for f in check(snapshot(**{"crosswalks/New.csv": new, "crosswalks/New2.csv": new})) if "FORMAT" in f.code
    ]
    assert found == [
        Finding("CROSSWALK_FORMAT", "crosswalks/New.csv, crosswalks/New2.csv", "New", "files share one format name"),
        Finding("AGGREGATE_FORMAT", "crosswalk.csv", "New", "no column for crosswalks/New.csv, crosswalks/New2.csv"),
    ]


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


def drop_zenodo_row(files: dict[str, str]) -> None:
    files["crosswalks/Zenodo.csv"] = files["crosswalks/Zenodo.csv"].replace("\nprogrammingLanguage,\n", "\n", 1)


def rename_context_term(files: dict[str, str]) -> None:
    doc = json.loads(files["codemeta.jsonld"])
    doc["@context"]["codeRepo"] = doc["@context"].pop("codeRepository")
    files["codemeta.jsonld"] = json.dumps(doc)


def add_example_term(files: dict[str, str]) -> None:
    files["examples/codemeta.json"] = json.dumps({**json.loads(files["examples/codemeta.json"]), "bogusTerm": 1})


def duplicate_table_row(files: dict[str, str]) -> None:
    header, first, rest = files["properties_description.csv"].split("\n", 2)
    files["properties_description.csv"] = f"{header}\n{first}\n{first}\n{rest}"


@pytest.mark.parametrize(
    ("fault", "expected"),
    [
        (drop_zenodo_row, [("CROSSWALK_ROWS", "crosswalks/Zenodo.csv", "programmingLanguage")]),
        (
            rename_context_term,
            [
                ("TABLE_NO_TERM", "properties_description.csv", "codeRepository"),
                ("TERM_NO_ROW", "codemeta.jsonld", "codeRepo"),
                ("EXAMPLE_NO_TERM", "examples/codemeta.json", "codeRepository"),
            ],
        ),
        (add_example_term, [("EXAMPLE_NO_TERM", "examples/codemeta.json", "bogusTerm")]),
        (duplicate_table_row, [("TABLE_DUPLICATE", "properties_description.csv", "codeRepository")]),
    ],
)
def test_seeded_drift_in_the_4_0_release_is_found(
    fault: Callable[[dict[str, str]], None], expected: list[tuple[str, str, str]]
):
    """One fault added to the real 4.0 files shows up as new findings, on top of the release's own."""
    files = load_fixture("4.0")
    before = set(check(files))
    fault(files)
    new = {(f.code, f.file, f.term) for f in set(check(files)) - before}
    assert set(expected) <= new
