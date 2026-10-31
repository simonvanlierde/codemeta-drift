import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from codemeta_drift import export as export_module
from codemeta_drift.cli import main, read_dir
from codemeta_drift.export import build_rows, classify, crosswalk_cells, export, read_curated, shared_paths

ROOT = Path(__file__).parent.parent
FIXTURE = ROOT / "tests/fixtures/3.1"
SCHEMAS = ROOT / "tests/fixtures/schemas"
SCHEMA = json.loads((ROOT / "src/codemeta_drift/mapping.schema.json").read_text())
EXAMPLE_FILE = ROOT / "examples/mapping-3.1.json"
EXAMPLE = json.loads(EXAMPLE_FILE.read_text())
CFF = "crosswalks/Citation File Format 1.2.0.csv"


def without(*pairs: tuple[str, str]) -> list[dict]:
    """The 3.1 curated rows minus the given (format, term) pairs."""
    return [c for c in read_curated("3.1") if (c["format"], c["term"]) not in pairs]


@pytest.mark.parametrize(
    ("cell", "kind"),
    [
        ("package.keywords", "path"),
        (" title ", "path"),
        ("related_identifiers.isSupplementTo", "path"),
        ("identifiers / person.orcid / doi", "prose"),
        ("description, long_description", "prose"),
        ("dependencies, dev-dependencies, build-dependencies", "prose"),
        ("(identifiers)", "prose"),
        ("", "empty"),
        ("  ", "empty"),
    ],
)
def test_classify(cell: str, kind: str):
    assert classify(cell) == kind


def test_cells_join_by_name_and_type_not_position():
    files = read_dir(FIXTURE)
    cells = crosswalk_cells(files, CFF)
    assert cells[("schema:Thing", "identifier")] == "identifiers / person.orcid / doi"
    assert cells[("schema:Person", "identifier")] == "person.orcid / identifiers / doi"
    assert cells[("schema:Thing", "name")] == "title"

    # The same rows in reverse order: names still find their cells, and repeated names keep their order.
    header, *rows = files[CFF].splitlines()
    rows = [r for r in rows if not r.startswith(("identifier,", "name,"))][::-1] + [
        r for r in rows if r.startswith(("identifier,", "name,"))
    ]
    assert crosswalk_cells({**files, CFF: "\n".join([header, *rows])}, CFF) == cells


def test_third_repeat_and_one_column_rows():
    files = read_dir(FIXTURE)
    files["properties_description.csv"] += "schema:Foo,identifier,Text,x\n"
    files[CFF] = files[CFF].replace("name,title\n", "name\n") + "identifier,third\n"
    cells = crosswalk_cells(files, CFF)
    assert cells[("schema:Person", "identifier")] == "person.orcid / identifiers / doi"
    assert cells[("schema:Foo", "identifier")] == "third"
    assert cells[("schema:Thing", "name")] == ""


def test_property_counts_that_differ_get_no_cell():
    files = read_dir(FIXTURE)
    text = files[CFF].replace("identifier,person.orcid / identifiers / doi\n", "")
    cells = crosswalk_cells({**files, CFF: text}, CFF)
    assert not {k for k in cells if k[1] == "identifier"}
    assert cells[("schema:Person", "givenName")] == "person.given-names"


def test_export_3_1_equals_the_example_in_order():
    mapping, findings = export(read_dir(FIXTURE), "3.1")
    assert findings == []
    Draft202012Validator(SCHEMA).validate(mapping)
    assert mapping == EXAMPLE


def test_cell_paths_get_list_and_person_prefix():
    rows, _ = build_rows(read_dir(FIXTURE), "3.1", [])
    path = {(r["format"], r["term"]): r["path"] for r in rows}
    assert path["cff-1.2.0", "author"] == "authors[]"
    assert path["cff-1.2.0", "author.givenName"] == "authors[].given-names"
    assert path["zenodo", "author.@id"] == "creators[].ORCID"
    assert path["npm", "author"] == "author"
    assert path["codemeta", "contributor.@id"] == "contributor[].@id"
    assert path["zenodo", "datePublished"] == "publication_date"


def test_swhid_rows_sit_beside_the_doi():
    rows, findings = build_rows(read_dir(FIXTURE), "3.1", read_curated("3.1"))
    path = {(r["format"], r["term"]): r["path"] for r in rows}
    assert findings == []
    assert path["cff-1.2.0", "swhid"] == "identifiers[type=swh].value"
    assert path["codemeta", "swhid"] == path["codemeta", "identifier"] == "identifier"
    assert path["zenodo", "swhid"] == "related_identifiers[scheme=swh].identifier"


