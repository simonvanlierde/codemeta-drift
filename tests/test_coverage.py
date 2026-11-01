import json
from pathlib import Path

import pytest

from codemeta_drift.cli import main, read_dir
from codemeta_drift.coverage import coverage, markdown, upstream

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/mapping-3.1.json"


def mapping():
    return json.loads(EXAMPLE.read_text("utf-8"))


def statuses():
    return {(c["format"], c["term"]): c["status"] for c in coverage(mapping())["cells"]}


def test_docs_page_is_generated_from_the_example():
    # Regenerate with: uv run codemeta-drift hub coverage examples/mapping-3.1.json --out docs/coverage.md
    assert (ROOT / "docs/coverage.md").read_text("utf-8") == markdown(mapping())


def test_known_cells_get_their_status():
    found = statuses()
    assert found["cff-1.2.0", "name"] == "as-is"
    assert found["cargo", "name"] == "corrected"  # the cell says package.authors
    assert found["npm", "identifier"] == "corrected"  # the cell says name, and npm has no DOI field
    assert found["cargo", "description"] == "added"  # no cell, though Cargo has package.description
    assert found["cargo", "datePublished"] == "no field"
    # The contributor person rows reuse the Person cells, but CFF has no contributor list to hold them.
    assert found["cff-1.2.0", "contributor.givenName"] == "no field"
    assert found["cff-1.2.0", "author.givenName"] == "as-is"  # the same Person row, with an author list
    assert found["pep621", "contributor.@id"] == "no field"
    assert not any(fmt == "codemeta" for fmt, _ in found)


def test_counts_for_the_crosswalks():
    found = [s for (fmt, _), s in statuses().items() if fmt != "pep621"]
    assert {s: found.count(s) for s in set(found)} == {"as-is": 41, "corrected": 32, "added": 26, "no field": 37}


def test_cli_writes_json(capsys: pytest.CaptureFixture[str]):
    assert main(["hub", "coverage", str(EXAMPLE), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["codemeta_tag"] == "3.1"
    assert len(data["cells"]) == 9 * 17


def test_upstream_reports_unmatched_changed_and_fixed_cells():
    files = read_dir(ROOT / "tests/fixtures/3.1")
    assert upstream(files, mapping()) == []
    cargo = "crosswalks/Cargo.csv"
    files[cargo] = files[cargo].replace("keywords,package.keyword", "keywords,package.keywords")
    files[cargo] = files[cargo].replace("version,package.version", "version,package.ver")
    zenodo = "crosswalks/Zenodo.csv"
    files[zenodo] = files[zenodo].replace("\nversion,", "\nversion,\nversion,", 1)
    cff = "crosswalks/Citation File Format 1.2.0.csv"
    files[cff] = files[cff].replace("\nname,title", "\nname,name", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping())}
    assert found == {
        ("cargo", "keywords"): "fixed",
        ("cargo", "version"): "changed",
        ("zenodo", "version"): "unmatched",
        ("cff-1.2.0", "name"): "changed",  # an as-is cell that changes is never "fixed"
    }


@pytest.mark.parametrize(
    ("cell", "term"),
    [
        ("identifier,ORCID", "author.@id"),  # Zenodo: orcid derives to creators[].orcid
        ("identifier,ORCID", "contributor.@id"),
    ],
)
def test_upstream_derives_the_new_cell_before_calling_it_fixed(cell: str, term: str):
    files = read_dir(ROOT / "tests/fixtures/3.1")
    zenodo = "crosswalks/Zenodo.csv"
    assert cell in files[zenodo]
    files[zenodo] = files[zenodo].replace(cell, "identifier,orcid")
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping())}
    assert found["zenodo", term] == "fixed"


def test_an_emptied_cell_is_not_a_fix_for_a_format_with_no_field():
    files = read_dir(ROOT / "tests/fixtures/3.1")
    npm = "crosswalks/NodeJS.csv"
    assert "\nidentifier,name" in files[npm]
    files[npm] = files[npm].replace("\nidentifier,name", "\nidentifier,", 1)
    found = {(c["format"], c["term"]): c["state"] for c in upstream(files, mapping())}
    # The export would refuse that empty cell without its curated row, so the row must stay.
    assert found["npm", "identifier"] == "changed"


def test_upstream_says_missing_when_a_crosswalk_is_gone():
    files = read_dir(ROOT / "tests/fixtures/3.1")
    del files["crosswalks/Cargo.csv"]
    states = {c["state"] for c in upstream(files, mapping()) if c["format"] == "cargo"}
    assert states == {"missing"}
