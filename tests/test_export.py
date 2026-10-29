import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from codemeta_drift.cli import main, read_dir
from codemeta_drift.export import build_rows, classify, crosswalk_cells, export, read_curated

ROOT = Path(__file__).parent.parent
FIXTURE = ROOT / "tests/fixtures/3.1"
SCHEMA = json.loads((ROOT / "src/codemeta_drift/mapping.schema.json").read_text())
EXAMPLE = json.loads((ROOT / "examples/mapping-3.1.json").read_text())
CFF = "crosswalks/Citation File Format 1.2.0.csv"


def by_pair(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r["format"], r["term"]))


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


def test_property_counts_that_differ_get_no_cell():
    files = read_dir(FIXTURE)
    text = files[CFF].replace("identifier,person.orcid / identifiers / doi\n", "")
    cells = crosswalk_cells({**files, CFF: text}, CFF)
    assert not {k for k in cells if k[1] == "identifier"}
    assert cells[("schema:Person", "givenName")] == "person.given-names"


def test_export_3_1_equals_the_example_but_the_generator():
    mapping, findings = export(read_dir(FIXTURE), "3.1")
    assert findings == []
    Draft202012Validator(SCHEMA).validate(mapping)
    assert {k: v for k, v in mapping.items() if k not in {"rows", "generator"}} == {
        k: v for k, v in EXAMPLE.items() if k not in {"rows", "generator"}
    }
    assert by_pair(mapping["rows"]) == by_pair(EXAMPLE["rows"])


def test_cell_paths_get_list_and_person_prefix():
    rows, _ = build_rows(read_dir(FIXTURE), "3.1", [])
    path = {(r["format"], r["term"]): r["path"] for r in rows}
    assert path["cff-1.2.0", "author"] == "authors[]"
    assert path["cff-1.2.0", "author.givenName"] == "authors[].given-names"
    assert path["zenodo", "author.@id"] == "creators[].ORCID"
    assert path["npm", "author"] == "author"


def test_prose_and_empty_cells_without_a_curated_row_are_refused():
    dropped = {("cff-1.2.0", "license"), ("cargo", "description")}
    curated = [c for c in read_curated("3.1") if (c["format"], c["term"]) not in dropped]
    rows, findings = build_rows(read_dir(FIXTURE), "3.1", curated)
    assert [str(f) for f in findings] == [
        f"CELL_PROSE {CFF}: license: prose cell 'license / license-url', and no curated row",
        "CELL_EMPTY crosswalks/Cargo.csv: description: empty cell, no curated row",
    ]
    assert len(rows) == 64


def test_curated_row_that_repeats_the_cell_is_refused():
    curated = [*read_curated("3.1"), {"format": "npm", "term": "keywords", "path": "keywords", "reason": "x"}]
    _, findings = build_rows(read_dir(FIXTURE), "3.1", curated)
    assert [f.code for f in findings] == ["CURATED_REPEATS"]


def test_cli_export_writes_the_example(tmp_path: Path):
    out = tmp_path / "mapping.json"
    schemas = str(ROOT / "tests/fixtures/schemas")
    assert main(["export", str(FIXTURE), "--tag", "3.1", "--out", str(out), "--schemas", schemas]) == 0
    assert json.loads(out.read_text()) | {"generator": None} == EXAMPLE | {"generator": None}


def test_cli_export_lists_refused_cells(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    for path, text in read_dir(FIXTURE).items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text.replace("description,abstract", "description,abstract / summary"))
    assert main(["export", str(tmp_path), "--tag", "3.1"]) == 1
    assert (
        capsys.readouterr().out
        == f"CELL_PROSE {CFF}: description: prose cell 'abstract / summary', and no curated row\n"
    )


@pytest.mark.parametrize("args", [["--tag", "9.9"], ["--tag", "../3.1"], ["--tag", "3.1", "--ref", "x"]])
def test_cli_export_exits_2(args: list[str], tmp_path: Path):
    assert main(["export", str(tmp_path), *args]) == 2


def test_plain_check_still_runs():
    assert main([str(FIXTURE)]) == 1