@pytest.mark.parametrize(("fmt", "label"), [("zenodo", "crosswalks/Zenodo.csv"), ("cff-1.2.0", CFF)])
def test_swhid_on_the_doi_path_is_shared_outside_codemeta(fmt: str, label: str):
    """Only codemeta.json holds the SWHID and the DOI in one key; elsewhere that path is a wrong row."""
    curated = [c | {"path": "doi"} if (c["format"], c["term"]) == (fmt, "swhid") else c for c in read_curated("3.1")]
    _, findings = build_rows(read_dir(FIXTURE), "3.1", curated)
    assert [str(f) for f in findings] == [f"PATH_SHARED {label}: swhid: 'doi' overlaps identifier's 'doi'"]


def test_contributor_cells_derive_like_author_cells():
    rows, findings = build_rows(
        read_dir(FIXTURE), "3.1", without(("npm", "contributor"), ("cff-1.2.0", "contributor.givenName"))
    )
    path = {(r["format"], r["term"]): r["path"] for r in rows}
    assert path["npm", "contributor"] == "contributors"
    detail = "cell 'person.given-names' is relative to contributor, which has no path"
    assert [str(f) for f in findings] == [f"CELL_NO_AUTHOR {CFF}: contributor.givenName: {detail}"]


def test_prose_and_empty_cells_without_a_curated_row_are_refused():
    rows, findings = build_rows(read_dir(FIXTURE), "3.1", without(("cff-1.2.0", "license"), ("cargo", "description")))
    assert [str(f) for f in findings] == [
        f"CELL_PROSE {CFF}: license: prose cell 'license / license-url', and no curated row",
        "CELL_EMPTY crosswalks/Cargo.csv: description: empty cell, no curated row",
    ]
    assert len(rows) == 100


def test_curated_row_that_repeats_the_cell_is_refused():
    row = {"format": "npm", "term": "keywords", "path": "keywords", "cell": "keywords", "reason": "x"}
    _, findings = build_rows(read_dir(FIXTURE), "3.1", [*read_curated("3.1"), row])
    assert [str(f) for f in findings] == [
        "CURATED_REPEATS crosswalks/NodeJS.csv: keywords: curated row repeats the cell 'keywords'"
    ]


def test_curated_row_whose_cell_changed_is_stale():
    files = read_dir(FIXTURE)
    files["crosswalks/Cargo.csv"] = files["crosswalks/Cargo.csv"].replace("package.keyword\n", "package.tags\n")
    _, findings = build_rows(files, "3.1", read_curated("3.1"))
    assert [str(f) for f in findings] == [
        (
            "CURATED_STALE crosswalks/Cargo.csv: keywords: the curated row is for the cell 'package.keyword', "
            "the cell is now 'package.tags'"
        ),
    ]


def test_unknown_and_duplicate_curated_rows_are_reported():
    curated = read_curated("3.1")
    typo = {"format": "cff-1.2.0", "term": "author.@ID", "path": "authors[].orcid", "reason": "x"}
    _, findings = build_rows(read_dir(FIXTURE), "3.1", [*curated, typo, curated[0]])
    assert [str(f) for f in findings] == [
        "CURATED_DUPLICATE curated-3.1.json: author.@id: second row for cff-1.2.0",
        "CURATED_UNUSED curated-3.1.json: author.@ID: no cff-1.2.0 row has this term",
    ]


@pytest.mark.parametrize("path", ["project/description", "!!!", "a | b |"])
def test_curated_path_outside_the_grammar_is_refused(path: str):
    row = {"format": "pep621", "term": "description", "path": path, "reason": "x"}
    _, findings = build_rows(read_dir(FIXTURE), "3.1", [*without(("pep621", "description")), row])
    assert [str(f) for f in findings] == [f"CURATED_PATH pep621: description: {path!r} is not a path"]


def test_curated_row_without_a_reason_names_the_file():
    curated = [
        {k: v for k, v in c.items() if k not in {"path", "reason"}} if i == 2 else c
        for i, c in enumerate(read_curated("3.1"))
    ]
    with pytest.raises(ValueError, match=r"curated-3\.1\.json: row 3 has no path, reason$"):
        build_rows(read_dir(FIXTURE), "3.1", curated)


def test_unknown_tag_names_it():
    with pytest.raises(KeyError, match=r"9\.9"):
        read_curated("9.9")


def test_curated_row_keeps_see_also_and_comment():
    row = {
        "format": "pep621",
        "term": "name",
        "path": "project.name",
        "reason": "x",
        "see_also": "https://a",
        "comment": "c",
    }
    rows, _ = build_rows(read_dir(FIXTURE), "3.1", [*without(("pep621", "name")), row])
    assert next(r for r in rows if r["format"] == "pep621" and r["term"] == "name") == {
        "format": "pep621",
        "term": "name",
        "path": "project.name",
        "source": "curated:x",
        "see_also": "https://a",
        "comment": "c",
    }


def test_missing_crosswalk_or_curated_row_is_refused():
    files = {p: t for p, t in read_dir(FIXTURE).items() if p != "crosswalks/Zenodo.csv"}
    _, findings = build_rows(files, "3.1", without(("pep621", "name")))
    assert "CELL_MISSING pep621: name: no crosswalk, and no curated row" in map(str, findings)
    assert "CELL_MISSING crosswalks/Zenodo.csv: name: no cell joined to the property table, and no curated row" in map(
        str, findings
    )


def test_shared_paths_checks_each_alternative_both_ways():
    rows = [
        {"term": "name", "path": "x | y"},
        {"term": "version", "path": "z | w"},
        {"term": "identifier", "path": "list.id"},
        {"term": "author", "path": "list[]"},
        {"term": "license", "path": "p.q"},
        {"term": "description", "path": "y"},
        {"term": "keywords", "path": "p"},
        {"term": "swhid", "path": "list.id"},
    ]
    # In codemeta, swhid shares identifier's path on purpose: both are values of one property, told apart by spelling.
    assert [f.detail for f in shared_paths("f", "codemeta", rows)] == [
        "'list[]' overlaps identifier's 'list.id'",
        "'y' overlaps name's 'y'",
        "'p' overlaps license's 'p.q'",
        "'list.id' overlaps author's 'list[]'",
    ]


def test_wrong_path_shaped_cells_shared_by_two_terms_are_refused():
    """Without their curated rows, Cargo name and npm identifier read paths of other terms."""
    _, findings = build_rows(read_dir(FIXTURE), "3.1", without(("cargo", "name"), ("npm", "identifier")))
    assert [str(f) for f in findings] == [
        "PATH_SHARED crosswalks/Cargo.csv: author: 'package.authors[]' overlaps name's 'package.authors'",
        "PATH_SHARED crosswalks/NodeJS.csv: identifier: 'name' overlaps name's 'name'",
    ]


def test_sub_term_without_an_author_row_says_so():
    files = read_dir(FIXTURE)
    files[CFF] = files[CFF].replace("author,authors\n", "")
    _, findings = build_rows(files, "3.1", read_curated("3.1"))
    assert [str(f) for f in findings] == [
        f"CELL_MISSING {CFF}: author: no cell joined to the property table, and no curated row",
        f"CELL_NO_AUTHOR {CFF}: author.givenName: cell 'person.given-names' is relative to author, which has no path",
        f"CELL_NO_AUTHOR {CFF}: author.familyName: cell 'person.family-names' is relative to author, which has no path",
    ]


def test_a_cell_that_already_reads_as_a_list_is_refused():
    files = read_dir(FIXTURE)
    files[CFF] = files[CFF].replace("author,authors\n", "author,authors[]\n")
    rows, findings = build_rows(files, "3.1", read_curated("3.1"))
    assert [str(f) for f in findings] == [
        f"CELL_PATH {CFF}: author: cell 'authors[]' gives 'authors[][]', which is not a path",
        f"CELL_NO_AUTHOR {CFF}: author.givenName: cell 'person.given-names' is relative to author, which has no path",
        f"CELL_NO_AUTHOR {CFF}: author.familyName: cell 'person.family-names' is relative to author, which has no path",
    ]
    assert not [r for r in rows if r["path"] and "[][]" in r["path"]]


def test_cli_export_reads_the_tag_and_writes_the_example(repo: Path, tmp_path: Path):
    """HEAD is 4.0 and the working tree has an edit: the rows must come from tag 3.1."""
    cargo = repo / "crosswalks/Cargo.csv"
    cargo.write_text(cargo.read_text().replace("version,package.version", "version,see the docs"))
    out = tmp_path / "mapping.json"
    assert main(["export", str(repo), "--tag", "3.1", "--out", str(out), "--schemas", str(SCHEMAS)]) == 0
    assert out.read_bytes() == EXAMPLE_FILE.read_bytes()


@pytest.mark.parametrize(
    ("case", "why"), [("not-a-repo", "not a git repository"), ("repo-without-tag", "Needed a single revision")]
)
def test_cli_export_without_the_tag_exits_2(
    case: str, why: str, tmp_path: Path, git: Callable[..., None], capsys: pytest.CaptureFixture[str]
):
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    if case == "repo-without-tag":
        git(tmp_path, "init", "-q")
        git(tmp_path, "add", "-A")
        git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "3.1")
    assert main(["export", str(tmp_path), "--tag", "3.1"]) == 2
    err = capsys.readouterr().err
    assert err.startswith(f"codemeta-drift: cannot read {tmp_path} at tag 3.1: fatal:")
    assert why in err


def test_cli_export_lists_refused_cells(tagged: Callable, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    files = {
        p: t.replace("description,abstract", "description,abstract / summary") for p, t in read_dir(FIXTURE).items()
    }
    out = tmp_path / "out.json"
    assert main(["export", str(tagged(files)), "--tag", "3.1", "--out", str(out), "--schemas", str(SCHEMAS)]) == 1
    out_text, err = capsys.readouterr()
    assert out_text == ""  # standard output, often redirected to the export file, stays empty
    assert err == f"CELL_PROSE {CFF}: description: prose cell 'abstract / summary', and no curated row\n"
    assert not out.exists()


def test_cli_export_path_not_in_schema_exits_1_and_writes_nothing(repo: Path, tmp_path: Path):
    schemas = tmp_path / "schemas"
    shutil.copytree(SCHEMAS, schemas)
    (schemas / "package.json").write_text('{"type": "object"}')
    out = tmp_path / "out.json"
    assert main(["export", str(repo), "--tag", "3.1", "--out", str(out), "--schemas", str(schemas)]) == 1
    assert not out.exists()


def test_cli_export_without_the_property_table_exits_2(tagged: Callable, capsys: pytest.CaptureFixture[str]):
    files = {p: t for p, t in read_dir(FIXTURE).items() if p != "properties_description.csv"}
    assert main(["export", str(tagged(files)), "--tag", "3.1"]) == 2
    assert "properties_description.csv" in capsys.readouterr().err


def test_cli_export_bad_schemas_dir_exits_2_and_names_the_file(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    assert main(["export", str(repo), "--tag", "3.1", "--schemas", str(tmp_path / "none")]) == 2
    assert str(tmp_path / "none" / "cff-1.2.0.json") in capsys.readouterr().err


def test_cli_export_unwritable_out_exits_2_and_names_the_file(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    out = tmp_path / "no-dir" / "out.json"
    assert main(["export", str(repo), "--tag", "3.1", "--out", str(out)]) == 2
    assert capsys.readouterr().err.startswith(f"codemeta-drift: cannot read or write {out}: FileNotFoundError:")


def test_cli_export_bad_curated_row_exits_2_and_names_the_file(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    rows = [{k: v for k, v in c.items() if k != "reason"} for c in read_curated("3.1")]
    monkeypatch.setattr(export_module, "read_curated", lambda _: rows)
    assert main(["export", str(repo), "--tag", "3.1"]) == 2
    assert "ValueError: curated-3.1.json: row 1 has no reason" in capsys.readouterr().err


@pytest.mark.parametrize("args", [["--tag", "9.9"], ["--tag", "../3.1"]])
def test_cli_export_exits_2(args: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    assert main(["export", str(tmp_path), *args]) == 2
    assert capsys.readouterr().err == f"codemeta-drift: no curated rows for {args[1]}; have 3.1\n"


def test_cli_export_prints_from_the_current_directory(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.chdir(repo)
    monkeypatch.setattr("sys.argv", ["codemeta-drift", "export", "--tag", "3.1"])
    assert main() == 0
    assert capsys.readouterr().out == EXAMPLE_FILE.read_text()


def test_plain_check_still_runs():
    assert main([str(FIXTURE)]) == 1


def test_help_names_the_export_subcommand(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "codemeta-drift export" in capsys.readouterr().out
